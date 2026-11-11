"""Puertos de salida de persistencia (DIP).

Los casos de uso dependen de estas abstracciones; SQLAlchemy es solo uno de
los adaptadores posibles (también existe uno en memoria para las pruebas).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date, datetime

from domain.entities.categoria import Categoria
from domain.entities.incidente import IncidenteAmbiental
from domain.entities.responsable import Responsable
from domain.entities.usuario import Usuario
from domain.value_objects.estado import EstadoIncidente


@dataclass
class FiltroIncidentes:
    """Criterios combinables de consulta (RF-05, HU-04)."""
    categoria_id: int | None = None
    estado: EstadoIncidente | None = None
    zona: str | None = None
    desde: date | None = None
    hasta: date | None = None
    texto: str | None = None
    responsable_id: int | None = None
    reportante_id: int | None = None


@dataclass
class RegistroAuditoria:
    fecha: datetime
    usuario_nombre: str
    accion: str
    recurso: str
    detalle: str = ""
    id: int | None = None


class IRepositorioIncidentes(ABC):
    @abstractmethod
    def guardar(self, incidente: IncidenteAmbiental) -> IncidenteAmbiental: ...

    @abstractmethod
    def buscar_por_id(self, incidente_id: int) -> IncidenteAmbiental | None: ...

    @abstractmethod
    def buscar_por_codigo(self, codigo: str) -> IncidenteAmbiental | None: ...

    @abstractmethod
    def listar(self, filtro: FiltroIncidentes | None = None) -> list[IncidenteAmbiental]: ...

    @abstractmethod
    def contar_del_anio(self, anio: int) -> int: ...


class IRepositorioUsuarios(ABC):
    @abstractmethod
    def guardar(self, usuario: Usuario) -> Usuario: ...

    @abstractmethod
    def buscar_por_id(self, usuario_id: int) -> Usuario | None: ...

    @abstractmethod
    def buscar_por_correo(self, correo: str) -> Usuario | None: ...

    @abstractmethod
    def listar(self) -> list[Usuario]: ...


class IRepositorioCategorias(ABC):
    @abstractmethod
    def guardar(self, categoria: Categoria) -> Categoria: ...

    @abstractmethod
    def buscar_por_id(self, categoria_id: int) -> Categoria | None: ...

    @abstractmethod
    def buscar_por_nombre(self, nombre: str) -> Categoria | None: ...

    @abstractmethod
    def listar(self, solo_activas: bool = False) -> list[Categoria]: ...


class IRepositorioResponsables(ABC):
    @abstractmethod
    def guardar(self, responsable: Responsable) -> Responsable: ...

    @abstractmethod
    def buscar_por_id(self, responsable_id: int) -> Responsable | None: ...

    @abstractmethod
    def buscar_por_usuario(self, usuario_id: int) -> Responsable | None: ...

    @abstractmethod
    def listar(self, solo_activos: bool = False) -> list[Responsable]: ...


class IRepositorioAuditoria(ABC):
    @abstractmethod
    def registrar(self, registro: RegistroAuditoria) -> None: ...

    @abstractmethod
    def listar(self, limite: int = 500) -> list[RegistroAuditoria]: ...
