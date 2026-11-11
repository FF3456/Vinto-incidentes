"""Páginas públicas y de ciudadano: inicio, reporte, seguimiento, acceso (RF-01…RF-04, RF-13)."""
from __future__ import annotations

import os
from datetime import datetime

from nicegui import events, ui

from application.dto import ArchivoSubido, ComandoRegistrarIncidente
from domain.entities.incidente import IncidenteAmbiental
from domain.exceptions import DominioError
from domain.value_objects.rol import Rol
from infrastructure.database.seed import PASS_DEMO, USUARIOS
from presentation.componentes.detalle import abrir_detalle, render_detalle
from presentation.componentes.estilos import fmt_fecha
from presentation.componentes.marco import marco
from presentation.componentes.mapa import SelectorUbicacion
from presentation.contexto import c
from presentation.pages.tablas import tabla_incidentes
from presentation.sesion import (
    actor_actual, autenticado, iniciar_sesion, notificar_error, ruta_inicial)


# ------------------------------------------------------------------ INICIO
@ui.page("/")
def inicio() -> None:
    actor = actor_actual()
    if autenticado() and actor.rol != Rol.CIUDADANO:
        ui.navigate.to(ruta_inicial(actor.rol))
        return
    with marco("Inicio", "/", actor):
        with ui.element("div").classes("hero w-full"):
            ui.html("<h1>Reporte de incidentes medio ambientales<br>en el Municipio de Vinto</h1>")
            ui.label("Informe basura, vertidos, quemas o contaminación de ríos con su ubicación y una foto. "
                     "Recibirá un código para seguir la atención de su reporte.").classes("text-base mb-4") \
                .style("max-width:640px; opacity:.95")
            with ui.row().classes("gap-3"):
                ui.button("Reportar incidente", icon="add_location_alt",
                          on_click=lambda: ui.navigate.to("/reportar")).props("unelevated no-caps color=white text-color=green-9")
                ui.button("Consultar mi reporte", icon="search",
                          on_click=lambda: ui.navigate.to("/seguimiento")).props("outline no-caps color=white")
        with ui.row().classes("w-full gap-4"):
            for icono, t, d in [
                ("edit_note", "1. Registre", "Elija la categoría, describa lo ocurrido y marque el punto en el mapa."),
                ("photo_camera", "2. Adjunte evidencia", "Suba fotografías para que el personal municipal verifique el caso."),
                ("track_changes", "3. Haga seguimiento", "Con su código consulte el estado: revisión, atención y cierre."),
            ]:
                with ui.card().classes("tarjeta p-5 flex-1 min-w-[240px] gap-1").props("flat"):
                    ui.icon(icono).classes("text-3xl").style("color:#2d6a4f")
                    ui.label(t).classes("font-bold text-base")
                    ui.label(d).classes("sub")


