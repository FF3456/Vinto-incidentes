"""Paneles del personal municipal: bandeja, mapa, estadísticas, asignados (RF-05…RF-09).

Mismas funciones y casos de uso para todos; cada rol recibe su propia composición de pantalla:
  · Funcionario   → «Centro de gestión»: franja de indicadores + rail de filtros a la izquierda + listado.
  · Administrador → «Consola»: panorama con gráfico + barra de filtros horizontal + listado a ancho completo.
  · Responsable   → «Mesa de campo»: tarjetas grandes de trabajo y mapa con lista lateral.
"""
from __future__ import annotations

from datetime import date

from nicegui import background_tasks, ui

from application.dto import Estadisticas
from domain.exceptions import DominioError
from domain.ports.repositorios import FiltroIncidentes
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from presentation.componentes.detalle import abrir_detalle
from presentation.componentes.estilos import chip_estado, encabezado, fmt_horas, kpi, kpi_tira, vacio
from presentation.componentes.marco import clave_rol, marco
from presentation.componentes.mapa import CapaIncidentes, crear_mapa, leyenda_estados
from presentation.contexto import c
from presentation.guardas import requerir
from presentation.pages.tablas import tabla_incidentes, tarjeta_caso
from presentation.sesion import notificar_error

STAFF = (Rol.FUNCIONARIO, Rol.ADMINISTRADOR)
VERDES = ["#003333", "#004c4c", "#006666", "#008080", "#009999", "#00b3b3", "#00cccc"]


def _parse_fecha(texto: str) -> date | None:
    try:
        return date.fromisoformat(texto) if texto else None
    except ValueError:
        return None


# ------------------------------------------------------------------ BANDEJA (RF-05)
def _filtros(f: dict, categorias: dict, estados: dict, zonas: dict, refrescar, vertical: bool) -> list:
    """Controles de filtrado; ``vertical`` los apila (rail del funcionario) o los alinea (barra del administrador)."""
    def ancho(base: str) -> str:
        return "w-full" if vertical else base

    def cambia(clave: str):
        return lambda e: (f.__setitem__(clave, e.value if e.value is not None else ""), refrescar())

    buscar = ui.input("Buscar por código, título o referencia", on_change=cambia("texto")) \
        .props("outlined dense clearable data-testid=buscar").classes(ancho("flex-1 min-w-[240px]"))
    cat = ui.select(categorias, label="Categoría", value=0,
                    on_change=lambda e: (f.__setitem__("categoria", e.value or 0), refrescar())) \
        .props("outlined dense").classes(ancho("w-56"))
    est = ui.select(estados, label="Estado", value="", on_change=cambia("estado")) \
        .props("outlined dense").classes(ancho("w-44"))
    zon = ui.select(zonas, label="Zona", value="", on_change=cambia("zona")) \
        .props("outlined dense").classes(ancho("w-48"))
    des = ui.input("Desde", on_change=cambia("desde")).props("outlined dense type=date").classes(ancho("w-40"))
    has = ui.input("Hasta", on_change=cambia("hasta")).props("outlined dense type=date").classes(ancho("w-40"))
    return [(buscar, ""), (cat, 0), (est, ""), (zon, ""), (des, ""), (has, "")]


