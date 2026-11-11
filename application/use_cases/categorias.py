"""RF-02 / HU-06: catálogo dinámico de categorías."""
from __future__ import annotations

from application.auditor import Auditor
from domain.entities.categoria import Categoria
from domain.exceptions import DuplicadoError, NoEncontradoError
from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, exigir
from domain.ports.repositorios import IRepositorioCategorias


class ListarCategorias:
    """Lectura pública: el formulario ciudadano necesita el catálogo."""

    def __init__(self, categorias: IRepositorioCategorias) -> None:
        self._categorias = categorias

    def ejecutar(self, solo_activas: bool = True) -> list[Categoria]:
        return self._categorias.listar(solo_activas)


class GestionarCategorias:
    def __init__(self, categorias: IRepositorioCategorias, auditor: Auditor) -> None:
        self._categorias, self._auditor = categorias, auditor

    def crear(self, actor: Actor, nombre: str, descripcion: str, perfil: str) -> Categoria:
        exigir(actor, Permiso.GESTIONAR_CATEGORIAS)
        nueva = Categoria(nombre, descripcion, perfil)
        if self._categorias.buscar_por_nombre(nueva.nombre):
            raise DuplicadoError("Ya existe una categoría con ese nombre.")
        guardada = self._categorias.guardar(nueva)
        self._auditor.registrar(actor, "Categoría creada", guardada.nombre, f"Perfil {perfil}")
        return guardada

    def editar(self, actor: Actor, categoria_id: int, nombre: str, descripcion: str,
               perfil: str) -> Categoria:
        exigir(actor, Permiso.GESTIONAR_CATEGORIAS)
        existente = self._categorias.buscar_por_id(categoria_id)
        if existente is None:
            raise NoEncontradoError("Categoría no encontrada.")
        actualizada = Categoria(nombre, descripcion, perfil, existente.activa, existente.id)
        otra = self._categorias.buscar_por_nombre(actualizada.nombre)
        if otra and otra.id != existente.id:
            raise DuplicadoError("Ya existe una categoría con ese nombre.")
        guardada = self._categorias.guardar(actualizada)
        self._auditor.registrar(actor, "Categoría editada", guardada.nombre)
        return guardada

    def cambiar_activa(self, actor: Actor, categoria_id: int, activa: bool) -> Categoria:
        exigir(actor, Permiso.GESTIONAR_CATEGORIAS)
        categoria = self._categorias.buscar_por_id(categoria_id)
        if categoria is None:
            raise NoEncontradoError("Categoría no encontrada.")
        categoria.activar() if activa else categoria.desactivar()
        guardada = self._categorias.guardar(categoria)
        self._auditor.registrar(
            actor, "Categoría activada" if activa else "Categoría desactivada", guardada.nombre)
        return guardada
