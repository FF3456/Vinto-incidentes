"""Utilidades para mostrar incidentes en ui.table (compartidas por varias páginas)."""
from __future__ import annotations

from datetime import datetime
from typing import Callable

from nicegui import ui

from domain.entities.incidente import IncidenteAmbiental
from domain.value_objects.estado import EstadoIncidente as E
from presentation.componentes.estilos import chip_estado, chip_prioridad, fmt_fecha

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
                     pagination=filas_por_pagina).classes("w-full tabla-incidentes").props("flat")
    tabla.add_slot("body-cell-codigo", '<q-td :props="props"><span class="mono">{{ props.value }}</span></q-td>')
    tabla.add_slot("body-cell-estado", '<q-td :props="props"><span :class="\'chip chip-\' + props.row.estado_key">'
                                        '{{ props.value }}</span></q-td>')
    tabla.add_slot("body-cell-prioridad", '<q-td :props="props"><span :class="\'chip chip-\' + props.row.prioridad_key">'
                                           '{{ props.value }}</span></q-td>')
    tabla.on("rowClick", lambda e: al_abrir(e.args[1]["codigo"]))
    return tabla


def tarjeta_caso(i: IncidenteAmbiental, al_abrir: Callable[[str], None], grande: bool = False,
                 mostrar_asignado: bool = True) -> None:
    """Caso como tarjeta (alternativa a la tabla): se abre con clic, Enter o Espacio."""
    estados = list(E)
    avance = estados.index(i.estado) / (len(estados) - 1)
    vencido = i.esta_vencido(datetime.now())
    el = ui.element("div").classes(f"caso e-{i.estado.value}" + (" grande" if grande else "")) \
        .props(f'role="button" tabindex="0" aria-label="Abrir el caso {i.codigo}"')
    el.on("click", lambda _=None, cod=i.codigo: al_abrir(cod))
    el.on("keydown.enter", lambda _=None, cod=i.codigo: al_abrir(cod))
    el.on("keydown.space.prevent", lambda _=None, cod=i.codigo: al_abrir(cod))
    with el:
        with ui.row().classes("items-center gap-2 w-full justify-between no-wrap"):
            ui.label(i.codigo).classes("mono font-bold")
            with ui.row().classes("gap-1 no-wrap"):
                chip_estado(i.estado)
                if vencido:
                    ui.label("Vencido").classes("chip chip-VENCIDO")
        ui.label(i.titulo).classes("titulo")
        with ui.row().classes("items-center gap-3 text-sm").style("color:var(--suave)"):
            ui.label(i.categoria_nombre)
            ui.label(f"📍 {i.ubicacion.zona or '—'}")
        if grande:
            ui.label(i.ubicacion.referencia or "").classes("text-sm")
        ui.linear_progress(value=avance, show_value=False).props("rounded size=6px color=primary")
        with ui.row().classes("items-center justify-between w-full text-xs").style("color:var(--suave)"):
            ui.label(f"Reportado {fmt_fecha(i.fecha_reporte, con_hora=False)}")
            if mostrar_asignado:
                ui.label(i.responsable_nombre or "Sin asignar")
            if grande:
                chip_prioridad(i.prioridad)