@ui.page("/bandeja")
def bandeja() -> None:
    actor = requerir("/bandeja", *STAFF)
    if not actor:
        return
    cont = c()
    es_admin = actor.rol == Rol.ADMINISTRADOR
    rol = clave_rol(actor)
    categorias = {0: "Todas las categorías"} | {x.id: x.nombre for x in cont.listar_categorias.ejecutar(False)}
    estados = {"": "Todos los estados"} | {e.value: e.etiqueta for e in E}
    zonas = {"": "Todas las zonas"} | {z.nombre: z.nombre for z in cont.geo.zonas()}
    f = {"categoria": 0, "estado": "", "zona": "", "desde": "", "hasta": "", "texto": ""}

    def filtro() -> FiltroIncidentes:
        return FiltroIncidentes(
            categoria_id=f["categoria"] or None, estado=E(f["estado"]) if f["estado"] else None,
            zona=f["zona"] or None, desde=_parse_fecha(f["desde"]), hasta=_parse_fecha(f["hasta"]),
            texto=f["texto"] or None)

    def abrir(cod: str) -> None:
        abrir_detalle(cod, actor, al_cambiar=lambda: (resumen.refresh(), listado.refresh()))

    with marco("Bandeja de incidentes", "/bandeja", actor):
        encabezado("Bandeja de incidentes", "Gestione y actualice el estado de los reportes ciudadanos."
                   if not es_admin else "Vista general de todos los reportes y su avance.", rol)

        @ui.refreshable
        def resumen() -> None:
            est = cont.estadisticas.ejecutar(actor)
            if es_admin:   # Consola: panorama con gráfico + indicadores en mosaico
                with ui.element("div").classes("panel-indic"):
                    with ui.card().classes("tarjeta p-4 gap-1").props("flat"):
                        ui.label("Casos por estado").classes("seccion-titulo")
                        ui.echart(_opcion_estados(est)).classes("w-full").style("height:230px")
                    with ui.element("div").classes("grid-2"):
                        kpi("Total de reportes", str(est.total), "#006666", "description")
                        kpi("Pendientes de revisión", str(est.pendientes), "#b45309", "schedule")
                        kpi("En proceso", str(est.en_proceso), "#004c4c", "engineering")
                        kpi("Resueltos", str(est.resueltos), "#008080", "check_circle")
            else:          # Centro de gestión: franja compacta
                kpi_tira([("Total de reportes", str(est.total), "#006666", "description"),
                          ("Pendientes de revisión", str(est.pendientes), "#b45309", "schedule"),
                          ("En proceso", str(est.en_proceso), "#004c4c", "engineering"),
                          ("Resueltos", str(est.resueltos), "#008080", "check_circle")])

        resumen()

        @ui.refreshable
        def listado() -> None:
            try:
                lista = cont.listar_incidentes.ejecutar(actor, filtro())
            except DominioError as e:
                return notificar_error(e)
            ui.label(f"{len(lista)} coincidencia(s)").classes("sub")
            with ui.card().classes("tarjeta w-full p-3").props("flat"):
                if lista:
                    tabla_incidentes(lista, abrir, filas_por_pagina=10 if es_admin else 8)
                else:
                    vacio("No hay incidentes con estos filtros", "Pruebe quitando algún filtro.")

        if es_admin:
            with ui.card().classes("tarjeta barra-filtros").props("flat"):
                _filtros(f, categorias, estados, zonas, lambda: listado.refresh(), vertical=False)
            listado()
        else:
            with ui.element("div").classes("rail-trabajo"):
                with ui.element("aside"):
                    with ui.card().classes("tarjeta filtros-rail").props("flat"):
                        ui.label("Filtros").classes("seccion-titulo")
                        controles = _filtros(f, categorias, estados, zonas, lambda: listado.refresh(), vertical=True)

                        def limpiar() -> None:
                            for control, valor in controles:
                                control.set_value(valor)
                        ui.button("Limpiar filtros", icon="filter_alt_off", on_click=limpiar).props("flat no-caps")
                with ui.column().classes("gap-3 min-w-0 w-full"):
                    listado()


