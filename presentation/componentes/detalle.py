"""Detalle de un incidente + acciones de gestión según el rol (RF-05, RF-06, RF-07, HU-05)."""
from __future__ import annotations

import html
from datetime import datetime
from typing import Callable

from nicegui import context, events, ui

from application.dto import ArchivoSubido
from domain.entities.incidente import IncidenteAmbiental
from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, puede, puede_transicionar
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from presentation.componentes.estilos import chip_estado, chip_prioridad, fmt_fecha
from presentation.componentes.mapa import mapa_puntual
from presentation.contexto import c
from presentation.sesion import notificar_error


def _progreso(i: IncidenteAmbiental) -> None:
    estados = list(E)
    idx = estados.index(i.estado)
    with ui.row().classes("items-center gap-2 flex-wrap"):
        for n, e in enumerate(estados):
            clase = "hecho" if n < idx or (n == idx and e == E.CERRADO) else ("actual" if n == idx else "")
            with ui.element("div").classes(f"paso {clase}"):
                ui.html(f'<div class="c">{"✓" if clase == "hecho" else n + 1}</div>')
                ui.label(e.etiqueta).classes("text-sm" + (" font-bold" if n == idx else ""))
            if n < len(estados) - 1:
                ui.element("div").style("width:22px;height:2px;background:#cfe3d7")


def _subida(archivos: list[ArchivoSubido], maximo: int = 3):
    async def al_subir(e: events.UploadEventArguments) -> None:
        if len(archivos) >= maximo:
            ui.notify(f"Máximo {maximo} fotografías.", type="warning")
            return
        archivos.append(ArchivoSubido(e.file.name, await e.file.read()))
    return ui.upload(on_upload=al_subir, auto_upload=True, multiple=True, max_files=maximo,
                     max_file_size=5 * 1024 * 1024, label="Adjuntar foto (JPG/PNG, máx. 5 MB)") \
        .props("accept=image/* flat bordered").classes("w-full")


def _acciones(i: IncidenteAmbiental, actor: Actor, al_cambiar: Callable[[], None]) -> None:
    cont = c()
    obs = None

    def ejecutar(fn, mensaje: str) -> None:
        try:
            fn()
            ui.notify(mensaje, type="positive", position="top")
            al_cambiar()
        except Exception as e:  # noqa: BLE001 - se traduce a mensaje de usuario
            notificar_error(e)

    gestiona = puede(actor, Permiso.CAMBIAR_ESTADO)
    atiende = puede(actor, Permiso.REGISTRAR_ATENCION)
    if not (gestiona or atiende):
        return
    if i.estado == E.CERRADO:
        return

    with ui.card().classes("tarjeta w-full gap-3 p-4").props("flat"):
        ui.label("Gestión del caso").classes("font-bold")

        if i.estado == E.REPORTADO and gestiona and puede_transicionar(actor, E.EN_REVISION):
            obs = ui.input("Observación (opcional)").props("outlined dense").classes("w-full")
            ui.button("Pasar a revisión", icon="visibility", on_click=lambda: ejecutar(
                lambda: cont.cambiar_estado.ejecutar(actor, i.codigo, E.EN_REVISION, obs.value),
                "El caso pasó a EN REVISIÓN")).props("unelevated no-caps color=primary")

        if i.estado in (E.EN_REVISION, E.EN_ATENCION) and puede(actor, Permiso.ASIGNAR_RESPONSABLE):
            responsables = cont.listar_responsables.ejecutar(actor)
            opciones = {r.id: f"{r.nombre} — {r.unidad}" for r in responsables}
            sel = ui.select(opciones, label="Responsable / cuadrilla", value=i.responsable_id) \
                .props("outlined dense").classes("w-full")
            obs = ui.input("Observación (opcional)").props("outlined dense").classes("w-full")

            def asignar() -> None:
                if sel.value is None:
                    ui.notify("Seleccione un responsable.", type="warning")
                    return
                ejecutar(lambda: cont.asignar_responsable.ejecutar(actor, i.codigo, sel.value, obs.value),
                         "Responsable asignado")
            txt = "Asignar y pasar a atención" if i.estado == E.EN_REVISION else "Reasignar responsable"
            ui.button(txt, icon="assignment_ind", on_click=asignar).props("unelevated no-caps color=primary")

        if i.estado == E.EN_ATENCION and atiende:
            propio = actor.rol != Rol.RESPONSABLE or i.codigo in {
                x.codigo for x in cont.incidentes_asignados.ejecutar(actor)}
            if propio:
                ui.separator()
                ui.label("Registrar atención realizada").classes("text-sm font-bold")
                resumen = ui.textarea("Resumen de la intervención").props("outlined dense autogrow") \
                    .classes("w-full")
                archivos: list[ArchivoSubido] = []
                _subida(archivos)
                ui.button("Marcar como atendido", icon="task_alt", on_click=lambda: ejecutar(
                    lambda: cont.registrar_atencion.ejecutar(actor, i.codigo, resumen.value, archivos),
                    "Atención registrada: caso ATENDIDO")).props("unelevated no-caps color=positive")

        if i.estado == E.ATENDIDO and gestiona and puede_transicionar(actor, E.CERRADO):
            obs = ui.input("Observación de cierre").props("outlined dense").classes("w-full")
            ui.button("Verificar y cerrar caso", icon="lock", on_click=lambda: ejecutar(
                lambda: cont.cambiar_estado.ejecutar(actor, i.codigo, E.CERRADO, obs.value or "Cierre verificado"),
                "Caso CERRADO")).props("unelevated no-caps color=primary")


