"""RF-10: autenticación, registro de ciudadanos y administración de usuarios."""
from __future__ import annotations

from application.auditor import Auditor
from domain.entities.responsable import Responsable
from domain.entities.usuario import Usuario
from domain.exceptions import AutenticacionError, DuplicadoError, NoEncontradoError, ValidacionError
from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, exigir
from domain.ports.repositorios import IRepositorioResponsables, IRepositorioUsuarios
from domain.ports.servicios import HasheadorPassword
from domain.value_objects.rol import Rol

MIN_PASSWORD = 6


def _validar_password(password: str) -> None:
    if len(password or "") < MIN_PASSWORD:
        raise ValidacionError(f"La contraseña debe tener al menos {MIN_PASSWORD} caracteres.")


class Autenticar:
    def __init__(self, usuarios: IRepositorioUsuarios, hasher: HasheadorPassword,
                 auditor: Auditor) -> None:
        self._usuarios, self._hasher, self._auditor = usuarios, hasher, auditor

    def ejecutar(self, correo: str, password: str) -> Actor:
        usuario = self._usuarios.buscar_por_correo((correo or "").strip().lower())
        # Mensaje genérico a propósito: no revela si el correo existe.
        if usuario is None or not usuario.activo or \
                not self._hasher.verificar(password or "", usuario.password_hash):
            raise AutenticacionError("Correo o contraseña incorrectos.")
        actor = Actor(usuario.id, usuario.nombre, usuario.rol)
        self._auditor.registrar(actor, "Inicio de sesión", usuario.correo)
        return actor


class RegistrarCiudadano:
    def __init__(self, usuarios: IRepositorioUsuarios, hasher: HasheadorPassword,
                 auditor: Auditor) -> None:
        self._usuarios, self._hasher, self._auditor = usuarios, hasher, auditor

    def ejecutar(self, nombre: str, correo: str, password: str) -> Actor:
        _validar_password(password)
        if self._usuarios.buscar_por_correo((correo or "").strip().lower()):
            raise DuplicadoError("Ya existe una cuenta con ese correo.")
        usuario = self._usuarios.guardar(
            Usuario(nombre, correo, self._hasher.hashear(password), Rol.CIUDADANO))
        actor = Actor(usuario.id, usuario.nombre, usuario.rol)
        self._auditor.registrar(actor, "Usuario creado", usuario.correo, "Rol CIUDADANO (autoregistro)")
        return actor


class GestionarUsuarios:
    def __init__(self, usuarios: IRepositorioUsuarios, responsables: IRepositorioResponsables,
                 hasher: HasheadorPassword, auditor: Auditor) -> None:
        self._usuarios, self._responsables = usuarios, responsables
        self._hasher, self._auditor = hasher, auditor

    def listar(self, actor: Actor) -> list[Usuario]:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        return self._usuarios.listar()

    def crear(self, actor: Actor, nombre: str, correo: str, password: str, rol: Rol,
              unidad: str = "") -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        _validar_password(password)
        if self._usuarios.buscar_por_correo((correo or "").strip().lower()):
            raise DuplicadoError("Ya existe una cuenta con ese correo.")
        usuario = self._usuarios.guardar(Usuario(nombre, correo, self._hasher.hashear(password), rol))
        if rol == Rol.RESPONSABLE:   # todo responsable de atención tiene su ficha operativa
            self._responsables.guardar(Responsable(
                nombre=usuario.nombre, unidad=unidad or "Cuadrilla sin unidad",
                contacto=usuario.correo, usuario_id=usuario.id))
        self._auditor.registrar(actor, "Usuario creado", usuario.correo, f"Rol {rol.value}")
        return usuario

    def cambiar_activo(self, actor: Actor, usuario_id: int, activo: bool) -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise NoEncontradoError("Usuario no encontrado.")
        if usuario.id == actor.usuario_id and not activo:
            raise ValidacionError("No puede desactivar su propia cuenta.")
        usuario.activo = activo
        guardado = self._usuarios.guardar(usuario)
        resp = self._responsables.buscar_por_usuario(usuario.id)
        if resp:
            resp.activo = activo
            self._responsables.guardar(resp)
        self._auditor.registrar(actor, "Usuario activado" if activo else "Usuario desactivado",
                                usuario.correo)
        return guardado

    def cambiar_rol(self, actor: Actor, usuario_id: int, rol: Rol) -> Usuario:
        exigir(actor, Permiso.GESTIONAR_USUARIOS)
        usuario = self._usuarios.buscar_por_id(usuario_id)
        if usuario is None:
            raise NoEncontradoError("Usuario no encontrado.")
        if usuario.id == actor.usuario_id:
            raise ValidacionError("No puede cambiar su propio rol.")
        usuario.rol = rol
        guardado = self._usuarios.guardar(usuario)
        if rol == Rol.RESPONSABLE and self._responsables.buscar_por_usuario(usuario.id) is None:
            self._responsables.guardar(Responsable(
                nombre=usuario.nombre, unidad="Cuadrilla sin unidad",
                contacto=usuario.correo, usuario_id=usuario.id))
        self._auditor.registrar(actor, "Rol modificado", usuario.correo, f"Nuevo rol {rol.value}")
        return guardado


class ListarResponsables:
    def __init__(self, responsables: IRepositorioResponsables) -> None:
        self._responsables = responsables

    def ejecutar(self, actor: Actor) -> list[Responsable]:
        exigir(actor, Permiso.ASIGNAR_RESPONSABLE)
        return self._responsables.listar(solo_activos=True)
