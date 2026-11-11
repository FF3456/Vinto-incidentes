"""Consulta de la bitácora de auditoría del sistema."""
from __future__ import annotations

from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, exigir
from domain.ports.repositorios import IRepositorioAuditoria, RegistroAuditoria


class ConsultarAuditoria:
    def __init__(self, repo: IRepositorioAuditoria) -> None:
        self._repo = repo

    def ejecutar(self, actor: Actor, limite: int = 500) -> list[RegistroAuditoria]:
        exigir(actor, Permiso.VER_AUDITORIA)
        return self._repo.listar(limite)
