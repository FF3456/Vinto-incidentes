"""Casos de uso de lectura (RF-05, RF-08, RF-13)."""
from __future__ import annotations

from dataclasses import replace

from application.dto import ArchivoSubido  # noqa: F401  (re-export cómodo para la UI)
from domain.entities.incidente import IncidenteAmbiental
from domain.exceptions import NoEncontradoError
from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, exigir
from domain.ports.repositorios import (
    FiltroIncidentes, IRepositorioIncidentes, IRepositorioResponsables)
from domain.ports.servicio_geografico import MarcadorMapa, ServicioGeografico
from domain.value_objects.rol import Rol


class ListarIncidentes:
    """RF-05: listado con filtros combinables por categoría, estado, fecha y zona."""

    def __init__(self, incidentes: IRepositorioIncidentes) -> None:
        self._incidentes = incidentes

    def ejecutar(self, actor: Actor, filtro: FiltroIncidentes | None = None) -> list[IncidenteAmbiental]:
        exigir(actor, Permiso.LISTAR_INCIDENTES)
        return self._incidentes.listar(filtro)


class ConsultarPorCodigo:
    """RF-13: cualquier persona con el código puede ver el estado de su reporte."""

    def __init__(self, incidentes: IRepositorioIncidentes) -> None:
        self._incidentes = incidentes

    def ejecutar(self, actor: Actor, codigo: str) -> IncidenteAmbiental:
        exigir(actor, Permiso.CONSULTAR_POR_CODIGO)
        incidente = self._incidentes.buscar_por_codigo((codigo or "").strip().upper())
        if incidente is None:
            raise NoEncontradoError("No se encontró ningún reporte con ese código.")
        if actor.rol == Rol.CIUDADANO:   # privacidad: el contacto del reportante no se expone al público
            incidente = replace(incidente, contacto_nombre="", contacto_medio="")
        return incidente


class MisReportes:
    def __init__(self, incidentes: IRepositorioIncidentes) -> None:
        self._incidentes = incidentes

    def ejecutar(self, actor: Actor) -> list[IncidenteAmbiental]:
        exigir(actor, Permiso.VER_MIS_REPORTES)
        if actor.usuario_id is None:
            return []
        return self._incidentes.listar(FiltroIncidentes(reportante_id=actor.usuario_id))


class IncidentesAsignados:
    def __init__(self, incidentes: IRepositorioIncidentes,
                 responsables: IRepositorioResponsables) -> None:
        self._incidentes, self._responsables = incidentes, responsables

    def ejecutar(self, actor: Actor) -> list[IncidenteAmbiental]:
        exigir(actor, Permiso.VER_ASIGNADOS)
        resp = self._responsables.buscar_por_usuario(actor.usuario_id or -1)
        if resp is None:
            return []
        return self._incidentes.listar(FiltroIncidentes(responsable_id=resp.id))


class ObtenerMarcadoresMapa:
    """RF-08: convierte incidentes en marcadores a través del puerto geográfico."""

    def __init__(self, incidentes: IRepositorioIncidentes, responsables: IRepositorioResponsables,
                 geo: ServicioGeografico) -> None:
        self._incidentes, self._responsables, self._geo = incidentes, responsables, geo

    def ejecutar(self, actor: Actor, filtro: FiltroIncidentes | None = None) -> list[MarcadorMapa]:
        exigir(actor, Permiso.VER_MAPA)
        filtro = filtro or FiltroIncidentes()
        if actor.rol == Rol.RESPONSABLE:   # el responsable solo ve su ruta de trabajo
            resp = self._responsables.buscar_por_usuario(actor.usuario_id or -1)
            if resp is None:
                return []
            filtro.responsable_id = resp.id
        return [self._geo.crear_marcador(i) for i in self._incidentes.listar(filtro)]