# ------------------------------------------------------------------ MAPA (RF-08)
@ui.page("/mapa")
def mapa_incidentes() -> None:
    actor = requerir("/mapa", Rol.FUNCIONARIO, Rol.ADMINISTRADOR, Rol.RESPONSABLE)
    if not actor:
        return
    cont = c()
    es_resp = actor.rol == Rol.RESPONSABLE
    es_admin = actor.rol == Rol.ADMINISTRADOR
    titulo = "Mapa de trabajo" if es_resp else "Mapa de incidentes"
    with marco(titulo, "/mapa", actor):
        encabezado(titulo, "Ubicación geográfica de los incidentes sobre OpenStreetMap. Pulse un marcador para ver el resumen."
                   if not es_resp else "Incidentes asignados a usted.", clave_rol(actor))
        estado_sel = {"v": ""}

        def barra() -> None:
            with ui.row().classes("w-full items-center justify-between gap-3"):
                ui.select({"": "Todos los estados"} | {e.value: e.etiqueta for e in E}, value="",
                          label="Estado", on_change=lambda e: (estado_sel.update(v=e.value), pedir_refresco())) \
                    .props("outlined dense").classes("w-56")
                leyenda_estados()

        if es_resp:    # Mesa de campo: lista de trabajo a la izquierda y mapa
            with ui.element("div").classes("lista-campo"):
                with ui.column().classes("gap-2 min-w-0 w-full"):
                    titulo_lista = ui.label().classes("seccion-titulo")
                    lista_col = ui.column().classes("w-full gap-3").style("max-height:660px; overflow:auto; padding:2px 4px 8px 2px")
                with ui.card().classes("tarjeta p-4 gap-3 min-w-0").props("flat"):
                    barra()
                    mapa = crear_mapa(cont.geo, altura=620)
                    capa = CapaIncidentes(mapa)
        else:          # Funcionario: mapa + tira horizontal · Administrador: mapa alto + mosaico
            with ui.card().classes("tarjeta p-4 gap-3").props("flat"):
                barra()
                mapa = crear_mapa(cont.geo, altura=640 if es_admin else 520)
                capa = CapaIncidentes(mapa)
            titulo_lista = ui.label().classes("seccion-titulo")
            lista_col = ui.element("div").classes("grid-3" if es_admin else "tira")

        async def refrescar() -> None:
            filtro = FiltroIncidentes(estado=E(estado_sel["v"]) if estado_sel["v"] else None)
            try:
                marcadores = cont.marcadores_mapa.ejecutar(actor, filtro)
            except DominioError as e:
                return notificar_error(e)
            await capa.mostrar(marcadores)
            titulo_lista.text = f"Lista de incidentes ({len(marcadores)})"
            lista_col.clear()
            with lista_col:
                for m in marcadores:
                    el = ui.element("div").classes(f"caso e-{E(m.estado).value}" + (" grande" if es_resp else "")) \
                        .props(f'role="button" tabindex="0" aria-label="Abrir el caso {m.codigo}"')
                    el.on("click", lambda _=None, cod=m.codigo, la=m.latitud, lo=m.longitud: (
                        mapa.set_center((la, lo)), mapa.set_zoom(17),
                        abrir_detalle(cod, actor, al_cambiar=pedir_refresco)))
                    with el:
                        with ui.row().classes("w-full justify-between items-center no-wrap"):
                            ui.label(m.codigo).classes("mono font-bold")
                            chip_estado(m.estado)
                        ui.label(m.titulo).classes("titulo")
                        ui.label(m.detalle.split(" · ")[-1]).classes("sub")

        def pedir_refresco() -> None:
            background_tasks.create(refrescar())

        ui.timer(0.3, refrescar, once=True)   # dibuja los marcadores cuando el cliente ya conectó


# ------------------------------------------------------------ ESTADÍSTICAS (RF-09)
def _opcion_barras(datos: dict[str, int], color: str = "#006666") -> dict:
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
                 "itemStyle": {"color": "#003333"}, "areaStyle": {"opacity": 0.12}},
                {"name": "Atendidos", "type": "line", "smooth": True, "data": [a for _, _, a in est.por_mes],
                 "itemStyle": {"color": "#00b3b3"}}]}


def _opcion_estados(est: Estadisticas) -> dict:
    colores = {"REPORTADO": "#f59e0b", "EN_REVISION": "#3b82f6", "EN_ATENCION": "#8b5cf6",
               "ATENDIDO": "#10b981", "CERRADO": "#6b7280"}
    return {"tooltip": {"trigger": "item"}, "legend": {"bottom": 0},
            "series": [{"type": "pie", "radius": ["48%", "72%"], "center": ["50%", "44%"],
                        "label": {"formatter": "{c}"},
                        "data": [{"name": E(k).etiqueta, "value": v, "itemStyle": {"color": colores[k]}}
                                 for k, v in est.por_estado.items()]}]}


