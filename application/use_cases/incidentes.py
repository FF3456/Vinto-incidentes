"""Casos de uso de escritura sobre incidentes (RF-01…RF-04, RF-06, RF-07)."""
from __future__ import annotations

import threading
from datetime import datetime
from typing import Callable

from application.auditor import Auditor
from application.dto import ArchivoSubido, ComandoRegistrarIncidente
from domain.entities.incidente import IncidenteAmbiental
from domain.exceptions import NoEncontradoError, PermisoDenegadoError, ValidacionError
from domain.factories.incidente_factory import IncidenteFactory
from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, exigir, puede_transicionar
from domain.ports.repositorios import (
    IRepositorioCategorias, IRepositorioIncidentes, IRepositorioResponsables)
from domain.ports.servicio_geografico import ServicioGeografico
from domain.ports.servicios import AlmacenamientoEvidencias
from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.evidencia import Evidencia
from domain.value_objects.rol import Rol
from domain.value_objects.ubicacion import Ubicacion

MAX_EVIDENCIAS = 3


def _subir(almacen: AlmacenamientoEvidencias, archivos: list[ArchivoSubido],
           ahora: datetime, tipo: str) -> list[Evidencia]:
    if len(archivos) > MAX_EVIDENCIAS:
        raise ValidacionError(f"Se permiten como máximo {MAX_EVIDENCIAS} fotografías.")
    return [Evidencia(almacen.guardar(a.nombre, a.contenido), ahora, tipo) for a in archivos]


def _cargar(repo: IRepositorioIncidentes, codigo: str) -> IncidenteAmbiental:
    incidente = repo.buscar_por_codigo((codigo or "").strip().upper())
    if incidente is None:
        raise NoEncontradoError(f"No existe un reporte con el código {codigo}.")
    return incidente


class RegistrarIncidente:
    """RF-01 + RF-02 + RF-03 + RF-04. Genera el código único de seguimiento."""

    _candado = threading.Lock()   # evita códigos duplicados bajo concurrencia

    def __init__(self, incidentes: IRepositorioIncidentes, categorias: IRepositorioCategorias,
                 factory: IncidenteFactory, geo: ServicioGeografico,
                 almacen: AlmacenamientoEvidencias, auditor: Auditor,
                 reloj: Callable[[], datetime] = datetime.now) -> None:
        self._incidentes, self._categorias = incidentes, categorias
        self._factory, self._geo, self._almacen = factory, geo, almacen
        self._auditor, self._reloj = auditor, reloj

    def ejecutar(self, actor: Actor, cmd: ComandoRegistrarIncidente) -> IncidenteAmbiental:
        exigir(actor, Permiso.REGISTRAR_INCIDENTE)
        categoria = self._categorias.buscar_por_id(cmd.categoria_id)
        if categoria is None:
            raise ValidacionError("Debe seleccionar una categoría válida.")
        if not self._geo.coordenadas_validas(cmd.latitud, cmd.longitud):
            raise ValidacionError(
                "La ubicación está fuera del área de cobertura del municipio de Vinto.")
        if len((cmd.referencia or "").strip()) < 3:
            raise ValidacionError("Indique una referencia del lugar (calle, barrio, punto conocido).")
        zona = cmd.zona or self._geo.zona_para(cmd.latitud, cmd.longitud)
        ubicacion = Ubicacion(cmd.latitud, cmd.longitud, cmd.referencia, zona)
        ahora = self._reloj()

        with self._candado:
            codigo = f"VINTO-{ahora.year}-{self._incidentes.contar_del_anio(ahora.year) + 1:04d}"
            incidente = self._factory.crear(
                categoria=categoria, codigo=codigo, titulo=cmd.titulo,
                descripcion=cmd.descripcion, fecha_incidente=cmd.fecha_incidente,
                fecha_reporte=ahora, ubicacion=ubicacion, reportante_id=actor.usuario_id,
                contacto_nombre=cmd.contacto_nombre, contacto_medio=cmd.contacto_medio)
            for ev in _subir(self._almacen, cmd.archivos, ahora, "REPORTE"):
                incidente.adjuntar_evidencia(ev)
            incidente.registrar_creacion(actor.nombre, actor.usuario_id)
            guardado = self._incidentes.guardar(incidente)
        self._auditor.registrar(actor, "Incidente registrado", guardado.codigo, guardado.titulo)
        return guardado


