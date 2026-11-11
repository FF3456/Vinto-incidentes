"""Sesión de usuario y guardas de acceso por rol (RF-10).

La sesión vive en ``app.storage.user`` (cookie firmada + almacenamiento en servidor).
Las guardas ocultan/redirigen en la UI; la autorización real vive en los casos de uso.
"""
from __future__ import annotations

from nicegui import app, ui

from domain.exceptions import DominioError
from domain.policies.actor import Actor
from domain.value_objects.rol import Rol


def actor_actual() -> Actor:
    s = app.storage.user.get("sesion")
    if not s:
        return Actor.anonimo()
    return Actor(s["id"], s["nombre"], Rol(s["rol"]))


def autenticado() -> bool:
    return bool(app.storage.user.get("sesion"))


def iniciar_sesion(actor: Actor) -> None:
    app.storage.user["sesion"] = {"id": actor.usuario_id, "nombre": actor.nombre, "rol": actor.rol.value}


def cerrar_sesion() -> None:
    app.storage.user.pop("sesion", None)


def ruta_inicial(rol: Rol) -> str:
    return {Rol.CIUDADANO: "/", Rol.FUNCIONARIO: "/bandeja", Rol.RESPONSABLE: "/asignados",
            Rol.ADMINISTRADOR: "/bandeja"}[rol]


def notificar_error(e: Exception) -> None:
    """Errores de negocio se muestran tal cual; los inesperados se ocultan tras un mensaje genérico."""
    if isinstance(e, DominioError):
        ui.notify(str(e), type="negative", position="top")
    else:  # pragma: no cover - defensivo
        import logging
        logging.getLogger("vinto").exception("Error inesperado", exc_info=e)
        ui.notify("Ocurrió un error inesperado. Intente nuevamente.", type="negative", position="top")
