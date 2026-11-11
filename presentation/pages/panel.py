"""Paneles del personal municipal: bandeja, mapa, estadísticas, asignados (RF-05…RF-09)."""
from __future__ import annotations

from datetime import date

from nicegui import background_tasks, ui

from application.dto import Estadisticas
from domain.exceptions import DominioError
from domain.ports.repositorios import FiltroIncidentes
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from presentation.componentes.detalle import abrir_detalle
from presentation.componentes.estilos import chip_estado, fmt_fecha, fmt_horas, kpi
from presentation.componentes.marco import marco
from presentation.componentes.mapa import CapaIncidentes, crear_mapa, leyenda_estados
from presentation.contexto import c
from presentation.guardas import requerir
from presentation.pages.tablas import tabla_incidentes
from presentation.sesion import notificar_error

STAFF = (Rol.FUNCIONARIO, Rol.ADMINISTRADOR)
VERDES = ["#1b4332", "#2d6a4f", "#40916c", "#52b788", "#74c69d", "#95d5b2", "#b7e4c7"]


def _parse_fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


# ------------------------------------------------------------------ BANDEJA (RF-05)
@ui.page("/bandeja")
def bandeja() -> None:
    actor = requerir("/bandeja", *STAFF)
    if not actor:
        return
    cont = c()
    categorias = {0: "Todas las categorías"} | {x.id: x.nombre for x in cont.listar_categorias.ejecutar(False)}
    estados = {"": "Todos los estados"} | {e.value: e.etiqueta for e in E}
    zonas = {"": "Todas las zonas"} | {z.nombre: z.nombre for z in cont.geo.zonas()}
    f = {"categoria": 0, "estado": "", "zona": "", "desde": "", "hasta": "", "texto": ""}

    def filtro() -> FiltroIncidentes:
        return FiltroIncidentes(
            categoria_id=f["categoria"] or None, estado=E(f["estado"]) if f["estado"] else None,
            zona=f["zona"] or None, desde=_parse_fecha(f["desde"]), hasta=_parse_fecha(f["hasta"]),
            texto=f["texto"] or None)

    with marco("Bandeja de incidentes", "/bandeja", actor):
        ui.html('<h1 class="h">Bandeja de incidentes</h1>')
        ui.label("Gestione y actualice el estado de los reportes ciudadanos.").classes("sub")

        @ui.refreshable
        def resumen() -> None:
            est = cont.estadisticas.ejecutar(actor)
            with ui.row().classes("w-full gap-4"):
                kpi("Total de reportes", str(est.total), "#2d6a4f", "description")
                kpi("Pendientes de revisión", str(est.pendientes), "#d97706", "schedule")
                kpi("En proceso", str(est.en_proceso), "#2563eb", "engineering")
                kpi("Resueltos", str(est.resueltos), "#059669", "check_circle")

        resumen()

        with ui.card().classes("tarjeta w-full p-4 gap-3").props("flat"):
            with ui.row().classes("w-full gap-3 items-end"):
                ui.input("Buscar por código, título o referencia", on_change=lambda e: (
                    f.__setitem__("texto", e.value), listado.refresh())).props("outlined dense clearable") \
                    .classes("flex-1 min-w-[240px]").props('data-testid=buscar')
                ui.select(categorias, label="Categoría", value=0, on_change=lambda e: (
                    f.__setitem__("categoria", e.value), listado.refresh())).props("outlined dense").classes("w-56")
                ui.select(estados, label="Estado", value="", on_change=lambda e: (
                    f.__setitem__("estado", e.value), listado.refresh())).props("outlined dense").classes("w-44")
                ui.select(zonas, label="Zona", value="", on_change=lambda e: (
                    f.__setitem__("zona", e.value), listado.refresh())).props("outlined dense").classes("w-48")
                ui.input("Desde", on_change=lambda e: (f.__setitem__("desde", e.value), listado.refresh())) \
                    .props("outlined dense type=date").classes("w-40")
                ui.input("Hasta", on_change=lambda e: (f.__setitem__("hasta", e.value), listado.refresh())) \
                    .props("outlined dense type=date").classes("w-40")

            @ui.refreshable
            def listado() -> None:
                try:
                    lista = cont.listar_incidentes.ejecutar(actor, filtro())
                except DominioError as e:
                    return notificar_error(e)
                ui.label(f"{len(lista)} coincidencia(s)").classes("sub")
                tabla_incidentes(lista, lambda cod: abrir_detalle(cod, actor, al_cambiar=lambda: (
                    resumen.refresh(), listado.refresh())))
            listado()