# ------------------------------------------------------------ REPORTAR (RF-01..04)
@ui.page("/reportar")
def reportar() -> None:
    actor = actor_actual()
    cont = c()
    with marco("Reportar incidente", "/reportar", actor):
        ui.html('<h1 class="h">Reportar un incidente</h1>')
        ui.label("Complete los cuatro pasos. Los campos con * son obligatorios.").classes("sub")

        categorias = {x.id: x.nombre for x in cont.listar_categorias.ejecutar()}
        zonas = [z.nombre for z in cont.geo.zonas()]
        archivos: list[ArchivoSubido] = []

        with ui.card().classes("tarjeta w-full max-w-[880px] mx-auto p-6").props("flat"):
            with ui.stepper().props("flat animated").classes("w-full") as paso:
                # ---------------- Paso 1: información
                with ui.step("Información", icon="description"):
                    categoria = ui.select(categorias, label="Categoría del incidente *").props("outlined") \
                        .classes("w-full").props('data-testid=categoria')
                    titulo = ui.input("Título breve *").props("outlined maxlength=120 counter").classes("w-full")
                    descripcion = ui.textarea("Descripción detallada *") \
                        .props("outlined maxlength=500 counter autogrow").classes("w-full")
                    fecha = ui.input("Fecha y hora del incidente *",
                                     value=datetime.now().strftime("%Y-%m-%dT%H:%M")) \
                        .props("outlined type=datetime-local").classes("w-full")
                    with ui.stepper_navigation():
                        def paso1() -> None:
                            if not categoria.value:
                                return ui.notify("Seleccione una categoría.", type="warning")
                            if len((titulo.value or "").strip()) < 5:
                                return ui.notify("Escriba un título de al menos 5 caracteres.", type="warning")
                            if len((descripcion.value or "").strip()) < 15:
                                return ui.notify("La descripción debe tener al menos 15 caracteres.", type="warning")
                            if not fecha.value:
                                return ui.notify("Indique la fecha y hora.", type="warning")
                            paso.next()
                        ui.button("Siguiente", on_click=paso1).props("unelevated no-caps color=primary icon-right=chevron_right")

                # ---------------- Paso 2: ubicación
                with ui.step("Ubicación", icon="place"):
                    ui.label("Haga clic en el mapa para marcar el lugar exacto (o ingrese las coordenadas).") \
                        .classes("text-sm mb-2")
                    with ui.row().classes("w-full gap-3 no-wrap items-start"):
                        lat = ui.number("Latitud *", format="%.6f", step=0.0001).props("outlined dense").classes("flex-1")
                        lon = ui.number("Longitud *", format="%.6f", step=0.0001).props("outlined dense").classes("flex-1")
                        zona = ui.select(zonas, label="Zona").props("outlined dense").classes("flex-1")

                    def elegido(la: float, lo: float) -> None:
                        lat.value, lon.value = round(la, 6), round(lo, 6)
                        zona.value = cont.geo.zona_para(la, lo)
                    selector = SelectorUbicacion(cont.geo, elegido)

                    def manual() -> None:
                        if lat.value is not None and lon.value is not None:
                            selector.fijar(lat.value, lon.value)
                            zona.value = cont.geo.zona_para(lat.value, lon.value)
                    lat.on_value_change(manual)
                    lon.on_value_change(manual)
                    referencia = ui.input("Referencia del lugar * (calle, barrio, punto conocido)") \
                        .props("outlined").classes("w-full mt-3")
                    with ui.stepper_navigation():
                        def paso2() -> None:
                            if lat.value is None or lon.value is None:
                                return ui.notify("Marque la ubicación en el mapa.", type="warning")
                            if not cont.geo.coordenadas_validas(lat.value, lon.value):
                                return ui.notify("La ubicación está fuera del área de Vinto.", type="warning")
                            if len((referencia.value or "").strip()) < 3:
                                return ui.notify("Indique una referencia del lugar.", type="warning")
                            paso.next()
                        ui.button("Anterior", on_click=paso.previous).props("flat no-caps")
                        ui.button("Siguiente", on_click=paso2).props("unelevated no-caps color=primary icon-right=chevron_right")

                # ---------------- Paso 3: evidencia
                with ui.step("Evidencia", icon="photo_camera"):
                    ui.label("Adjunte hasta 3 fotografías del incidente (opcional pero recomendado).").classes("text-sm mb-2")

                    async def al_subir(e: events.UploadEventArguments) -> None:
                        if len(archivos) >= 3:
                            return ui.notify("Máximo 3 fotografías.", type="warning")
                        archivos.append(ArchivoSubido(e.file.name, await e.file.read()))
                        ui.notify(f"«{e.file.name}» listo para enviar.", type="positive")
                    ui.upload(on_upload=al_subir, auto_upload=True, multiple=True, max_files=3,
                              max_file_size=5 * 1024 * 1024,
                              on_rejected=lambda: ui.notify("Archivo rechazado: use imágenes de hasta 5 MB.", type="warning"),
                              label="Arrastre o seleccione imágenes (JPG, PNG, WEBP · máx. 5 MB)") \
                        .props("accept=image/* flat bordered").classes("w-full")
                    with ui.stepper_navigation():
                        ui.button("Anterior", on_click=paso.previous).props("flat no-caps")
                        ui.button("Siguiente", on_click=paso.next).props("unelevated no-caps color=primary icon-right=chevron_right")

                # ---------------- Paso 4: contacto y envío
                with ui.step("Contacto y envío", icon="send"):
                    ui.label("Sus datos de contacto ayudan al personal a pedirle información adicional (opcional).") \
                        .classes("text-sm mb-2")
                    c_nombre = ui.input("Nombre", value=actor.nombre if autenticado() else "").props("outlined").classes("w-full")
                    c_medio = ui.input("Teléfono o correo").props("outlined").classes("w-full")
                    with ui.stepper_navigation():
                        def enviar() -> None:
                            try:
                                cmd = ComandoRegistrarIncidente(
                                    categoria_id=categoria.value or 0, titulo=titulo.value or "",
                                    descripcion=descripcion.value or "",
                                    fecha_incidente=datetime.fromisoformat(fecha.value),
                                    latitud=float(lat.value), longitud=float(lon.value),
                                    referencia=referencia.value or "", zona=zona.value or "",
                                    contacto_nombre=c_nombre.value or "", contacto_medio=c_medio.value or "",
                                    archivos=list(archivos))
                                creado = cont.registrar_incidente.ejecutar(actor, cmd)
                            except (DominioError, ValueError, TypeError) as e:
                                if isinstance(e, DominioError):
                                    notificar_error(e)
                                else:
                                    ui.notify("Revise los datos ingresados.", type="negative")
                                return
                            _exito(creado)
                        ui.button("Anterior", on_click=paso.previous).props("flat no-caps")
                        ui.button("Enviar reporte", icon="send", on_click=enviar).props("unelevated no-caps color=primary") \
                            .props("data-testid=enviar")


