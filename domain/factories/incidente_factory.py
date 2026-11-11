"""Patrón Factory: creación de incidentes según el perfil de su categoría (RF-01/RF-02).

Cada perfil de categoría aporta una ``PoliticaCategoria`` (prioridad, plazo de
atención y longitud mínima de la descripción). Para soportar un tipo nuevo de
incidente basta con registrar otra política: ``IncidenteFactory`` no se modifica
(OCP).
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from domain.entities.categoria import Categoria
from domain.entities.incidente import IncidenteAmbiental
from domain.exceptions import ValidacionError
from domain.value_objects.prioridad import Prioridad
from domain.value_objects.ubicacion import Ubicacion


class PoliticaCategoria(ABC):
    """Variación de comportamiento por tipo de incidente (Strategy)."""
    prioridad: Prioridad = Prioridad.MEDIA
    plazo_horas: int = 72
    descripcion_minima: int = 15

    def validar(self, descripcion: str) -> None:
        if len((descripcion or "").strip()) < self.descripcion_minima:
            raise ValidacionError(
                f"La descripción debe tener al menos {self.descripcion_minima} caracteres "
                f"para esta categoría.")


class PoliticaResiduos(PoliticaCategoria):
    prioridad, plazo_horas = Prioridad.MEDIA, 72


class PoliticaAgua(PoliticaCategoria):
    """Vertidos y contaminación de ríos: riesgo sanitario → atención urgente."""
    prioridad, plazo_horas, descripcion_minima = Prioridad.URGENTE, 24, 20


class PoliticaAire(PoliticaCategoria):
    prioridad, plazo_horas = Prioridad.ALTA, 48


class PoliticaRuido(PoliticaCategoria):
    prioridad, plazo_horas = Prioridad.BAJA, 120


class PoliticaAreasVerdes(PoliticaCategoria):
    prioridad, plazo_horas = Prioridad.MEDIA, 96


class PoliticaGenerica(PoliticaCategoria):
    prioridad, plazo_horas = Prioridad.MEDIA, 72


class IncidenteFactory:
    def __init__(self, politicas: dict[str, PoliticaCategoria] | None = None) -> None:
        self._politicas: dict[str, PoliticaCategoria] = politicas or {
            "RESIDUOS": PoliticaResiduos(),
            "AGUA": PoliticaAgua(),
            "AIRE": PoliticaAire(),
            "RUIDO": PoliticaRuido(),
            "AREAS_VERDES": PoliticaAreasVerdes(),
            "GENERICO": PoliticaGenerica(),
        }

    def registrar_politica(self, perfil: str, politica: PoliticaCategoria) -> None:
        """Punto de extensión (OCP): nuevos tipos sin tocar el código existente."""
        self._politicas[perfil] = politica

    def politica_de(self, categoria: Categoria) -> PoliticaCategoria:
        return self._politicas.get(categoria.perfil, self._politicas["GENERICO"])

    def crear(self, *, categoria: Categoria, codigo: str, titulo: str, descripcion: str,
              fecha_incidente: datetime, fecha_reporte: datetime, ubicacion: Ubicacion,
              reportante_id: int | None = None, contacto_nombre: str = "",
              contacto_medio: str = "") -> IncidenteAmbiental:
        if not categoria.activa:
            raise ValidacionError("La categoría seleccionada no está disponible.")
        if categoria.id is None:
            raise ValidacionError("La categoría no es válida.")
        if fecha_incidente > fecha_reporte:
            raise ValidacionError("La fecha del incidente no puede ser futura.")
        politica = self.politica_de(categoria)
        politica.validar(descripcion)
        return IncidenteAmbiental(
            codigo=codigo, titulo=titulo, descripcion=descripcion,
            categoria_id=categoria.id, categoria_nombre=categoria.nombre,
            fecha_incidente=fecha_incidente, fecha_reporte=fecha_reporte,
            ubicacion=ubicacion, prioridad=politica.prioridad,
            plazo_horas=politica.plazo_horas, reportante_id=reportante_id,
            contacto_nombre=contacto_nombre.strip(), contacto_medio=contacto_medio.strip())