# ------------------------------------------------------------------ MAPA (RF-08)
@ui.page("/mapa")
def mapa_incidentes() -> None:
    actor = requerir("/mapa", Rol.FUNCIONARIO, Rol.ADMINISTRADOR, Rol.RESPONSABLE)
    if not actor:
        return
    cont = c()
    es_resp = actor.rol == Rol.RESPONSABLE
    titulo = "Mapa de trabajo" if es_resp else "Mapa de incidentes"
    with marco(titulo, "/mapa", actor):
        ui.html(f'<h1 class="h">{titulo}</h1>')
        ui.label("Ubicación geográfica de los incidentes sobre OpenStreetMap. Pulse un marcador para ver el resumen."
                 if not es_resp else "Incidentes asignados a usted.").classes("sub")
        estado_sel = {"v": ""}
        with ui.row().classes("w-full gap-4 no-wrap items-start"):
            with ui.card().classes("tarjeta p-4 gap-3 flex-1").props("flat"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.select({"": "Todos los estados"} | {e.value: e.etiqueta for e in E}, value="",
                              label="Estado", on_change=lambda e: (estado_sel.update(v=e.value), pedir_refresco())) \
                        .props("outlined dense").classes("w-56")
                    leyenda_estados()
                mapa = crear_mapa(cont.geo, altura=520)
                capa = CapaIncidentes(mapa)
            with ui.column().classes("w-[340px] gap-2 gt-sm"):
                titulo_lista = ui.label().classes("font-bold text-sm").style("letter-spacing:.06em")
                lista_col = ui.column().classes("w-full gap-2").style("max-height:560px; overflow:auto")

        async def refrescar() -> None:
            filtro = FiltroIncidentes(estado=E(estado_sel["v"]) if estado_sel["v"] else None)
            try:
                marcadores = cont.marcadores_mapa.ejecutar(actor, filtro)
            except DominioError as e:
                return notificar_error(e)
            await capa.mostrar(marcadores)
            titulo_lista.text = f"LISTA DE INCIDENTES ({len(marcadores)})"
            lista_col.clear()
            with lista_col:
                for m in marcadores:
                    with ui.card().classes("tarjeta p-3 w-full cursor-pointer gap-1").props("flat") \
                            .on("click", lambda _, cod=m.codigo, la=m.latitud, lo=m.longitud: (
                                mapa.set_center((la, lo)), mapa.set_zoom(17),
                                abrir_detalle(cod, actor, al_cambiar=pedir_refresco))):
                        with ui.row().classes("w-full justify-between items-center no-wrap"):
                            ui.label(m.codigo).classes("mono")
                            chip_estado(m.estado)
                        ui.label(m.titulo).classes("text-sm font-bold")
                        ui.label(m.detalle.split(" · ")[-1]).classes("sub")

        def pedir_refresco() -> None:
            background_tasks.create(refrescar())

        ui.timer(0.3, refrescar, once=True)   # dibuja los marcadores cuando el cliente ya conectó


# ------------------------------------------------------------ ESTADÍSTICAS (RF-09)
def _opcion_barras(datos: dict[str, int], color: str = "#2d6a4f") -> dict:
    items = list(datos.items())[::-1]
    return {"grid": {"left": 150, "right": 24, "top": 8, "bottom": 24},
            "tooltip": {"trigger": "axis", "axisPointer": {"type": "shadow"}},
            "xAxis": {"type": "value", "minInterval": 1},
            "yAxis": {"type": "category", "data": [k for k, _ in items],
                      "axisLabel": {"width": 130, "overflow": "truncate"}},
            "series": [{"type": "bar", "data": [v for _, v in items], "itemStyle": {"color": color,
                        "borderRadius": [0, 4, 4, 0]}, "label": {"show": True, "position": "right"}}]}


def _opcion_tendencia(est: Estadisticas) -> dict:
    meses = [m for m, _, _ in est.por_mes]
    return {"tooltip": {"trigger": "axis"}, "legend": {"bottom": 0},
            "grid": {"left": 36, "right": 16, "top": 16, "bottom": 44},
            "xAxis": {"type": "category", "data": meses},
            "yAxis": {"type": "value", "minInterval": 1},
            "series": [
                {"name": "Reportados", "type": "line", "smooth": True, "data": [r for _, r, _ in est.por_mes],
                 "itemStyle": {"color": "#1b4332"}, "areaStyle": {"opacity": 0.12}},
                {"name": "Atendidos", "type": "line", "smooth": True, "data": [a for _, _, a in est.por_mes],
                 "itemStyle": {"color": "#52b788"}}]}


def _opcion_estados(est: Estadisticas) -> dict:
    colores = {"REPORTADO": "#f59e0b", "EN_REVISION": "#3b82f6", "EN_ATENCION": "#8b5cf6",
               "ATENDIDO": "#10b981", "CERRADO": "#6b7280"}
    return {"tooltip": {"trigger": "item"}, "legend": {"bottom": 0},
            "series": [{"type": "pie", "radius": ["48%", "72%"], "center": ["50%", "44%"],
                        "label": {"formatter": "{c}"},
                        "data": [{"name": E(k).etiqueta, "value": v, "itemStyle": {"color": colores[k]}}
                                 for k, v in est.por_estado.items()]}]}


@ui.page("/estadisticas")
def estadisticas() -> None:
    actor = requerir("/estadisticas", *STAFF)
    if not actor:
        return
    est = c().estadisticas.ejecutar(actor)
    with marco("Estadísticas", "/estadisticas", actor):
        ui.html('<h1 class="h">Estadísticas y análisis</h1>')
        ui.label("Métricas de gestión de incidentes ambientales — Municipio de Vinto.").classes("sub")
        with ui.row().classes("w-full gap-4"):
            kpi("Total de incidentes", str(est.total), "#2d6a4f", "description")
            kpi("Tasa de resolución", f"{est.tasa_resolucion:.0f}%", "#2563eb", "percent")
            kpi("Tiempo medio de respuesta", fmt_horas(est.tiempo_medio_respuesta_h), "#7c3aed", "timer")
            kpi("Tiempo medio de resolución", fmt_horas(est.tiempo_medio_resolucion_h), "#059669", "task_alt")
            kpi("Casos con plazo vencido", str(est.vencidos), "#b91c1c", "warning")
        ui.label("Tiempo de respuesta: desde el reporte hasta el inicio de la atención en campo. "
                 "Resolución: desde el reporte hasta el estado ATENDIDO.").classes("sub")

        with ui.row().classes("w-full gap-4 no-wrap items-stretch"):
            with ui.card().classes("tarjeta p-4 flex-1").props("flat"):
                ui.label("Tendencia mensual — Reportados vs. Atendidos").classes("font-bold")
                ui.echart(_opcion_tendencia(est)).classes("w-full h-72")
            with ui.card().classes("tarjeta p-4 w-[380px]").props("flat"):
                ui.label("Incidentes por estado").classes("font-bold")
                ui.echart(_opcion_estados(est)).classes("w-full h-72")
        with ui.row().classes("w-full gap-4 no-wrap items-stretch"):
            with ui.card().classes("tarjeta p-4 flex-1").props("flat"):
                ui.label("Incidentes por categoría").classes("font-bold")
                ui.echart(_opcion_barras(est.por_categoria)).classes("w-full").style("height:320px")
            with ui.card().classes("tarjeta p-4 flex-1 gap-2").props("flat"):
                ui.label("Zonas críticas (casos abiertos)").classes("font-bold")
                if not est.zonas_criticas:
                    ui.label("No hay casos abiertos.").classes("sub")
                for n, z in enumerate(est.zonas_criticas, 1):
                    with ui.row().classes("items-center gap-3 w-full no-wrap"):
                        ui.label(str(n)).classes("font-extrabold text-xl").style(f"color:{VERDES[n]}")
                        with ui.column().classes("gap-0 flex-1"):
                            ui.label(z.zona).classes("font-bold")
                            ui.label(f"{z.abiertos} {'abierto' if z.abiertos == 1 else 'abiertos'} · "
                                     f"{z.total} {'histórico' if z.total == 1 else 'históricos'}").classes("sub")
                        ui.label(f"{z.porcentaje:.0f}%").classes("font-bold")
                    ui.linear_progress(value=z.porcentaje / 100, show_value=False).props("rounded color=primary")
                ui.separator()
                ui.label("Incidentes por zona (histórico)").classes("font-bold")
                ui.echart(_opcion_barras(est.por_zona, "#52b788")).classes("w-full").style("height:200px")


# ------------------------------------------------------------ ASIGNADOS (HU-05)
@ui.page("/asignados")
def asignados() -> None:
    actor = requerir("/asignados", Rol.RESPONSABLE)
    if not actor:
        return
    cont = c()
    with marco("Incidentes asignados", "/asignados", actor):
        ui.html('<h1 class="h">Incidentes asignados</h1>')
        ui.label("Casos a su cargo. Abra un caso para registrar la atención realizada.").classes("sub")

        @ui.refreshable
        def lista() -> None:
            datos = cont.incidentes_asignados.ejecutar(actor)
            pendientes = [i for i in datos if i.estado == E.EN_ATENCION]
            with ui.row().classes("w-full gap-4"):
                kpi("Asignados en total", str(len(datos)), "#2d6a4f", "assignment_ind")
                kpi("Pendientes de atender", str(len(pendientes)), "#d97706", "pending_actions")
                kpi("Atendidos / cerrados", str(len(datos) - len(pendientes)), "#059669", "check_circle")
            with ui.card().classes("tarjeta w-full p-3").props("flat"):
                if not datos:
                    ui.label("No tiene incidentes asignados.").classes("sub")
                else:
                    tabla_incidentes(datos, lambda cod: abrir_detalle(cod, actor, al_cambiar=lista.refresh))
        lista()
