"""Objetos de transferencia de datos entre la UI y los casos de uso."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class ArchivoSubido:
    nombre: str
    contenido: bytes


@dataclass
class ComandoRegistrarIncidente:
    categoria_id: int
    titulo: str
    descripcion: str
    fecha_incidente: datetime
    latitud: float
    longitud: float
    referencia: str
    zona: str = ""
    contacto_nombre: str = ""
    contacto_medio: str = ""
    archivos: list[ArchivoSubido] = field(default_factory=list)


@dataclass
class ZonaCritica:
    zona: str
    total: int
    abiertos: int
    porcentaje: float


@dataclass
class Estadisticas:
    total: int = 0
    pendientes: int = 0
    en_proceso: int = 0
    resueltos: int = 0
    tasa_resolucion: float = 0.0
    tiempo_medio_respuesta_h: float | None = None
    tiempo_medio_resolucion_h: float | None = None
    vencidos: int = 0
    por_estado: dict[str, int] = field(default_factory=dict)
    por_categoria: dict[str, int] = field(default_factory=dict)
    por_zona: dict[str, int] = field(default_factory=dict)
    por_mes: list[tuple[str, int, int]] = field(default_factory=list)
    zonas_criticas: list[ZonaCritica] = field(default_factory=list)
