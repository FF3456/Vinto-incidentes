"""Objeto de valor Evidencia fotográfica (RF-04)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class Evidencia:
    ruta_archivo: str            # nombre relativo dentro del almacenamiento
    fecha_carga: datetime
    tipo: str = "REPORTE"        # REPORTE (ciudadano) | ATENCION (responsable)
