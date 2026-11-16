"""Marco común de todas las páginas: cabecera, menú lateral DERECHO desplazable y pie.

La estructura es la misma para todos los roles (misma marca, mismo menú, mismos componentes); lo que cambia
es el contenido del menú, su color y su personalidad según el rol.
"""
from __future__ import annotations

import html
from contextlib import contextmanager

from nicegui import ui

from domain.policies.actor import Actor
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from presentation.componentes.estilos import AMBITO, aplicar_tema
from presentation.contexto import c
from presentation.sesion import autenticado, cerrar_sesion

# (grupo, etiqueta, ruta, icono)
_PUBLICO = [("", "Inicio", "/", "home"), ("", "Reportar incidente", "/reportar", "add_location_alt"),
            ("", "Seguimiento", "/seguimiento", "travel_explore")]
_NAV_POR_ROL: dict[Rol, list[tuple[str, str, str, str]]] = {
    Rol.CIUDADANO: _PUBLICO + [("", "Mis reportes", "/mis-reportes", "folder_open")],
    Rol.FUNCIONARIO: [("Gestión", "Bandeja de incidentes", "/bandeja", "inbox"),
                      ("Gestión", "Mapa de incidentes", "/mapa", "map"),
                      ("Análisis", "Estadísticas", "/estadisticas", "insights")],
    Rol.RESPONSABLE: [("Mi trabajo", "Incidentes asignados", "/asignados", "assignment_turned_in"),
                      ("Mi trabajo", "Mapa de trabajo", "/mapa", "map")],
    Rol.ADMINISTRADOR: [("Operación", "Bandeja de incidentes", "/bandeja", "inbox"),
                        ("Operación", "Mapa de incidentes", "/mapa", "map"),
                        ("Operación", "Estadísticas", "/estadisticas", "insights"),
                        ("Administración", "Gestión de usuarios", "/admin/usuarios", "group"),
                        ("Administración", "Categorías", "/admin/categorias", "category"),
                        ("Control", "Auditoría", "/admin/auditoria", "fact_check")],
}
_ICONO_ROL = {Rol.CIUDADANO: "diversity_3", Rol.FUNCIONARIO: "badge", Rol.RESPONSABLE: "engineering",
              Rol.ADMINISTRADOR: "admin_panel_settings"}
_ICONO_AMBITO = {"publico": "park", "ciudadano": "park", "funcionario": "dashboard", "responsable": "local_shipping",
                 "administrador": "shield"}
_HERRAMIENTAS = [
    ("text_decrease", "Reducir el tamaño del texto", "sirima.fuente(-1)"),
    ("text_increase", "Aumentar el tamaño del texto", "sirima.fuente(1)"),
    ("contrast", "Activar o desactivar el alto contraste", "sirima.contraste()"),
]
_CONSEJOS = [
    "Separar los residuos orgánicos de los reciclables reduce la basura que llega a calles y ríos.",
    "Un árbol urbano da sombra, refresca el barrio y ayuda a limpiar el aire que respiramos.",
    "Quemar residuos libera humo dañino. Si ve una quema, repórtela para que se actúe a tiempo.",
    "Los ríos y canales limpios empiezan con vecinos que avisan cuando algo los contamina.",
    "Una foto y una referencia clara del lugar ayudan a atender su reporte más rápido.",
]


def navegacion_para(actor: Actor) -> list[tuple[str, str]]:
    items = _NAV_POR_ROL[actor.rol] if autenticado() else _PUBLICO
    return [(etiqueta, ruta) for _, etiqueta, ruta, _ in items]


def clave_rol(actor: Actor) -> str:
    """Clave de identidad visual: 'publico', 'ciudadano', 'funcionario', 'responsable' o 'administrador'."""
    return actor.rol.value.lower() if autenticado() else "publico"


def _iniciales(nombre: str) -> str:
    partes = [p for p in (nombre or "").split() if p]
    return "".join(p[0] for p in partes[:2]).upper() or "?"