def _zonas_criticas(est: Estadisticas) -> None:
    if not est.zonas_criticas:
        ui.label("No hay casos abiertos.").classes("sub")
    for n, z in enumerate(est.zonas_criticas, 1):
        with ui.row().classes("items-center gap-3 w-full no-wrap"):
            ui.label(str(n)).classes("font-bold text-xl").style(f"color:{VERDES[n]}; font-family:var(--titulos)")
            with ui.column().classes("gap-0 flex-1"):
                ui.label(z.zona).classes("font-bold")
                ui.label(f"{z.abiertos} {'abierto' if z.abiertos == 1 else 'abiertos'} · "
                         f"{z.total} {'histórico' if z.total == 1 else 'históricos'}").classes("sub")
            ui.label(f"{z.porcentaje:.0f}%").classes("font-bold")
        ui.linear_progress(value=z.porcentaje / 100, show_value=False).props("rounded color=primary")


def _nota_tiempos() -> None:
    ui.label("Tiempo de respuesta: desde el reporte hasta el inicio de la atención en campo. "
             "Resolución: desde el reporte hasta el estado ATENDIDO.").classes("sub")


@ui.page("/estadisticas")
def estadisticas() -> None:
    actor = requerir("/estadisticas", *STAFF)
    if not actor:
        return
    est = c().estadisticas.ejecutar(actor)
    es_admin = actor.rol == Rol.ADMINISTRADOR
    with marco("Estadísticas", "/estadisticas", actor):
        encabezado("Estadísticas y análisis", "Métricas de gestión de incidentes ambientales — Municipio de Vinto.",
                   clave_rol(actor))
        if es_admin:
            _estadisticas_consola(est)
        else:
            _estadisticas_tablero(est)


def _estadisticas_tablero(est: Estadisticas) -> None:
    """Funcionario: indicador principal en anillo + indicadores, tendencia ancha y tres paneles."""
    with ui.element("div").classes("tablero"):
        with ui.card().classes("tarjeta p-6 items-center justify-center gap-3").props("flat"):
            ui.label("Tasa de resolución").classes("seccion-titulo")
            ui.html(f'<div class="anillo" style="--p:{est.tasa_resolucion:.0f}" role="img" '
                    f'aria-label="Tasa de resolución {est.tasa_resolucion:.0f} por ciento">'
                    f'<span>{est.tasa_resolucion:.0f}%</span></div>')
            ui.label(f"{est.total} incidentes registrados").classes("sub")
        with ui.element("div").classes("rejilla-kpi"):
            kpi("Total de incidentes", str(est.total), "#006666", "description")
            kpi("Casos con plazo vencido", str(est.vencidos), "#b91c1c", "warning")
            kpi("Tiempo medio de respuesta", fmt_horas(est.tiempo_medio_respuesta_h), "#004c4c", "timer")
            kpi("Tiempo medio de resolución", fmt_horas(est.tiempo_medio_resolucion_h), "#008080", "task_alt")
    _nota_tiempos()
    with ui.card().classes("tarjeta p-4 w-full").props("flat"):
        ui.label("Tendencia mensual — Reportados vs. Atendidos").classes("seccion-titulo")
        ui.echart(_opcion_tendencia(est)).classes("w-full").style("height:300px")
    with ui.element("div").classes("grid-3"):
        with ui.card().classes("tarjeta p-4").props("flat"):
            ui.label("Incidentes por estado").classes("seccion-titulo")
            ui.echart(_opcion_estados(est)).classes("w-full").style("height:300px")
        with ui.card().classes("tarjeta p-4").props("flat"):
            ui.label("Incidentes por categoría").classes("seccion-titulo")
            ui.echart(_opcion_barras(est.por_categoria)).classes("w-full").style("height:300px")
        with ui.card().classes("tarjeta p-4 gap-2").props("flat"):
            ui.label("Zonas críticas (casos abiertos)").classes("seccion-titulo")
            _zonas_criticas(est)


