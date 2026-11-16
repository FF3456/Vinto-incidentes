"""Páginas públicas y de ciudadano: inicio, reporte, seguimiento, acceso (RF-01…RF-04, RF-13)."""
from __future__ import annotations

import os
from contextlib import contextmanager
from datetime import datetime
from urllib.parse import quote

from nicegui import events, ui

from application.dto import ArchivoSubido, ComandoRegistrarIncidente
from domain.entities.incidente import IncidenteAmbiental
from domain.exceptions import DominioError
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from infrastructure.database.seed import PASS_DEMO, USUARIOS
from presentation.componentes.detalle import abrir_detalle, render_detalle
from presentation.componentes.estilos import encabezado, kpi_tira, vacio
from presentation.componentes.marco import clave_rol, marco
from presentation.componentes.mapa import SelectorUbicacion
from presentation.contexto import c
from presentation.pages.tablas import tarjeta_caso
from presentation.sesion import (
    actor_actual, autenticado, iniciar_sesion, notificar_error, ruta_inicial)


# ------------------------------------------------------------------ INICIO
_ICONOS_CATEGORIA = [("basura", "delete_sweep"), ("residuo", "delete_sweep"), ("vertido", "water_drop"),
                     ("río", "water"), ("residual", "water_drop"), ("quema", "local_fire_department"),
                     ("aire", "air"), ("verde", "park"), ("acústica", "volume_up"), ("ruido", "volume_up"),
                     ("animal", "pets")]


def _icono_categoria(nombre: str) -> str:
    n = nombre.lower()
    return next((ic for clave, ic in _ICONOS_CATEGORIA if clave in n), "eco")


@ui.page("/")
def inicio() -> None:
    actor = actor_actual()
    if autenticado() and actor.rol != Rol.CIUDADANO:
        ui.navigate.to(ruta_inicial(actor.rol))
        return
    with marco("Inicio", "/", actor):
        with ui.element("div").classes("bento"):
            # ---- Bloque principal (8 columnas)
            with ui.element("div").classes("hero b-8"):
                for izq, retraso in [(10, 0), (30, 3), (50, 6), (70, 1.5), (88, 4.5)]:
                    ui.element("span").classes("hoja-flota").props('aria-hidden="true"') \
                        .style(f"left:{izq}%; top:0; animation-delay:{retraso}s")
                with ui.row().classes("insignia items-center gap-2"):
                    ui.icon("park").props('aria-hidden="true"')
                    ui.label(f"Hola, {actor.nombre.split(' ')[0]}" if autenticado() else "Cuidemos juntos el entorno de Vinto")
                ui.html("<h1>Reporte de incidentes medio ambientales en el Municipio de Vinto</h1>")
                ui.label("Informe basura, vertidos, quemas o contaminación de ríos con su ubicación y una foto. "
                         "Recibirá un código para seguir la atención de su reporte.").classes("lead mb-5")
                with ui.row().classes("gap-3"):
                    ui.button("Reportar incidente", icon="add_location_alt",
                              on_click=lambda: ui.navigate.to("/reportar")).props("unelevated no-caps size=lg").classes("btn-hero-1")
                    ui.button("Consultar mi reporte", icon="search",
                              on_click=lambda: ui.navigate.to("/seguimiento")).props("flat no-caps size=lg").classes("btn-hero-2")
            # ---- Columna derecha (4 columnas): consulta rápida + resumen de pasos
            with ui.column().classes("b-4 gap-[18px]"):
                with ui.card().classes("tarjeta consulta w-full").props("flat"):
                    ui.icon("travel_explore").classes("text-3xl").style("color:var(--c6)").props('aria-hidden="true"')
                    ui.label("Consulta rápida").classes("seccion-titulo")
                    ui.label("¿Ya envió un reporte? Escriba su código.").classes("sub")
                    rapido = ui.input("Código (VINTO-2026-0001)").props("outlined dense").classes("w-full")

                    def ir() -> None:
                        if (rapido.value or "").strip():
                            ui.navigate.to(f"/seguimiento?codigo={quote(rapido.value.strip())}")
                    rapido.on("keydown.enter", ir)
                    ui.button("Ver estado", icon="arrow_forward", on_click=ir).props("unelevated no-caps color=primary")
                with ui.card().classes("tarjeta p-5 w-full gap-2 flex-1").props("flat"):
                    ui.label("Antes de reportar, tenga a mano").classes("seccion-titulo")
                    for icono, texto in [("place", "El lugar exacto o una referencia clara"),
                                         ("photo_camera", "Hasta 3 fotografías (opcional)"),
                                         ("schedule", "Fecha y hora aproximadas")]:
                        with ui.element("div").classes("check"):
                            ui.icon(icono).props('aria-hidden="true"')
                            ui.label(texto)
            # ---- Cómo funciona (ancho completo)
            with ui.card().classes("tarjeta b-12 p-6 gap-4").props("flat"):
                ui.label("¿Cómo funciona?").classes("seccion-titulo")
                with ui.element("div").classes("pasos-linea"):
                    for icono, t, d in [
                        ("edit_note", "1. Registre", "Elija la categoría, describa lo ocurrido y marque el punto en el mapa."),
                        ("photo_camera", "2. Adjunte evidencia", "Suba fotografías para que el personal municipal verifique el caso."),
                        ("track_changes", "3. Haga seguimiento", "Con su código consulte el estado: revisión, atención y cierre."),
                    ]:
                        with ui.element("div").classes("p"):
                            with ui.element("div").classes("num"):
                                ui.icon(icono).style("font-size:1.7rem").props('aria-hidden="true"')
                            ui.label(t).classes("t2")
                            ui.label(d).classes("sub")
            # ---- Categorías
            categorias = c().listar_categorias.ejecutar()
            if categorias:
                with ui.column().classes("b-12 gap-3"):
                    ui.label("¿Qué puede reportar?").classes("seccion-titulo")
                    with ui.element("div").classes("tiles"):
                        for cat in categorias:
                            with ui.link(target="/reportar").classes("tile"):
                                with ui.element("div").classes("ic"):
                                    ui.icon(_icono_categoria(cat.nombre)).style("font-size:1.6rem").props('aria-hidden="true"')
                                ui.html(f"<b>{cat.nombre}</b>")
                                ui.label(cat.descripcion).classes("d")


