"""Fixtures compartidas. Los casos de uso se prueban con repositorios en memoria (DIP)."""
from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from application.auditor import Auditor
from application.dto import ArchivoSubido, ComandoRegistrarIncidente
from application.use_cases.categorias import GestionarCategorias, ListarCategorias
from application.use_cases.consultas import (
    ConsultarPorCodigo, IncidentesAsignados, ListarIncidentes, MisReportes, ObtenerMarcadoresMapa)
from application.use_cases.estadisticas import ObtenerEstadisticas
from application.use_cases.incidentes import (
    AsignarResponsable, CambiarEstado, RegistrarAtencion, RegistrarIncidente)
from application.use_cases.usuarios import Autenticar, GestionarUsuarios, RegistrarCiudadano
from domain.entities.categoria import Categoria
from domain.entities.responsable import Responsable
from domain.entities.usuario import Usuario
from domain.factories.incidente_factory import IncidenteFactory
from domain.policies.actor import Actor
from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.rol import Rol
from infrastructure.maps.adaptadores import AdaptadorOpenStreetMap
from infrastructure.memory.repositorios_memoria import (
    RepositorioAuditoriaMemoria, RepositorioCategoriasMemoria, RepositorioIncidentesMemoria,
    RepositorioResponsablesMemoria, RepositorioUsuariosMemoria)
from infrastructure.security.hasher import HasheadorPBKDF2
from infrastructure.storage.almacenamiento_local import AlmacenamientoLocal

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPG = b"\xff\xd8\xff\xe0" + b"\x00" * 64


class Reloj:
    """Reloj controlable para probar tiempos de respuesta de forma determinista."""
    def __init__(self) -> None:
        self.ahora = datetime(2026, 10, 1, 9, 0)

    def __call__(self) -> datetime:
        return self.ahora

    def avanzar(self, **kw) -> None:
        self.ahora += timedelta(**kw)


class Mundo:
    """Contenedor mínimo de pruebas: casos de uso + repos en memoria."""
    def __init__(self, tmp_path) -> None:
        self.reloj = Reloj()
        self.incidentes = RepositorioIncidentesMemoria()
        self.categorias = RepositorioCategoriasMemoria()
        self.usuarios = RepositorioUsuariosMemoria()
        self.responsables = RepositorioResponsablesMemoria()
        self.auditoria = RepositorioAuditoriaMemoria()
        self.geo = AdaptadorOpenStreetMap()
        self.almacen = AlmacenamientoLocal(tmp_path / "ev")
        self.hasher = HasheadorPBKDF2(iteraciones=1000)   # rápido en pruebas
        self.factory = IncidenteFactory()
        a = Auditor(self.auditoria, self.reloj)
        self.auditor = a
        self.cat_basura = self.categorias.guardar(Categoria("Acumulación de basura", "", "RESIDUOS"))
        self.cat_rio = self.categorias.guardar(Categoria("Contaminación de ríos", "", "AGUA"))
        u_resp = self.usuarios.guardar(Usuario("Carlos Mamani", "resp@vinto.test", "x", Rol.RESPONSABLE))
        self.resp = self.responsables.guardar(Responsable("Carlos Mamani", "Residuos", "", True, u_resp.id))
        self.resp_actor = Actor(u_resp.id, "Carlos Mamani", Rol.RESPONSABLE)
        u_otro = self.usuarios.guardar(Usuario("Otra Persona", "otro@vinto.test", "x", Rol.RESPONSABLE))
        self.otro = self.responsables.guardar(Responsable("Otra Persona", "Agua", "", True, u_otro.id))
        self.otro_actor = Actor(u_otro.id, "Otra Persona", Rol.RESPONSABLE)
        self.func = self._actor("Patricia Quispe", "func@vinto.test", Rol.FUNCIONARIO)
        self.admin = self._actor("Administrador", "admin@vinto.test", Rol.ADMINISTRADOR)
        self.vecino = self._actor("Vecino Prueba", "vecino@vinto.test", Rol.CIUDADANO)
        self.anonimo = Actor.anonimo()

        self.registrar = RegistrarIncidente(self.incidentes, self.categorias, self.factory, self.geo,
                                            self.almacen, a, self.reloj)
        self.cambiar = CambiarEstado(self.incidentes, a, self.reloj)
        self.asignar = AsignarResponsable(self.incidentes, self.responsables, a, self.reloj)
        self.atender = RegistrarAtencion(self.incidentes, self.responsables, self.almacen, a, self.reloj)
        self.listar = ListarIncidentes(self.incidentes)
        self.por_codigo = ConsultarPorCodigo(self.incidentes)
        self.mis = MisReportes(self.incidentes)
        self.asignados = IncidentesAsignados(self.incidentes, self.responsables)
        self.marcadores = ObtenerMarcadoresMapa(self.incidentes, self.responsables, self.geo)
        self.stats = ObtenerEstadisticas(self.incidentes, self.reloj)
        self.autenticar = Autenticar(self.usuarios, self.hasher, a)
        self.reg_ciudadano = RegistrarCiudadano(self.usuarios, self.hasher, a)
        self.usuarios_uc = GestionarUsuarios(self.usuarios, self.responsables, self.hasher, a)
        self.categorias_uc = GestionarCategorias(self.categorias, a)
        self.listar_cat = ListarCategorias(self.categorias)

    def _actor(self, nombre: str, correo: str, rol: Rol) -> Actor:
        u = self.usuarios.guardar(Usuario(nombre, correo, "x", rol))
        return Actor(u.id, nombre, rol)

    def cmd(self, **kw) -> ComandoRegistrarIncidente:
        base = dict(categoria_id=self.cat_basura.id, titulo="Basura en la esquina",
                    descripcion="Hay bolsas de basura acumuladas hace varios días.",
                    fecha_incidente=self.reloj.ahora - timedelta(hours=2),
                    latitud=-17.3868, longitud=-66.3142, referencia="Av. Bolívar esq. calle 1")
        base.update(kw)
        return ComandoRegistrarIncidente(**base)

    def nuevo(self, actor=None, **kw):
        return self.registrar.ejecutar(actor or self.vecino, self.cmd(**kw))

    def llevar_a_atencion(self, codigo: str) -> None:
        self.cambiar.ejecutar(self.func, codigo, EstadoIncidente.EN_REVISION)
        self.asignar.ejecutar(self.func, codigo, self.resp.id)


@pytest.fixture
def mundo(tmp_path) -> Mundo:
    return Mundo(tmp_path)


@pytest.fixture
def png() -> ArchivoSubido:
    return ArchivoSubido("foto.png", PNG)
