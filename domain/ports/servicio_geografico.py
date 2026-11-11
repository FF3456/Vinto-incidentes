"""Puerto geográfico (patrón Adapter, RF-03 y RF-08).

El dominio y la aplicación hablan con esta interfaz; el proveedor concreto de
mapas (OpenStreetMap, otro servidor de teselas, etc.) queda aislado en un
adaptador de infraestructura.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field

from domain.entities.incidente import IncidenteAmbiental


@dataclass(frozen=True)
class ConfiguracionMapa:
    centro: tuple[float, float]
    zoom: int
    url_teselas: str
    atribucion: str
    zoom_maximo: int = 19


@dataclass(frozen=True)
class MarcadorMapa:
    latitud: float
    longitud: float
    titulo: str
    detalle: str
    codigo: str
    estado: str
    color: str


@dataclass(frozen=True)
class Zona:
    nombre: str
    latitud: float
    longitud: float


class ServicioGeografico(ABC):
    @abstractmethod
    def configuracion(self) -> ConfiguracionMapa: ...

    @abstractmethod
    def crear_marcador(self, incidente: IncidenteAmbiental) -> MarcadorMapa: ...

    @abstractmethod
    def coordenadas_validas(self, latitud: float, longitud: float) -> bool:
        """¿El punto cae dentro del área de cobertura del municipio?"""

    @abstractmethod
    def zonas(self) -> list[Zona]: ...

    @abstractmethod
    def zona_para(self, latitud: float, longitud: float) -> str:
        """Zona más cercana al punto (se usa para el filtro por zona)."""