def _conteos(actor: Actor) -> dict:
    """Datos vivos para el menú. Si algo falla, el menú se muestra igual sin ellos."""
    try:
        if actor.rol in (Rol.FUNCIONARIO, Rol.ADMINISTRADOR):
            est = c().estadisticas.ejecutar(actor)
            return {"pendientes": est.pendientes, "proceso": est.en_proceso, "vencidos": est.vencidos,
                    "resueltos": est.resueltos, "total": est.total}
        if actor.rol == Rol.RESPONSABLE:
            datos = c().incidentes_asignados.ejecutar(actor)
            pend = sum(1 for i in datos if i.estado == E.EN_ATENCION)
            return {"pendientes": pend, "total": len(datos)}
    except Exception:  # noqa: BLE001 - el menú nunca debe romper la página
        pass
    return {}


def _widget(actor: Actor, datos: dict) -> None:
    """Bloque inferior del menú, distinto por rol."""
    if not autenticado():
        with ui.element("div").classes("menu-widget"):
            ui.html("<h3>¿Ya tiene cuenta?</h3>")
            ui.label("Ingrese para ver el historial de sus reportes.").classes("text-sm")
            ui.button("Ingresar", icon="login", on_click=lambda: ui.navigate.to("/login")) \
                .props("unelevated no-caps color=primary")
        return
    if actor.rol == Rol.CIUDADANO:
        indice = {"i": 0}
        with ui.element("div").classes("menu-widget"):
            ui.html("<h3>🌿 Dato verde</h3>")
            texto = ui.label(_CONSEJOS[0]).classes("text-sm").props('aria-live="polite"')

            def otro() -> None:
                indice["i"] = (indice["i"] + 1) % len(_CONSEJOS)
                texto.text = _CONSEJOS[indice["i"]]
            ui.button("Otro dato", icon="autorenew", on_click=otro).props("flat no-caps dense")
    elif actor.rol == Rol.FUNCIONARIO and datos:
        with ui.element("div").classes("menu-widget"):
            ui.html("<h3>Resumen del día</h3>")
            for etiqueta, clave in [("Por revisar", "pendientes"), ("En proceso", "proceso"), ("Plazo vencido", "vencidos")]:
                ui.html(f'<div class="fila"><span>{etiqueta}</span><b>{datos[clave]}</b></div>')
    elif actor.rol == Rol.RESPONSABLE and datos:
        total, pend = datos["total"], datos["pendientes"]
        with ui.element("div").classes("menu-widget"):
            ui.html("<h3>Mi jornada</h3>")
            ui.html(f'<div class="fila"><span>Por atender</span><b>{pend}</b></div>')
            ui.html(f'<div class="fila"><span>Atendidos</span><b>{total - pend}</b></div>')
            ui.linear_progress(value=(total - pend) / total if total else 0, show_value=False).props("rounded color=primary")
    elif actor.rol == Rol.ADMINISTRADOR and datos:
        with ui.element("div").classes("menu-widget"):
            ui.html("<h3>Estado del sistema</h3>")
            ui.html(f'<div class="fila"><span>Incidentes totales</span><b>{datos["total"]}</b></div>')
            ui.html(f'<div class="fila"><span>Resueltos</span><b>{datos["resueltos"]}</b></div>')
            ui.html(f'<div class="fila"><span>Con plazo vencido</span><b>{datos["vencidos"]}</b></div>')


