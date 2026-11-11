"""Entidad Usuario (RF-10)."""
from __future__ import annotations

import re
from dataclasses import dataclass

from domain.exceptions import ValidacionError
from domain.value_objects.rol import Rol

_CORREO = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@dataclass
class Usuario:
    nombre: str
    correo: str
    password_hash: str
    rol: Rol = Rol.CIUDADANO
    activo: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        self.nombre = (self.nombre or "").strip()
        self.correo = (self.correo or "").strip().lower()
        if len(self.nombre) < 3:
            raise ValidacionError("El nombre debe tener al menos 3 caracteres.")
        if not _CORREO.match(self.correo):
            raise ValidacionError("El correo electrónico no es válido.")
