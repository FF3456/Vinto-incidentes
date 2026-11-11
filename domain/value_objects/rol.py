"""Roles del sistema (RF-10)."""
from enum import Enum


class Rol(str, Enum):
    CIUDADANO = "CIUDADANO"
    FUNCIONARIO = "FUNCIONARIO"
    RESPONSABLE = "RESPONSABLE"
    ADMINISTRADOR = "ADMINISTRADOR"

    @property
    def etiqueta(self) -> str:
        return {
            "CIUDADANO": "Ciudadano",
            "FUNCIONARIO": "Funcionario municipal",
            "RESPONSABLE": "Responsable de atención",
            "ADMINISTRADOR": "Administrador",
        }[self.value]