def _menu(actor: Actor, ruta: str, rol: str) -> None:
    sesion = autenticado()
    items = _NAV_POR_ROL[actor.rol] if sesion else _PUBLICO
    datos = _conteos(actor) if sesion else {}
    with ui.element("nav").classes("menu").props('aria-label="Menú principal"'):
        ui.element("div").classes("menu-banda").props('aria-hidden="true"') \
            .style(f"background-color:var(--cab-fondo); background-image:url('/ilustraciones/banda-{'ciudadano' if rol == 'publico' else rol}.svg')")
        with ui.element("div").classes("menu-perfil"):
            if sesion:
                ui.html(f'<div class="avatar" aria-hidden="true">{html.escape(_iniciales(actor.nombre))}</div>')
                with ui.column().classes("gap-0"):
                    ui.label(actor.nombre).classes("font-bold").style("line-height:1.2; color:var(--menu-texto)")
                    ui.label(actor.rol.etiqueta).classes("text-xs").style("color:var(--menu-suave)")
            else:
                ui.html('<div class="avatar" aria-hidden="true">🌳</div>')
                with ui.column().classes("gap-0"):
                    ui.html("<b>Bienvenido</b>")
                    ui.html("<span>Navegue sin cuenta</span>")
        grupo_actual = None
        for grupo, etiqueta, destino, icono in items:
            if grupo and grupo != grupo_actual:
                ui.html(f'<div class="menu-grupo">{grupo}</div>')
                grupo_actual = grupo
            activa = destino == ruta
            with ui.link(target=destino).classes("menu-item" + (" activa" if activa else "")) \
                    .props('aria-current="page"' if activa else ""):
                ui.icon(icono).props('aria-hidden="true"')
                ui.label(etiqueta)
                if destino in ("/bandeja", "/asignados") and datos.get("pendientes"):
                    ui.label(str(datos["pendientes"])).classes("conteo").props('aria-label="pendientes"')
        _widget(actor, datos)
        if sesion:
            with ui.element("div").classes("menu-pie"):
                ui.button("Cerrar sesión", icon="logout",
                          on_click=lambda: (cerrar_sesion(), ui.navigate.to("/"))).props("flat no-caps")


@contextmanager
def marco(titulo: str, ruta: str, actor: Actor):
    """Uso: ``with marco('Bandeja', '/bandeja', actor):`` y dentro el contenido de la página."""
    sesion = autenticado()
    rol = clave_rol(actor)
    aplicar_tema(rol)
    ui.page_title(f"{titulo} · SIRIMA Vinto")
    ui.link("Saltar al contenido", "#contenido").classes("saltar")

    drawer = ui.right_drawer(value=None, fixed=True).props("width=300 breakpoint=1024 bordered") \
        .classes("menu-lateral" + (" menu-oscuro" if rol in ("funcionario", "administrador") else ""))
    with drawer:
        _menu(actor, ruta, rol)

    with ui.header().classes("items-center justify-between px-5 py-2 gap-3").props("elevated=false"):
        with ui.link(target="/").classes("marca row items-center gap-3 no-wrap") \
                .props('aria-label="SIRIMA Vinto, ir al inicio"'):
            with ui.element("div").classes("logo"):
                ui.icon("park").style("color:#00ffff; font-size:28px").props('aria-hidden="true"')
            with ui.column().classes("gap-0"):
                ui.html("<b>SIRIMA Vinto</b>")
                ui.html("<span>Municipio de Vinto · Cochabamba</span>")
        with ui.element("div").classes("ambito gt-xs"):
            ui.icon(_ICONO_AMBITO[rol]).props('aria-hidden="true"')
            ui.label(AMBITO[rol])
        with ui.row().classes("items-center gap-2 no-wrap"):
            with ui.element("div").classes("herramientas").props('role="group" aria-label="Opciones de accesibilidad"'):
                for icono, ayuda, js in _HERRAMIENTAS:
                    ui.button(icon=icono).props(f'flat round dense aria-label="{ayuda}"') \
                        .on("click", js_handler=f"() => {js}").tooltip(ayuda)
            if not sesion:
                ui.button("Ingresar", icon="login", on_click=lambda: ui.navigate.to("/login")) \
                    .props("unelevated no-caps color=primary").classes("gt-xs")
            ui.button(icon="menu", on_click=drawer.toggle) \
                .props('flat round aria-label="Mostrar u ocultar el menú lateral"').classes("btn-cab")

    with ui.element("main").props("id=contenido tabindex=-1").classes("pagina flex flex-col gap-5"):
        yield

    with ui.element("footer").classes("pie"):
        with ui.element("div").classes("pie-int"):
            with ui.row().classes("items-center gap-2 no-wrap"):
                ui.icon("eco").style("color:#00ffff").props('aria-hidden="true"')
                ui.html("<span><b>SIRIMA Vinto</b> · Cuidemos juntos nuestro entorno</span>")
            ui.label("Municipio de Vinto, Cochabamba · Bolivia").classes("text-sm")
