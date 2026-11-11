"""Patrón Adapter: traduce el puerto ``ServicioGeografico`` a un proveedor de mapas concreto.

El resto del sistema nunca menciona OpenStreetMap ni Leaflet: solo conoce
``ServicioGeografico``. Cambiar de proveedor equivale a elegir otro adaptador
(variable de entorno ``VINTO_MAPA``) sin tocar dominio ni casos de uso (OCP/DIP).
"""
from __future__ import annotations

import math

from domain.entities.incidente import IncidenteAmbiental
from domain.ports.servicio_geografico import (
    ConfiguracionMapa, MarcadorMapa, ServicioGeografico, Zona)

CENTRO_VINTO = (-17.3865, -66.3140)
# Área de cobertura generosa alrededor de Vinto (configurable). Evita coordenadas absurdas.
_LAT = (-17.50, -17.28)
_LON = (-66.45, -66.18)

# Centros REFERENCIALES de zona: deben ajustarse con la cartografía oficial de la Alcaldía.
ZONAS_VINTO = [
    Zona("Zona Central", -17.3865, -66.3140),
    Zona("Zona Norte", -17.3745, -66.3140),
    Zona("Zona Sur", -17.3985, -66.3140),
    Zona("Zona Industrial", -17.3925, -66.2990),
    Zona("Barrio San Antonio", -17.3805, -66.3260),
    Zona("Zona Rural", -17.4115, -66.3440),
]

COLOR_ESTADO = {
    "REPORTADO": "#f59e0b", "EN_REVISION": "#3b82f6", "EN_ATENCION": "#8b5cf6",
    "ATENDIDO": "#10b981", "CERRADO": "#6b7280",
}


def _haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


class _AdaptadorLeafletBase(ServicioGeografico):
    """Lógica común; las subclases solo aportan el proveedor de teselas."""
    URL_TESELAS = ""
    ATRIBUCION = ""

    def configuracion(self) -> ConfiguracionMapa:
        return ConfiguracionMapa(CENTRO_VINTO, 13, self.URL_TESELAS, self.ATRIBUCION)

    def crear_marcador(self, incidente: IncidenteAmbiental) -> MarcadorMapa:
        u = incidente.ubicacion
        return MarcadorMapa(
            latitud=u.latitud, longitud=u.longitud, titulo=incidente.titulo,
            detalle=f"{incidente.categoria_nombre} · {incidente.estado.etiqueta} · {u.zona}",
            codigo=incidente.codigo, estado=incidente.estado.value,
            color=COLOR_ESTADO[incidente.estado.value])

    def coordenadas_validas(self, latitud: float, longitud: float) -> bool:
        return _LAT[0] <= latitud <= _LAT[1] and _LON[0] <= longitud <= _LON[1]

    def zonas(self) -> list[Zona]:
        return list(ZONAS_VINTO)

    def zona_para(self, latitud: float, longitud: float) -> str:
        return min(ZONAS_VINTO, key=lambda z: _haversine(latitud, longitud, z.latitud, z.longitud)).nombre


class AdaptadorOpenStreetMap(_AdaptadorLeafletBase):
    URL_TESELAS = "https://tile.openstreetmap.org/{z}/{x}/{y}.png"
    ATRIBUCION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'


class AdaptadorCartoClaro(_AdaptadorLeafletBase):
    URL_TESELAS = "https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png"
    ATRIBUCION = '&copy; OpenStreetMap contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'


_PROVEEDORES = {"osm": AdaptadorOpenStreetMap, "carto": AdaptadorCartoClaro}


def crear_servicio_geografico(proveedor: str = "osm") -> ServicioGeografico:
    return _PROVEEDORES.get(proveedor.lower(), AdaptadorOpenStreetMap)()
