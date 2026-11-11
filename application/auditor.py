"""Servicio de aplicación que deja huella de las acciones relevantes."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from domain.policies.actor import Actor
from domain.ports.repositorios import IRepositorioAuditoria, RegistroAuditoria


class Auditor:
    def __init__(self, repo: IRepositorioAuditoria, reloj: Callable[[], datetime] = datetime.now):
        self._repo = repo
        self._reloj = reloj

    def registrar(self, actor: Actor, accion: str, recurso: str, detalle: str = "") -> None:
        self._repo.registrar(RegistroAuditoria(
            fecha=self._reloj(), usuario_nombre=actor.nombre,
            accion=accion, recurso=recurso, detalle=detalle))
