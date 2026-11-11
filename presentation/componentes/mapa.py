"""Componentes de mapa (RF-03 selección de punto, RF-08 visor de incidentes).

Usan el puerto ``ServicioGeografico``: la UI no sabe qué proveedor de teselas hay detrás.
"""
from __future__ import annotations

import html
from typing import Callable

from nicegui import ui

from domain.ports.servicio_geografico import MarcadorMapa, ServicioGeografico
from domain.value_objects.estado import EstadoIncidente

LEYENDA = [(e.etiqueta, c) for e, c in zip(
    EstadoIncidente, ["#f59e0b", "#3b82f6", "#8b5cf6", "#10b981", "#6b7280"])]


def crear_mapa(geo: ServicioGeografico, altura: int = 420, centro: tuple[float, float] | None = None,
               zoom: int | None = None) -> ui.leaflet:
    cfg = geo.configuracion()
    mapa = ui.leaflet(center=centro or cfg.centro, zoom=zoom or cfg.zoom).classes("w-full") \
        .style(f"height:{altura}px; min-height:{altura}px; flex-shrink:0; border-radius:12px")
    mapa.clear_layers()        # quita la capa OSM por defecto: el adaptador decide el proveedor
    mapa.tile_layer(url_template=cfg.url_teselas,
                    options={"attribution": cfg.atribucion, "maxZoom": cfg.zoom_maximo})
    return mapa


def _popup(m: MarcadorMapa) -> str:
    e = html.escape
    return f"<b>{e(m.codigo)}</b><br>{e(m.titulo)}<br><small>{e(m.detalle)}</small>"


class CapaIncidentes:
    """Dibuja marcadores circulares coloreados por estado y permite refrescarlos."""

    def __init__(self, mapa: ui.leaflet) -> None:
        self._mapa = mapa
        self._capas: list = []

    async def mostrar(self, marcadores: list[MarcadorMapa]) -> None:
        for capa in self._capas:
            self._mapa.remove_layer(capa)
        self._capas = []
        nuevas = []
        with self._mapa:
            for mk in marcadores:
                capa = self._mapa.generic_layer(name="circleMarker", args=[
                    [mk.latitud, mk.longitud],
                    {"radius": 10, "color": "#ffffff", "weight": 2, "fillColor": mk.color,
                     "fillOpacity": 0.95}])
                nuevas.append((capa, mk))
        self._capas = [c for c, _ in nuevas]
        try:
            await self._mapa.initialized()
        except Exception:      # el cliente se desconectó
            return
        for capa, mk in nuevas:
            capa.run_method("bindPopup", _popup(mk))


def leyenda_estados() -> None:
    with ui.row().classes("leyenda gap-4 text-sm"):
        for etiqueta, color in LEYENDA:
            ui.html(f'<span><i style="background:{color}"></i>{etiqueta}</span>')


class SelectorUbicacion:
    """Mapa en el que el ciudadano hace clic para fijar la ubicación del incidente (RF-03)."""

    def __init__(self, geo: ServicioGeografico, al_elegir: Callable[[float, float], None]) -> None:
        self._geo = geo
        self._al_elegir = al_elegir
        self.mapa = crear_mapa(geo, altura=340, zoom=14)
        self._marcador = None
        self.mapa.on("map-click", self._clic)

    def _clic(self, e) -> None:
        ll = e.args["latlng"]
        self.fijar(ll["lat"], ll["lng"])
        self._al_elegir(ll["lat"], ll["lng"])

    def fijar(self, lat: float, lng: float) -> None:
        if self._marcador is None:
            with self.mapa:
                self._marcador = self.mapa.marker(latlng=(lat, lng))
        else:
            self._marcador.move(lat, lng)


def mapa_puntual(geo: ServicioGeografico, lat: float, lng: float, altura: int = 220) -> ui.leaflet:
    mapa = crear_mapa(geo, altura=altura, centro=(lat, lng), zoom=16)
    with mapa:
        mapa.marker(latlng=(lat, lng))
    return mapa
