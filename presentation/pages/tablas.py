"""Utilidades para mostrar incidentes en ui.table (compartidas por varias páginas)."""
from __future__ import annotations

from typing import Callable

from nicegui import ui

from domain.entities.incidente import IncidenteAmbiental
from presentation.componentes.estilos import fmt_fecha

COLUMNAS = [
    {"name": "codigo", "label": "Código", "field": "codigo", "align": "left", "sortable": True},
    {"name": "titulo", "label": "Incidente", "field": "titulo", "align": "left"},
    {"name": "categoria", "label": "Categoría", "field": "categoria", "align": "left", "sortable": True},
    {"name": "zona", "label": "Zona", "field": "zona", "align": "left", "sortable": True},
    {"name": "prioridad", "label": "Prioridad", "field": "prioridad", "align": "left"},
    {"name": "estado", "label": "Estado", "field": "estado", "align": "left", "sortable": True},
    {"name": "reportado", "label": "Reportado", "field": "reportado", "align": "left", "sortable": True},
    {"name": "asignado", "label": "Asignado a", "field": "asignado", "align": "left"},
]


def fila(i: IncidenteAmbiental) -> dict:
    return {
        "codigo": i.codigo, "titulo": i.titulo, "categoria": i.categoria_nombre,
        "zona": i.ubicacion.zona or "—", "prioridad": i.prioridad.etiqueta,
        "prioridad_key": i.prioridad.value, "estado": i.estado.etiqueta, "estado_key": i.estado.value,
        "reportado": fmt_fecha(i.fecha_reporte, con_hora=False), "asignado": i.responsable_nombre or "Sin asignar",
    }


def tabla_incidentes(incidentes: list[IncidenteAmbiental], al_abrir: Callable[[str], None],
                     filas_por_pagina: int = 8, columnas: list[dict] | None = None) -> ui.table:
    tabla = ui.table(columns=columnas or COLUMNAS, rows=[fila(i) for i in incidentes], row_key="codigo",
                     pagination=filas_por_pagina).classes("w-full").props("flat")
    tabla.add_slot("body-cell-codigo", '<q-td :props="props"><span class="mono">{{ props.value }}</span></q-td>')
    tabla.add_slot("body-cell-estado", '<q-td :props="props"><span :class="\'chip chip-\' + props.row.estado_key">'
                                        '{{ props.value }}</span></q-td>')
    tabla.add_slot("body-cell-prioridad", '<q-td :props="props"><span :class="\'chip chip-\' + props.row.prioridad_key">'
                                           '{{ props.value }}</span></q-td>')
    tabla.on("rowClick", lambda e: al_abrir(e.args[1]["codigo"]))
    return tabla
