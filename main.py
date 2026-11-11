"""SIRIMA Vinto — Sistema de Reporte de Incidentes Medio Ambientales.

Ejecución:  python main.py        (abre http://localhost:8080)
"""
import os

from bootstrap import construir_contenedor
from presentation.nicegui_app import iniciar

if __name__ in {"__main__", "__mp_main__"}:
    iniciar(construir_contenedor(), puerto=int(os.getenv("PORT", "8082")))
