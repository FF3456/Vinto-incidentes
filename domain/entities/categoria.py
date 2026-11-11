"""Entidad Categoria (RF-02): catálogo dinámico administrable (HU-06)."""
from __future__ import annotations

from dataclasses import dataclass

from domain.exceptions import ValidacionError

PERFILES_VALIDOS = ("RESIDUOS", "AGUA", "AIRE", "RUIDO", "AREAS_VERDES", "GENERICO")


@dataclass
class Categoria:
    nombre: str
    descripcion: str = ""
    perfil: str = "GENERICO"   # selecciona la PoliticaCategoria usada por la Factory
    activa: bool = True
    id: int | None = None

    def __post_init__(self) -> None:
        self.nombre = (self.nombre or "").strip()
        if len(self.nombre) < 3:
            raise ValidacionError("El nombre de la categoría debe tener al menos 3 caracteres.")
        if self.perfil not in PERFILES_VALIDOS:
            raise ValidacionError(f"Perfil de categoría inválido: {self.perfil}.")

    def desactivar(self) -> None:
        """Las categorías nunca se eliminan: se desactivan para conservar el histórico."""
        self.activa = False

    def activar(self) -> None:
        self.activa = True
