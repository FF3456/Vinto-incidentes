"""Guardas de acceso por rol para las páginas privadas (RF-10)."""
from __future__ import annotations

from nicegui import ui

from domain.policies.actor import Actor
from domain.value_objects.rol import Rol
from presentation.componentes.marco import marco
from presentation.sesion import actor_actual, autenticado, ruta_inicial


def requerir(ruta: str, *roles: Rol) -> Actor | None:
    """Devuelve el actor si puede entrar; si no, redirige al login o muestra «acceso denegado»."""
    actor = actor_actual()
    if not autenticado():
        ui.navigate.to(f"/login?next={ruta}")
        return None
    if actor.rol not in roles:
        with marco("Acceso denegado", ruta, actor):
            with ui.card().classes("tarjeta p-8 items-center gap-2 mx-auto").props("flat"):
                ui.icon("lock").classes("text-5xl").style("color:#b91c1c").props('aria-hidden="true"')
                ui.label("Acceso denegado").classes("text-2xl font-bold").style("font-family:var(--titulos)")
                ui.label(f"Su rol ({actor.rol.etiqueta}) no tiene permiso para ver esta sección.").classes("sub")
                ui.button("Ir a mi página", on_click=lambda: ui.navigate.to(ruta_inicial(actor.rol))) \
                    .props("unelevated no-caps color=primary")
        return None
    return actor
