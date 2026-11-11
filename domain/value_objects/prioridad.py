"""Prioridad de atención, definida por la política de cada categoría."""
from enum import Enum


class Prioridad(str, Enum):
    BAJA = "BAJA"
    MEDIA = "MEDIA"
    ALTA = "ALTA"
    URGENTE = "URGENTE"

    @property
    def etiqueta(self) -> str:
        return self.value.capitalize()