def _estadisticas_consola(est: Estadisticas) -> None:
    """Administrador: análisis organizado en pestañas (Resumen · Tiempos · Territorio)."""
    with ui.tabs().classes("w-full").props("align=left no-caps inline-label") as pestanas:
        t_res = ui.tab("Resumen", icon="dashboard")
        t_tie = ui.tab("Tiempos y plazos", icon="timer")
        t_ter = ui.tab("Territorio", icon="map")
    with ui.tab_panels(pestanas, value=t_res).classes("w-full").style("background:transparent"):
        with ui.tab_panel(t_res).classes("p-0 pt-4 gap-4"):
            kpi_tira([("Total de incidentes", str(est.total), "#006666", "description"),
                      ("Tasa de resolución", f"{est.tasa_resolucion:.0f}%", "#004c4c", "percent"),
                      ("Casos con plazo vencido", str(est.vencidos), "#b91c1c", "warning")])
            with ui.element("div").classes("grid-2 mt-4"):
                with ui.card().classes("tarjeta p-4").props("flat"):
                    ui.label("Incidentes por estado").classes("seccion-titulo")
                    ui.echart(_opcion_estados(est)).classes("w-full").style("height:320px")
                with ui.card().classes("tarjeta p-4").props("flat"):
                    ui.label("Incidentes por categoría").classes("seccion-titulo")
                    ui.echart(_opcion_barras(est.por_categoria)).classes("w-full").style("height:320px")
        with ui.tab_panel(t_tie).classes("p-0 pt-4 gap-4"):
            with ui.element("div").classes("grid-2"):
                kpi("Tiempo medio de respuesta", fmt_horas(est.tiempo_medio_respuesta_h), "#004c4c", "timer")
                kpi("Tiempo medio de resolución", fmt_horas(est.tiempo_medio_resolucion_h), "#008080", "task_alt")
            _nota_tiempos()
            with ui.card().classes("tarjeta p-4 w-full mt-2").props("flat"):
                ui.label("Tendencia mensual — Reportados vs. Atendidos").classes("seccion-titulo")
                ui.echart(_opcion_tendencia(est)).classes("w-full").style("height:340px")
        with ui.tab_panel(t_ter).classes("p-0 pt-4 gap-4"):
            with ui.element("div").classes("grid-2"):
                with ui.card().classes("tarjeta p-4 gap-2").props("flat"):
                    ui.label("Zonas críticas (casos abiertos)").classes("seccion-titulo")
                    _zonas_criticas(est)
                with ui.card().classes("tarjeta p-4").props("flat"):
                    ui.label("Incidentes por zona (histórico)").classes("seccion-titulo")
                    ui.echart(_opcion_barras(est.por_zona, "#00b3b3")).classes("w-full").style("height:340px")


# ------------------------------------------------------------ ASIGNADOS (HU-05)
@ui.page("/asignados")
def asignados() -> None:
    actor = requerir("/asignados", Rol.RESPONSABLE)
    if not actor:
        return
    cont = c()
    vista = {"v": "Pendientes"}
    with marco("Incidentes asignados", "/asignados", actor):
        acciones = encabezado("Incidentes asignados", "Casos a su cargo. Abra un caso para registrar la atención realizada.",
                              clave_rol(actor))
        with acciones:
            ui.toggle(["Pendientes", "Todos"], value="Pendientes",
                      on_change=lambda e: (vista.update(v=e.value), lista.refresh())) \
                .props("no-caps unelevated toggle-color=white toggle-text-color=teal-10 color=teal-9 text-color=white")

        @ui.refreshable
        def lista() -> None:
            datos = cont.incidentes_asignados.ejecutar(actor)
            pendientes = [i for i in datos if i.estado == E.EN_ATENCION]
            kpi_tira([("Asignados en total", str(len(datos)), "#006666", "assignment_ind"),
                      ("Pendientes de atender", str(len(pendientes)), "#b45309", "pending_actions"),
                      ("Atendidos / cerrados", str(len(datos) - len(pendientes)), "#008080", "check_circle")])
            visibles = sorted(pendientes if vista["v"] == "Pendientes" else datos, key=lambda i: i.fecha_limite)
            if not visibles:
                with ui.card().classes("tarjeta w-full").props("flat"):
                    vacio("No tiene incidentes asignados" if not datos else "No tiene casos pendientes",
                          "Cuando le asignen un caso aparecerá aquí." if not datos else "¡Buen trabajo! Todo está atendido.")
                return
            with ui.element("div").classes("grid-2"):
                for i in visibles:
                    tarjeta_caso(i, lambda cod: abrir_detalle(cod, actor, al_cambiar=lista.refresh), grande=True,
                                 mostrar_asignado=False)
        lista()
