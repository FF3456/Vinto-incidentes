"""Marco común de todas las páginas: cabecera, navegación por rol y menú de usuario."""
from __future__ import annotations

from contextlib import contextmanager

from nicegui import ui

from domain.policies.actor import Actor
from domain.value_objects.rol import Rol
from presentation.componentes.estilos import aplicar_tema
from presentation.sesion import autenticado, cerrar_sesion

_NAV_PUBLICO = [("Inicio", "/"), ("Reportar incidente", "/reportar"), ("Seguimiento", "/seguimiento")]
_NAV_POR_ROL: dict[Rol, list[tuple[str, str]]] = {
    Rol.CIUDADANO: _NAV_PUBLICO + [("Mis reportes", "/mis-reportes")],
    Rol.FUNCIONARIO: [("Bandeja de incidentes", "/bandeja"), ("Mapa de incidentes", "/mapa"),
                      ("Estadísticas", "/estadisticas")],
    Rol.RESPONSABLE: [("Incidentes asignados", "/asignados"), ("Mapa de trabajo", "/mapa")],
    Rol.ADMINISTRADOR: [("Bandeja de incidentes", "/bandeja"), ("Mapa de incidentes", "/mapa"),
                        ("Estadísticas", "/estadisticas"), ("Gestión de usuarios", "/admin/usuarios"),
                        ("Categorías", "/admin/categorias"), ("Auditoría", "/admin/auditoria")],
}


def navegacion_para(actor: Actor) -> list[tuple[str, str]]:
    if not autenticado():
        return _NAV_PUBLICO
    return _NAV_POR_ROL[actor.rol]


@contextmanager
def marco(titulo: str, ruta: str, actor: Actor):
    """Uso: ``with marco('Bandeja', '/bandeja', actor):`` y dentro el contenido de la página."""
    aplicar_tema()
    ui.page_title(f"{titulo} · SIRIMA Vinto")
    with ui.header().classes("items-center justify-between px-5 py-2").props("elevated=false"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            with ui.element("div").classes("logo"):
                ui.icon("eco").style("color:#fff; font-size:24px")
            with ui.column().classes("marca gap-0"):
                ui.html("<b>SIRIMA Vinto</b>")
                ui.html("<span>Municipio de Vinto · Cbba</span>")
        ui.label("Sistema de reporte de incidentes medio ambientales").classes("titulo-sistema gt-sm")
        with ui.row().classes("items-center gap-2 no-wrap"):
            if autenticado():
                ui.label(actor.nombre).classes("text-sm gt-xs")
                with ui.button(actor.rol.etiqueta, icon="expand_more").props(
                        "rounded unelevated no-caps color=green-1 text-color=green-10 size=sm"):
                    with ui.menu():
                        ui.menu_item("Cerrar sesión", on_click=lambda: (cerrar_sesion(), ui.navigate.to("/")))
            else:
                ui.button("Ingresar", icon="login", on_click=lambda: ui.navigate.to("/login")) \
                    .props("unelevated no-caps color=primary size=sm")
    with ui.element("nav").classes("nav w-full"):
        for etiqueta, destino in navegacion_para(actor):
            ui.link(etiqueta, destino).classes("activa" if destino == ruta else "")
    with ui.column().classes("pagina gap-5"):
        yield
