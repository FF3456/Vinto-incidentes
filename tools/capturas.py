"""Demostración automatizada de punta a punta + capturas de pantalla para el informe.

Uso:   1) python main.py            (en otra terminal, con una base limpia)
       2) python tools/capturas.py  [http://localhost:8080]

Recorre los 10 RF con los 4 roles, verifica resultados esperados (aserciones) y guarda
las imágenes en docs/capturas/. Requiere:  pip install playwright && playwright install chromium
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

from playwright.sync_api import Page, expect, sync_playwright

URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8080"
RAIZ = Path(__file__).resolve().parent.parent
SALIDA = RAIZ / "docs" / "capturas"
FOTO = str(RAIZ / "tools" / "muestra_evidencia.png")
CLAVE = "Vinto2026"
SALIDA.mkdir(parents=True, exist_ok=True)
resultado: dict = {"capturas": [], "codigo": None}


def foto(p: Page, nombre: str, completa: bool = False) -> None:
    p.wait_for_timeout(900)
    p.screenshot(path=str(SALIDA / f"{nombre}.png"), full_page=completa)
    resultado["capturas"].append(nombre)
    print("  📸", nombre)


def ir(p: Page, ruta: str) -> None:
    p.goto(URL + ruta)
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(500)


def entrar(p: Page, correo: str) -> None:
    ir(p, "/login")
    campo(p, "correo").fill(correo)
    campo(p, "clave").fill(CLAVE)
    p.get_by_test_id("ingresar").click()
    p.wait_for_load_state("networkidle")
    p.wait_for_timeout(800)


def salir(p: Page) -> None:
    p.context.clear_cookies()
    p.evaluate("() => { localStorage.clear(); sessionStorage.clear(); }")


def campo(p: Page, test_id: str):
    """Quasar coloca data-testid en el <input> nativo o en su contenedor, según la versión."""
    loc = p.get_by_test_id(test_id).first
    return loc if loc.evaluate("e => e.tagName") == "INPUT" else loc.locator("input")


def elegir(p: Page, etiqueta: str, opcion: str) -> None:
    p.get_by_label(etiqueta).first.click()
    p.get_by_role("option", name=opcion).first.click()


def main() -> None:
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        ctx = nav.new_context(viewport={"width": 1366, "height": 860}, device_scale_factor=1)
        p = ctx.new_page()
        errores: list[str] = []
        p.on("pageerror", lambda e: errores.append(str(e)))

        # ---- Público: inicio y login
        ir(p, "/"); foto(p, "01_inicio")
        ir(p, "/login"); foto(p, "02_login")

        # ---- RF-01..04: ciudadano con cuenta registra un incidente
        entrar(p, "vecino@vinto.gob.bo")
        ir(p, "/reportar")
        elegir(p, "Categoría del incidente *", "Vertido ilegal")
        p.get_by_label("Título breve *").fill("Escombros arrojados junto al canal")
        p.get_by_label("Descripción detallada *").fill(
            "Desde ayer se arrojan escombros y bolsas con aceite usado junto al canal de riego, "
            "obstruyendo el paso del agua.")
        foto(p, "03_reporte_paso1_informacion")
        p.get_by_role("button", name="Siguiente").click()
        p.wait_for_timeout(1500)
        mapa = p.locator(".nicegui-leaflet").first
        caja = mapa.bounding_box()
        p.mouse.click(caja["x"] + caja["width"] * 0.55, caja["y"] + caja["height"] * 0.45)
        p.wait_for_timeout(700)
        p.get_by_label("Referencia del lugar *").fill("Canal de riego, junto al puente de la Av. Bolívar")
        foto(p, "04_reporte_paso2_ubicacion_mapa")
        p.get_by_role("button", name="Siguiente").click()
        p.locator("input[type=file]").first.set_input_files(FOTO)
        p.wait_for_timeout(1200)
        foto(p, "05_reporte_paso3_evidencia")
        p.get_by_role("button", name="Siguiente").click()
        p.get_by_label("Teléfono o correo").fill("70712345")
        foto(p, "06_reporte_paso4_envio")
        p.get_by_test_id("enviar").click()
        p.get_by_test_id("codigo-generado").wait_for()
        codigo = p.get_by_test_id("codigo-generado").inner_text().strip()
        assert re.fullmatch(r"VINTO-\d{4}-\d{4}", codigo), codigo
        resultado["codigo"] = codigo
        foto(p, "07_reporte_enviado_codigo")

        # ---- Mis reportes (ciudadano)
        ir(p, "/mis-reportes"); expect(p.get_by_text(codigo).first).to_be_visible(); foto(p, "08_mis_reportes")
        # ---- RBAC: ciudadano no puede entrar a la bandeja
        ir(p, "/bandeja"); expect(p.get_by_text("Acceso denegado").first).to_be_visible(); foto(p, "09_rbac_acceso_denegado")
        salir(p)

        # ---- RF-13 / seguimiento público (sin sesión)
        ir(p, "/seguimiento")
        campo(p, "codigo").fill(codigo)
        p.get_by_test_id("consultar").click()
        expect(p.get_by_text("Historial de estados")).to_be_visible()
        foto(p, "10_seguimiento_publico", completa=True)

        # ---- Funcionario: bandeja, filtros, gestión
        entrar(p, "funcionario@vinto.gob.bo")
        ir(p, "/bandeja"); foto(p, "11_bandeja_funcionario")
        elegir(p, "Estado", "Reportado")
        p.wait_for_timeout(700)
        foto(p, "12_bandeja_filtro_estado")
        campo(p, "buscar").fill(codigo)
        p.wait_for_timeout(900)
        expect(p.get_by_text("1 coincidencia(s)")).to_be_visible()
        p.get_by_text(codigo).first.click()
        p.get_by_text("Gestión del caso").wait_for()
        foto(p, "13_detalle_gestion_caso")
        p.get_by_role("button", name="Pasar a revisión").click()
        p.wait_for_timeout(1200)
        elegir(p, "Responsable / cuadrilla", "Dra. Sofía Herbas")
        foto(p, "14_asignar_responsable")
        p.get_by_role("button", name="Asignar y pasar a atención").click()
        p.wait_for_timeout(1200)
        expect(p.get_by_text("En atención").first).to_be_visible()
        foto(p, "15_caso_en_atencion")
        p.keyboard.press("Escape")
        ir(p, "/mapa"); p.wait_for_timeout(1500); foto(p, "16_mapa_incidentes")
        ir(p, "/estadisticas"); p.wait_for_timeout(1800); foto(p, "17_panel_estadisticas", completa=True)
        salir(p)

        # ---- Responsable: asignados y registro de atención
        entrar(p, "responsable2@vinto.gob.bo")
        ir(p, "/asignados"); foto(p, "18_responsable_asignados")
        p.get_by_text(codigo).first.click()
        p.get_by_label("Resumen de la intervención").fill(
            "Se retiraron los escombros con volqueta y se limpió el cauce; se notificó al infractor.")
        p.get_by_role("button", name="Marcar como atendido").click()
        p.wait_for_timeout(1200)
        foto(p, "19_atencion_registrada")
        p.keyboard.press("Escape")
        ir(p, "/mapa"); p.wait_for_timeout(1200); foto(p, "20_mapa_de_trabajo_responsable")
        salir(p)

        # ---- Funcionario cierra el caso
        entrar(p, "funcionario@vinto.gob.bo")
        ir(p, "/bandeja")
        campo(p, "buscar").fill(codigo)
        p.wait_for_timeout(900)
        p.get_by_text(codigo).first.click()
        p.get_by_role("button", name="Verificar y cerrar caso").click()
        p.wait_for_timeout(1200)
        expect(p.get_by_text("Cerrado").first).to_be_visible()
        foto(p, "21_caso_cerrado_historial", completa=True)
        salir(p)

        # ---- Administrador
        entrar(p, "admin@vinto.gob.bo")
        ir(p, "/admin/usuarios"); foto(p, "22_admin_usuarios")
        ir(p, "/admin/categorias"); foto(p, "23_admin_categorias")
        ir(p, "/admin/auditoria"); foto(p, "24_admin_auditoria")
        nav.close()
        resultado["errores_js"] = errores
    (SALIDA / "resultado.json").write_text(json.dumps(resultado, indent=2, ensure_ascii=False))
    print("OK · código creado:", resultado["codigo"], "· errores JS:", len(resultado["errores_js"]))


if __name__ == "__main__":
    main()
