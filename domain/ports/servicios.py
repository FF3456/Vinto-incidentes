"""Puertos de servicios técnicos: archivos y contraseñas."""
from __future__ import annotations

from abc import ABC, abstractmethod


class AlmacenamientoEvidencias(ABC):
    @abstractmethod
    def guardar(self, nombre_original: str, contenido: bytes) -> str:
        """Valida y guarda la imagen; devuelve la ruta relativa almacenada."""

    @abstractmethod
    def url_publica(self, ruta: str) -> str: ...


class HasheadorPassword(ABC):
    @abstractmethod
    def hashear(self, password: str) -> str: ...

    @abstractmethod
    def verificar(self, password: str, hash_guardado: str) -> bool: ...
