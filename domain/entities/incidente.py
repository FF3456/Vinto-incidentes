"""Agregado raíz IncidenteAmbiental (DDD).

El agregado protege sus propias invariantes (SRP): flujo de estados, asignación
de responsable e historial. No sabe nada de bases de datos ni de NiceGUI.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta

from domain.exceptions import TransicionInvalidaError, ValidacionError
from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.evidencia import Evidencia
from domain.value_objects.prioridad import Prioridad
from domain.value_objects.ubicacion import Ubicacion


@dataclass(frozen=True)
class RegistroHistorial:
    """Un cambio de estado inmutable (RF-14 / trazabilidad)."""
    estado_anterior: EstadoIncidente | None
    estado_nuevo: EstadoIncidente
    fecha: datetime
    usuario_nombre: str
    observacion: str = ""
    usuario_id: int | None = None


@dataclass
class IncidenteAmbiental:
    codigo: str
    titulo: str
    descripcion: str
    categoria_id: int
    categoria_nombre: str
    fecha_incidente: datetime
    fecha_reporte: datetime
    ubicacion: Ubicacion
    prioridad: Prioridad = Prioridad.MEDIA
    plazo_horas: int = 72
    estado: EstadoIncidente = EstadoIncidente.REPORTADO
    reportante_id: int | None = None
    contacto_nombre: str = ""
    contacto_medio: str = ""
    responsable_id: int | None = None
    responsable_nombre: str = ""
    resumen_atencion: str = ""
    evidencias: list[Evidencia] = field(default_factory=list)
    historial: list[RegistroHistorial] = field(default_factory=list)
    fecha_actualizacion: datetime | None = None
    id: int | None = None

    # ------------------------------------------------------------------ reglas
    def __post_init__(self) -> None:
        self.titulo = (self.titulo or "").strip()
        self.descripcion = (self.descripcion or "").strip()
        if not self.titulo:
            raise ValidacionError("El título es obligatorio.")
        if not self.descripcion:
            raise ValidacionError("La descripción es obligatoria.")
        if self.fecha_actualizacion is None:
            self.fecha_actualizacion = self.fecha_reporte

    def registrar_creacion(self, usuario_nombre: str, usuario_id: int | None = None) -> None:
        """Primer registro del historial: nace en REPORTADO."""
        self.historial.append(RegistroHistorial(
            None, EstadoIncidente.REPORTADO, self.fecha_reporte,
            usuario_nombre, "Reporte registrado", usuario_id))

    def cambiar_estado(self, nuevo: EstadoIncidente, ahora: datetime,
                       usuario_nombre: str, observacion: str = "",
                       usuario_id: int | None = None) -> None:
        """RF-06: REPORTADO → EN_REVISION → EN_ATENCION → ATENDIDO → CERRADO."""
        if not self.estado.puede_pasar_a(nuevo):
            raise TransicionInvalidaError(
                f"Cambio no permitido: {self.estado.etiqueta} → {nuevo.etiqueta}.")
        if nuevo == EstadoIncidente.EN_ATENCION and self.responsable_id is None:
            raise TransicionInvalidaError(
                "Debe asignarse un responsable antes de pasar a EN ATENCIÓN.")
        anterior = self.estado
        self.estado = nuevo
        self.fecha_actualizacion = ahora
        self.historial.append(RegistroHistorial(
            anterior, nuevo, ahora, usuario_nombre, (observacion or "").strip(), usuario_id))

    def asignar_responsable(self, responsable_id: int, responsable_nombre: str) -> None:
        """RF-07: solo mientras el caso está en revisión o en atención."""
        if self.estado not in (EstadoIncidente.EN_REVISION, EstadoIncidente.EN_ATENCION):
            raise TransicionInvalidaError(
                "Solo se puede asignar responsable a casos EN REVISIÓN o EN ATENCIÓN.")
        self.responsable_id = responsable_id
        self.responsable_nombre = responsable_nombre

    def registrar_atencion(self, resumen: str, ahora: datetime,
                           usuario_nombre: str, usuario_id: int | None = None) -> None:
        """HU-05: el responsable deja constancia y el caso pasa a ATENDIDO."""
        resumen = (resumen or "").strip()
        if len(resumen) < 10:
            raise ValidacionError("El resumen de la atención debe tener al menos 10 caracteres.")
        self.resumen_atencion = resumen
        self.cambiar_estado(EstadoIncidente.ATENDIDO, ahora, usuario_nombre, resumen, usuario_id)

    def adjuntar_evidencia(self, evidencia: Evidencia) -> None:
        self.evidencias.append(evidencia)

    # -------------------------------------------------------------- consultas
    @property
    def fecha_limite(self) -> datetime:
        return self.fecha_reporte + timedelta(hours=self.plazo_horas)

    def esta_vencido(self, ahora: datetime) -> bool:
        return self.estado in (EstadoIncidente.REPORTADO, EstadoIncidente.EN_REVISION,
                               EstadoIncidente.EN_ATENCION) and ahora > self.fecha_limite

    def fecha_de(self, estado: EstadoIncidente) -> datetime | None:
        """Fecha en que el caso llegó por primera vez al estado indicado."""
        for r in self.historial:
            if r.estado_nuevo == estado:
                return r.fecha
        return None

    def horas_hasta(self, estado: EstadoIncidente) -> float | None:
        f = self.fecha_de(estado)
        return None if f is None else (f - self.fecha_reporte).total_seconds() / 3600
