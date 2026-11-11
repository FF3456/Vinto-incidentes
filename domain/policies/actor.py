"""Actor: quien ejecuta una acción. Un ciudadano sin cuenta es un actor anónimo."""
from __future__ import annotations

from dataclasses import dataclass

from domain.value_objects.rol import Rol


@dataclass(frozen=True)
class Actor:
    usuario_id: int | None
    nombre: str
    rol: Rol

    @staticmethod
    def anonimo() -> "Actor":
        return Actor(None, "Ciudadano (sin cuenta)", Rol.CIUDADANO)
