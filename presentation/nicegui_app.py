"""Punto de entrada de la capa de presentación: registra páginas y archivos estáticos."""
from __future__ import annotations

import os

from nicegui import app, ui

from bootstrap import Contenedor
from presentation import contexto
from presentation.pages import admin, panel, publicas  # noqa: F401  (importar registra las rutas)


def iniciar(contenedor: Contenedor, puerto: int = 8080, recargar: bool = False) -> None:
    contexto.fijar(contenedor)
    app.add_static_files("/evidencias", str(contenedor.carpeta_evidencias))
    ui.run(title="SIRIMA Vinto", port=puerto, reload=recargar, show=False, language="es",
           storage_secret=os.getenv("VINTO_SECRETO", "cambiar-este-secreto-en-produccion"),
           favicon="🌿")
