"""Entidad Responsable de atención / cuadrilla (RF-07)."""
from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import ValidacionError


@dataclass
class Responsable:
    nombre: str
    unidad: str = ""
    contacto: str = ""
    activo: bool = True
    usuario_id: int | None = None   # cuenta con la que el responsable ingresa al sistema
    id: int | None = None

    def __post_init__(self) -> None:
        self.nombre = (self.nombre or "").strip()
        if len(self.nombre) < 3:
            raise ValidacionError("El nombre del responsable debe tener al menos 3 caracteres.")
