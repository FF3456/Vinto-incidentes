"""Adaptador de archivos: guarda evidencias fotográficas en una carpeta controlada (RF-04)."""
from __future__ import annotations

import uuid
from pathlib import Path

from domain.exceptions import EvidenciaInvalidaError
from domain.ports.servicios import AlmacenamientoEvidencias

_FIRMAS = {            # firma binaria → extensión (no se confía solo en el nombre del archivo)
    b"\xff\xd8\xff": ".jpg",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"GIF8": ".gif",
}
MAX_BYTES = 5 * 1024 * 1024


def _detectar_extension(contenido: bytes) -> str | None:
    for firma, ext in _FIRMAS.items():
        if contenido.startswith(firma):
            return ext
    if contenido[:4] == b"RIFF" and contenido[8:12] == b"WEBP":
        return ".webp"
    return None


class AlmacenamientoLocal(AlmacenamientoEvidencias):
    def __init__(self, carpeta: str | Path, prefijo_url: str = "/evidencias") -> None:
        self._carpeta = Path(carpeta)
        self._carpeta.mkdir(parents=True, exist_ok=True)
        self._prefijo = prefijo_url.rstrip("/")

    def guardar(self, nombre_original: str, contenido: bytes) -> str:
        if not contenido:
            raise EvidenciaInvalidaError(f"El archivo «{nombre_original}» está vacío.")
        if len(contenido) > MAX_BYTES:
            raise EvidenciaInvalidaError(
                f"«{nombre_original}» supera el máximo de {MAX_BYTES // (1024 * 1024)} MB.")
        extension = _detectar_extension(contenido)
        if extension is None:
            raise EvidenciaInvalidaError(
                f"«{nombre_original}» no es una imagen válida (use JPG, PNG, GIF o WEBP).")
        nombre = f"{uuid.uuid4().hex}{extension}"
        (self._carpeta / nombre).write_bytes(contenido)
        return nombre

    def url_publica(self, ruta: str) -> str:
        return f"{self._prefijo}/{ruta}"