# ------------------------------------------------------------ REPORTAR (RF-01..04)
@ui.page("/reportar")
def reportar() -> None:
    actor = actor_actual()
    cont = c()
    with marco("Reportar incidente", "/reportar", actor):
        encabezado("Reportar un incidente", "Complete los cuatro pasos. Los campos con * son obligatorios.", clave_rol(actor))

        categorias = {x.id: x.nombre for x in cont.listar_categorias.ejecutar()}
        zonas = [z.nombre for z in cont.geo.zonas()]
        archivos: list[ArchivoSubido] = []

        with ui.element("div").classes("dos-col"):
          with ui.card().classes("tarjeta p-6 min-w-0").props("flat"):
            with ui.stepper().props("flat animated alternative-labels").classes("w-full") as paso:
                # ---------------- Paso 1: información
                with ui.step("Información", icon="description"):
                    with ui.element("div").classes("form-grid"):
                        categoria = ui.select(categorias, label="Categoría del incidente *").props("outlined") \
                            .classes("w-full").props('data-testid=categoria')
                        fecha = ui.input("Fecha y hora del incidente *",
                                         value=datetime.now().strftime("%Y-%m-%dT%H:%M")) \
                            .props("outlined type=datetime-local").classes("w-full")
                        titulo = ui.input("Título breve *").props("outlined maxlength=120 counter").classes("w-full ancho")
                        descripcion = ui.textarea("Descripción detallada *") \
                            .props("outlined maxlength=500 counter autogrow").classes("w-full ancho")
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

          with ui.element("aside"):
            with ui.card().classes("tarjeta aside-ayuda").props("flat"):
                ui.image("/ilustraciones/arbol.svg").classes("w-32 self-center").props('alt=""')
                ui.label("Un buen reporte incluye").classes("seccion-titulo")
                for texto in ["Un título claro: qué ocurre y dónde",
                              "El punto exacto marcado en el mapa",
                              "Una referencia: calle, barrio o lugar conocido",
                              "Fotografías que muestren el problema"]:
                    with ui.element("div").classes("check"):
                        ui.icon("check_circle").props('aria-hidden="true"')
                        ui.label(texto)
            with ui.card().classes("tarjeta aside-ayuda").props("flat"):
                ui.label("¿Qué pasa después?").classes("seccion-titulo")
                for n, texto in [("1", "Recibe un código de seguimiento"), ("2", "El municipio revisa y asigna una cuadrilla"),
                                 ("3", "Puede consultar cada avance con su código")]:
                    with ui.row().classes("items-center gap-3 no-wrap"):
                        ui.html(f'<div class="avatar" style="width:34px;height:34px;font-size:.9rem">{n}</div>')
                        ui.label(texto).classes("text-sm")


