"""Política de control de acceso basado en roles (RF-10 / RNF-02).

Está en el dominio porque *qué puede hacer cada rol* es una regla de negocio.
La interfaz solo la consulta para ocultar opciones; la autoridad real la
ejercen los casos de uso mediante ``exigir``.
"""
from __future__ import annotations

from enum import Enum

from domain.exceptions import PermisoDenegadoError
from domain.policies.actor import Actor
from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.rol import Rol


class Permiso(str, Enum):
    REGISTRAR_INCIDENTE = "REGISTRAR_INCIDENTE"
    CONSULTAR_POR_CODIGO = "CONSULTAR_POR_CODIGO"
    VER_MIS_REPORTES = "VER_MIS_REPORTES"
    LISTAR_INCIDENTES = "LISTAR_INCIDENTES"
    VER_MAPA = "VER_MAPA"
    VER_ESTADISTICAS = "VER_ESTADISTICAS"
    CAMBIAR_ESTADO = "CAMBIAR_ESTADO"
    ASIGNAR_RESPONSABLE = "ASIGNAR_RESPONSABLE"
    VER_ASIGNADOS = "VER_ASIGNADOS"
    REGISTRAR_ATENCION = "REGISTRAR_ATENCION"
    GESTIONAR_USUARIOS = "GESTIONAR_USUARIOS"
    GESTIONAR_CATEGORIAS = "GESTIONAR_CATEGORIAS"
    VER_AUDITORIA = "VER_AUDITORIA"


_P = Permiso
_CIUDADANO = {_P.REGISTRAR_INCIDENTE, _P.CONSULTAR_POR_CODIGO, _P.VER_MIS_REPORTES}
_FUNCIONARIO = _CIUDADANO | {
    _P.LISTAR_INCIDENTES, _P.VER_MAPA, _P.VER_ESTADISTICAS,
    _P.CAMBIAR_ESTADO, _P.ASIGNAR_RESPONSABLE,
}
_RESPONSABLE = {_P.CONSULTAR_POR_CODIGO, _P.VER_MAPA, _P.VER_ASIGNADOS, _P.REGISTRAR_ATENCION}
_ADMIN = set(Permiso)

PERMISOS_POR_ROL: dict[Rol, set[Permiso]] = {
    Rol.CIUDADANO: _CIUDADANO,
    Rol.FUNCIONARIO: _FUNCIONARIO,
    Rol.RESPONSABLE: _RESPONSABLE,
    Rol.ADMINISTRADOR: _ADMIN,
}

# Estados destino que cada rol puede establecer (RF-06 + RBAC).
TRANSICIONES_POR_ROL: dict[Rol, set[EstadoIncidente]] = {
    Rol.CIUDADANO: set(),
    Rol.FUNCIONARIO: {EstadoIncidente.EN_REVISION, EstadoIncidente.EN_ATENCION,
                      EstadoIncidente.CERRADO},
    Rol.RESPONSABLE: {EstadoIncidente.ATENDIDO},
    Rol.ADMINISTRADOR: set(EstadoIncidente),
}


def puede(actor: Actor, permiso: Permiso) -> bool:
    return permiso in PERMISOS_POR_ROL[actor.rol]


def exigir(actor: Actor, permiso: Permiso) -> None:
    if not puede(actor, permiso):
        raise PermisoDenegadoError(
            f"El rol {actor.rol.etiqueta} no tiene permiso para esta acción.")


def puede_transicionar(actor: Actor, destino: EstadoIncidente) -> bool:
    return destino in TRANSICIONES_POR_ROL[actor.rol]
