"""Objeto de valor Ubicacion (RF-03).

Es inmutable y se valida al construirse: un incidente jamás puede quedar con
coordenadas fuera de rango.
"""
from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import ValidacionError


@dataclass(frozen=True)
class Ubicacion:
    latitud: float
    longitud: float
    referencia: str = ""
    zona: str = ""

    def __post_init__(self) -> None:
        if not isinstance(self.latitud, (int, float)) or not isinstance(self.longitud, (int, float)):
            raise ValidacionError("Las coordenadas deben ser numéricas.")
        if not -90 <= self.latitud <= 90:
            raise ValidacionError("La latitud debe estar entre -90 y 90.")
        if not -180 <= self.longitud <= 180:
            raise ValidacionError("La longitud debe estar entre -180 y 180.")
        object.__setattr__(self, "referencia", (self.referencia or "").strip())
        object.__setattr__(self, "zona", (self.zona or "").strip())

    @property
    def coordenadas(self) -> tuple[float, float]:
        return (self.latitud, self.longitud)