def _exito(i: IncidenteAmbiental) -> None:
    with ui.dialog().props("persistent") as dlg, ui.card().classes("p-6 items-center gap-2 w-[420px] max-w-[92vw]"):
        ui.image("/ilustraciones/arbol.svg").classes("w-28").props('alt=""')
        ui.label("¡Reporte enviado! Gracias por cuidar Vinto").classes("text-xl font-bold text-center")
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
        encabezado("Seguimiento de reporte", "Consulte el avance de su caso con el código que recibió al enviarlo.",
                   clave_rol(actor))
        with ui.element("div").classes("buscador"):
            ui.icon("travel_explore").classes("text-4xl").props('aria-hidden="true"')
            with ui.column().classes("gap-0"):
                ui.label("Código de seguimiento").classes("seccion-titulo").style("color:#fff")
                ui.label("Por ejemplo: VINTO-2026-0001").style("color:#c9fafa")
            entrada = ui.input("Código de seguimiento", value=codigo).props("outlined dense data-testid=codigo") \
                .classes("flex-1 min-w-[240px]")
            ui.button("Consultar", icon="search", on_click=lambda: resultado.refresh()) \
                .props("unelevated no-caps data-testid=consultar").classes("btn-hero-1")

        @ui.refreshable
        def resultado() -> None:
            if not (entrada.value or "").strip():
                vacio("Escriba su código para ver el estado", "Verá el avance, las fotos y el historial completo.")
                return
            try:
                i = c().consultar_por_codigo.ejecutar(actor, entrada.value)
            except DominioError as e:
                with ui.card().classes("tarjeta p-5 w-full").props("flat"):
                    ui.icon("search_off").classes("text-3xl").style("color:var(--suave)")
                    ui.label(str(e)).classes("text-sm")
                return
            with ui.card().classes("tarjeta p-6 w-full gap-3").props("flat"):
                render_detalle(i, actor, resultado.refresh)

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
        acciones = encabezado("Mis reportes", "Todos los incidentes que ha enviado con esta cuenta.", clave_rol(actor))
        with acciones:
            ui.button("Nuevo reporte", icon="add_location_alt", on_click=lambda: ui.navigate.to("/reportar")) \
                .props("unelevated no-caps color=primary")
        try:
            lista = c().mis_reportes.ejecutar(actor)
        except DominioError as e:
            ui.label(str(e))
            return
        if not lista:
            with ui.card().classes("tarjeta w-full").props("flat"):
                vacio("Aún no ha enviado reportes con esta cuenta", "Cuando reporte un incidente aparecerá aquí con su estado.")
            return
        cerrados = sum(1 for i in lista if i.estado in (E.ATENDIDO, E.CERRADO))
        kpi_tira([("Reportes enviados", str(len(lista)), "#006666", "description"),
                  ("En proceso", str(len(lista) - cerrados), "#b45309", "pending_actions"),
                  ("Atendidos o cerrados", str(cerrados), "#008080", "check_circle")])
        with ui.element("div").classes("grid-auto"):
            for i in lista:
                tarjeta_caso(i, lambda cod: abrir_detalle(cod, actor), mostrar_asignado=False)


# ----------------------------------------------------------------- LOGIN / REGISTRO
@contextmanager
def _acceso(titulo: str, mensaje: str):
    """Dos columnas: ilustración de bosque a la izquierda y formulario a la derecha."""
    with ui.element("div").classes("acceso"):
        with ui.element("div").classes("acceso-ilus"):
            ui.icon("park").style("font-size:2.6rem; color:#00ffff").props('aria-hidden="true"')
            ui.html(f"<h2>{titulo}</h2>")
            ui.label(mensaje)
        with ui.element("div").classes("acceso-form"):
            yield


@ui.page("/login")
def login(next: str = "") -> None:  # noqa: A002 - nombre del parámetro de consulta
    actor = actor_actual()
    with marco("Ingresar", "/login", actor):
        with _acceso("Bienvenido de nuevo", "Ingrese para reportar, gestionar o atender incidentes del municipio."):
            ui.label("Iniciar sesión").classes("text-2xl font-bold").style("font-family:var(--titulos)")
            correo = ui.input("Correo electrónico").props("outlined dense data-testid=correo autocomplete=username").classes("w-full")
            clave = ui.input("Contraseña", password=True, password_toggle_button=True) \
                .props("outlined dense data-testid=clave autocomplete=current-password").classes("w-full")

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
                with ui.expansion("Cuentas de demostración (pulse una para completar)", icon="info").classes("w-full text-sm"):
                    ui.label(f"Contraseña de todas: {PASS_DEMO}").classes("mono")
                    for _nombre, mail, rol, _ in USUARIOS:
                        ui.button(f"{rol.etiqueta}: {mail}", on_click=lambda m=mail: (
                            correo.set_value(m), clave.set_value(PASS_DEMO))) \
                            .props("flat no-caps dense align=left").classes("w-full mono")


@ui.page("/registro")
def registro() -> None:
    actor = actor_actual()
    with marco("Registro", "/registro", actor):
        with _acceso("Sea parte del cuidado de Vinto", "Con una cuenta puede guardar el historial de sus reportes y seguirlos fácilmente."):
            ui.label("Crear cuenta de ciudadano").classes("text-2xl font-bold").style("font-family:var(--titulos)")
            nombre = ui.input("Nombre completo").props("outlined dense autocomplete=name").classes("w-full")
            correo = ui.input("Correo electrónico").props("outlined dense autocomplete=email").classes("w-full")
            clave = ui.input("Contraseña (mín. 6 caracteres)", password=True, password_toggle_button=True) \
                .props("outlined dense autocomplete=new-password").classes("w-full")

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