def _exito(i: IncidenteAmbiental) -> None:
    with ui.dialog().props("persistent") as dlg, ui.card().classes("p-6 items-center gap-2 w-[420px] max-w-[92vw]"):
        ui.icon("check_circle").classes("text-6xl").style("color:#10b981")
        ui.label("¡Reporte enviado!").classes("text-xl font-extrabold")
        ui.label("Guarde este código para consultar el estado de su reporte:").classes("text-sm text-center")
        ui.label(i.codigo).classes("mono text-2xl font-bold").props("data-testid=codigo-generado")
        ui.label(f"Prioridad asignada: {i.prioridad.etiqueta} · plazo {i.plazo_horas} h").classes("sub")
        with ui.row().classes("gap-2 mt-2"):
            ui.button("Copiar código", icon="content_copy", on_click=lambda: (
                ui.clipboard.write(i.codigo), ui.notify("Código copiado"))).props("flat no-caps")
            ui.button("Ver seguimiento", icon="track_changes",
                      on_click=lambda: ui.navigate.to(f"/seguimiento?codigo={i.codigo}")).props("unelevated no-caps color=primary")
    dlg.open()


# ------------------------------------------------------------ SEGUIMIENTO (RF-13)
@ui.page("/seguimiento")
def seguimiento(codigo: str = "") -> None:
    actor = actor_actual()
    with marco("Seguimiento", "/seguimiento", actor):
        ui.html('<h1 class="h">Seguimiento de reporte</h1>')
        ui.label("Ingrese el código que recibió al enviar su reporte (por ejemplo VINTO-2026-0001).").classes("sub")
        entrada = ui.input("Código de seguimiento", value=codigo).props("outlined dense data-testid=codigo") \
            .classes("w-full max-w-[420px]")

        @ui.refreshable
        def resultado() -> None:
            if not (entrada.value or "").strip():
                return
            try:
                i = c().consultar_por_codigo.ejecutar(actor, entrada.value)
            except DominioError as e:
                with ui.card().classes("tarjeta p-5 w-full max-w-[880px]").props("flat"):
                    ui.icon("search_off").classes("text-3xl text-grey-6")
                    ui.label(str(e)).classes("text-sm")
                return
            with ui.card().classes("tarjeta p-6 w-full max-w-[880px] gap-3").props("flat"):
                render_detalle(i, actor, resultado.refresh)

        ui.button("Consultar", icon="search", on_click=resultado.refresh).props("unelevated no-caps color=primary") \
            .props("data-testid=consultar")
        entrada.on("keydown.enter", resultado.refresh)
        resultado()


