"""Acceso al contenedor de casos de uso desde las páginas (evita globals dispersos)."""
from __future__ import annotations

from bootstrap import Contenedor

_contenedor: Contenedor | None = None


def fijar(contenedor: Contenedor) -> None:
    global _contenedor
    _contenedor = contenedor


def c() -> Contenedor:
    assert _contenedor is not None, "El contenedor no fue inicializado (ver main.py)"
    return _contenedor
