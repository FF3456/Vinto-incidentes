"""Adaptador de hashing de contraseñas (PBKDF2-HMAC-SHA256, solo biblioteca estándar)."""
from __future__ import annotations

import base64
import hashlib
import hmac
import os

from domain.ports.servicios import HasheadorPassword

_ITERACIONES = 200_000


class HasheadorPBKDF2(HasheadorPassword):
    def __init__(self, iteraciones: int = _ITERACIONES) -> None:
        self._it = iteraciones

    def hashear(self, password: str) -> str:
        sal = os.urandom(16)
        h = hashlib.pbkdf2_hmac("sha256", password.encode(), sal, self._it)
        return f"pbkdf2${self._it}${base64.b64encode(sal).decode()}${base64.b64encode(h).decode()}"

    def verificar(self, password: str, hash_guardado: str) -> bool:
        try:
            _, it, sal, h = hash_guardado.split("$")
            calculado = hashlib.pbkdf2_hmac("sha256", password.encode(), base64.b64decode(sal), int(it))
            return hmac.compare_digest(calculado, base64.b64decode(h))
        except (ValueError, TypeError):
            return False