# ------------------------------------------------------------------ MIS REPORTES
@ui.page("/mis-reportes")
def mis_reportes() -> None:
    actor = actor_actual()
    if not autenticado():
        ui.navigate.to("/login?next=/mis-reportes")
        return
    with marco("Mis reportes", "/mis-reportes", actor):
        ui.html('<h1 class="h">Mis reportes</h1>')
        try:
            lista = c().mis_reportes.ejecutar(actor)
        except DominioError as e:
            ui.label(str(e))
            return
        if not lista:
            ui.label("Aún no ha enviado reportes con esta cuenta.").classes("sub")
            return
        with ui.card().classes("tarjeta w-full p-3").props("flat"):
            tabla_incidentes(lista, lambda cod: abrir_detalle(cod, actor))


# ----------------------------------------------------------------- LOGIN / REGISTRO
@ui.page("/login")
def login(next: str = "") -> None:  # noqa: A002 - nombre del parámetro de consulta
    actor = actor_actual()
    with marco("Ingresar", "/login", actor):
        with ui.card().classes("tarjeta p-6 w-[420px] max-w-full mx-auto gap-3").props("flat"):
            ui.label("Iniciar sesión").classes("text-xl font-extrabold")
            correo = ui.input("Correo electrónico").props("outlined dense data-testid=correo").classes("w-full")
            clave = ui.input("Contraseña", password=True, password_toggle_button=True) \
                .props("outlined dense data-testid=clave").classes("w-full")

            def entrar() -> None:
                try:
                    a = c().autenticar.ejecutar(correo.value, clave.value)
                except DominioError as e:
                    return notificar_error(e)
                iniciar_sesion(a)
                ui.navigate.to(next if next.startswith("/") else ruta_inicial(a.rol))
            clave.on("keydown.enter", entrar)
            ui.button("Ingresar", icon="login", on_click=entrar).props("unelevated no-caps color=primary data-testid=ingresar").classes("w-full")
            ui.link("¿No tiene cuenta? Regístrese como ciudadano", "/registro").classes("text-sm")
            ui.link("Continuar sin cuenta: reportar incidente", "/reportar").classes("text-sm")
            if os.getenv("VINTO_DEMO", "1") == "1":
                with ui.expansion("Cuentas de demostración", icon="info").classes("w-full text-sm"):
                    ui.label(f"Contraseña de todas: {PASS_DEMO}").classes("mono")
                    for nombre, mail, rol, _ in USUARIOS:
                        ui.label(f"{rol.etiqueta}: {mail}").classes("mono")


@ui.page("/registro")
def registro() -> None:
    actor = actor_actual()
    with marco("Registro", "/registro", actor):
        with ui.card().classes("tarjeta p-6 w-[420px] max-w-full mx-auto gap-3").props("flat"):
            ui.label("Crear cuenta de ciudadano").classes("text-xl font-extrabold")
            nombre = ui.input("Nombre completo").props("outlined dense").classes("w-full")
            correo = ui.input("Correo electrónico").props("outlined dense").classes("w-full")
            clave = ui.input("Contraseña (mín. 6 caracteres)", password=True, password_toggle_button=True) \
                .props("outlined dense").classes("w-full")

            def crear() -> None:
                try:
                    a = c().registrar_ciudadano.ejecutar(nombre.value, correo.value, clave.value)
                except DominioError as e:
                    return notificar_error(e)
                iniciar_sesion(a)
                ui.notify("Cuenta creada", type="positive")
                ui.navigate.to("/")
            ui.button("Crear cuenta", icon="person_add", on_click=crear).props("unelevated no-caps color=primary").classes("w-full")
            ui.link("Ya tengo cuenta", "/login").classes("text-sm")