class CambiarEstado:
    """RF-06: transición validada por el dominio y autorizada por rol."""

    def __init__(self, incidentes: IRepositorioIncidentes, auditor: Auditor,
                 reloj: Callable[[], datetime] = datetime.now) -> None:
        self._incidentes, self._auditor, self._reloj = incidentes, auditor, reloj

    def ejecutar(self, actor: Actor, codigo: str, nuevo: EstadoIncidente,
                 observacion: str = "") -> IncidenteAmbiental:
        exigir(actor, Permiso.CAMBIAR_ESTADO)
        if not puede_transicionar(actor, nuevo):
            raise PermisoDenegadoError(
                f"El rol {actor.rol.etiqueta} no puede establecer el estado {nuevo.etiqueta}.")
        incidente = _cargar(self._incidentes, codigo)
        anterior = incidente.estado
        incidente.cambiar_estado(nuevo, self._reloj(), actor.nombre, observacion, actor.usuario_id)
        guardado = self._incidentes.guardar(incidente)
        self._auditor.registrar(actor, "Cambio de estado", guardado.codigo,
                                f"{anterior.value} → {nuevo.value}")
        return guardado


class AsignarResponsable:
    """RF-07: asigna cuadrilla/responsable y, si el caso estaba en revisión, lo pasa a atención."""

    def __init__(self, incidentes: IRepositorioIncidentes, responsables: IRepositorioResponsables,
                 auditor: Auditor, reloj: Callable[[], datetime] = datetime.now) -> None:
        self._incidentes, self._responsables = incidentes, responsables
        self._auditor, self._reloj = auditor, reloj

    def ejecutar(self, actor: Actor, codigo: str, responsable_id: int,
                 observacion: str = "") -> IncidenteAmbiental:
        exigir(actor, Permiso.ASIGNAR_RESPONSABLE)
        responsable = self._responsables.buscar_por_id(responsable_id)
        if responsable is None or not responsable.activo:
            raise NoEncontradoError("El responsable seleccionado no existe o está inactivo.")
        incidente = _cargar(self._incidentes, codigo)
        incidente.asignar_responsable(responsable.id, responsable.nombre)
        if incidente.estado == EstadoIncidente.EN_REVISION:
            incidente.cambiar_estado(
                EstadoIncidente.EN_ATENCION, self._reloj(), actor.nombre,
                observacion or f"Asignado a {responsable.nombre}", actor.usuario_id)
        guardado = self._incidentes.guardar(incidente)
        self._auditor.registrar(actor, "Responsable asignado", guardado.codigo, responsable.nombre)
        return guardado


class RegistrarAtencion:
    """HU-05: el responsable documenta la intervención y el caso pasa a ATENDIDO."""

    def __init__(self, incidentes: IRepositorioIncidentes, responsables: IRepositorioResponsables,
                 almacen: AlmacenamientoEvidencias, auditor: Auditor,
                 reloj: Callable[[], datetime] = datetime.now) -> None:
        self._incidentes, self._responsables = incidentes, responsables
        self._almacen, self._auditor, self._reloj = almacen, auditor, reloj

    def ejecutar(self, actor: Actor, codigo: str, resumen: str,
                 archivos: list[ArchivoSubido] | None = None) -> IncidenteAmbiental:
        exigir(actor, Permiso.REGISTRAR_ATENCION)
        incidente = _cargar(self._incidentes, codigo)
        if actor.rol == Rol.RESPONSABLE:
            propio = self._responsables.buscar_por_usuario(actor.usuario_id or -1)
            if propio is None or incidente.responsable_id != propio.id:
                raise PermisoDenegadoError("Este caso no está asignado a usted.")
        ahora = self._reloj()
        incidente.registrar_atencion(resumen, ahora, actor.nombre, actor.usuario_id)
        for ev in _subir(self._almacen, archivos or [], ahora, "ATENCION"):
            incidente.adjuntar_evidencia(ev)
        guardado = self._incidentes.guardar(incidente)
        self._auditor.registrar(actor, "Atención registrada", guardado.codigo, resumen[:120])
        return guardado