def render_detalle(i: IncidenteAmbiental, actor: Actor, al_cambiar: Callable[[], None]) -> None:
    cont = c()
    ahora_vencido = i.esta_vencido(datetime.now())
    with ui.row().classes("items-center gap-2 w-full flex-wrap"):
        ui.label(i.codigo).classes("mono font-bold text-base")
        chip_estado(i.estado)
        chip_prioridad(i.prioridad)
        if ahora_vencido:
            ui.label("Plazo vencido").classes("chip chip-VENCIDO")
    ui.label(i.titulo).classes("text-xl font-extrabold")
    _progreso(i)
    ui.label(i.descripcion).classes("text-sm")

    with ui.grid(columns=2).classes("w-full gap-x-6 gap-y-1 text-sm"):
        for etiqueta, valor in [
            ("Categoría", i.categoria_nombre), ("Zona", i.ubicacion.zona or "—"),
            ("Referencia", i.ubicacion.referencia or "—"),
            ("Coordenadas", f"{i.ubicacion.latitud:.5f}, {i.ubicacion.longitud:.5f}"),
            ("Ocurrió", fmt_fecha(i.fecha_incidente)), ("Reportado", fmt_fecha(i.fecha_reporte)),
            ("Última actualización", fmt_fecha(i.fecha_actualizacion)),
            ("Plazo de atención", f"{i.plazo_horas} h (hasta {fmt_fecha(i.fecha_limite)})"),
            ("Responsable", i.responsable_nombre or "Sin asignar"),
        ]:
            ui.html(f'<span style="color:#5b7a6a">{etiqueta}:</span> <b>{_esc(valor)}</b>')
        if actor.rol != Rol.CIUDADANO and (i.contacto_nombre or i.contacto_medio):
            ui.html(f'<span style="color:#5b7a6a">Contacto:</span> '
                    f'<b>{_esc(i.contacto_nombre)} {_esc(i.contacto_medio)}</b>')

    if i.resumen_atencion:
        with ui.card().classes("tarjeta w-full p-3").props("flat"):
            ui.label("Resumen de la atención").classes("text-sm font-bold")
            ui.label(i.resumen_atencion).classes("text-sm")

    if i.evidencias:
        ui.label("Evidencia fotográfica").classes("font-bold")
        with ui.row().classes("gap-3"):
            for ev in i.evidencias:
                with ui.column().classes("gap-0 items-center"):
                    ui.image(cont.almacen.url_publica(ev.ruta_archivo)).classes("w-40 h-28 rounded-lg") \
                        .props("fit=cover")
                    ui.label("Atención" if ev.tipo == "ATENCION" else "Reporte").classes("text-xs text-grey-7")

    mapa_puntual(cont.geo, i.ubicacion.latitud, i.ubicacion.longitud)

    ui.label("Historial de estados").classes("font-bold")
    with ui.column().classes("linea gap-3"):
        for h in i.historial:
            with ui.element("div").classes("relative"):
                ui.element("div").classes("punto")
                with ui.row().classes("items-center gap-2"):
                    chip_estado(h.estado_nuevo)
                    ui.label(fmt_fecha(h.fecha)).classes("text-xs text-grey-7")
                    ui.label(f"por {h.usuario_nombre}").classes("text-xs text-grey-7")
                if h.observacion:
                    ui.label(h.observacion).classes("text-sm")

    _acciones(i, actor, al_cambiar)


def _esc(texto: str) -> str:
    return html.escape(str(texto or ""))


def abrir_detalle(codigo: str, actor: Actor, al_cambiar: Callable[[], None] | None = None) -> None:
    """Abre el detalle en un diálogo; tras cada acción se re-renderiza y avisa a la página."""
    # El diálogo se crea en la raíz del cliente: si colgara de un contenedor ``@ui.refreshable``
    # (p. ej. el listado), se destruiría al refrescar la tabla tras cambiar el estado del caso.
    with context.client.content, ui.dialog().props("maximized=false") as dlg, \
            ui.card().classes("w-[900px] max-w-[95vw] max-h-[92vh] overflow-auto gap-3"):
        @ui.refreshable
        def contenido() -> None:
            try:
                render_detalle(c().consultar_por_codigo.ejecutar(actor, codigo), actor, cambiado)
            except Exception as e:  # noqa: BLE001
                notificar_error(e)

        def cambiado() -> None:
            contenido.refresh()
            if al_cambiar:
                al_cambiar()

        with ui.row().classes("w-full justify-end"):
            ui.button(icon="close", on_click=dlg.close).props("flat round dense")
        contenido()
    dlg.open()
