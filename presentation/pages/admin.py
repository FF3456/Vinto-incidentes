"""Administración: usuarios, categorías y auditoría (RF-02, RF-10, HU-06)."""
from __future__ import annotations

import csv
import html
import io

from nicegui import ui

from domain.entities.categoria import PERFILES_VALIDOS
from domain.exceptions import DominioError
from domain.value_objects.rol import Rol
from presentation.componentes.estilos import encabezado, kpi_tira, vacio
from presentation.componentes.marco import clave_rol, marco
from presentation.contexto import c
from presentation.guardas import requerir
from presentation.sesion import notificar_error

ADMIN = (Rol.ADMINISTRADOR,)
PERFILES = {
    "RESIDUOS": "Residuos sólidos (prioridad media · 72 h)",
    "AGUA": "Agua / vertidos (urgente · 24 h)",
    "AIRE": "Aire (alta · 48 h)",
    "RUIDO": "Ruido (baja · 120 h)",
    "AREAS_VERDES": "Áreas verdes (media · 96 h)",
    "GENERICO": "Genérico (media · 72 h)",
}
assert set(PERFILES) == set(PERFILES_VALIDOS)

_SLOT_ACCIONES = """
<q-td :props="props" auto-width>
  <q-btn flat dense round icon="edit" @click="() => $parent.$emit('editar', props.row)" />
  <q-btn flat dense round :icon="props.row.activo ? 'toggle_on' : 'toggle_off'"
         :color="props.row.activo ? 'positive' : 'grey'" @click="() => $parent.$emit('alternar', props.row)" />
</q-td>"""
_SLOT_ACTIVO = """<q-td :props="props"><span :class="'chip ' + (props.row.activo ? 'chip-ATENDIDO' : 'chip-CERRADO')">
{{ props.row.activo ? 'Activo' : 'Inactivo' }}</span></q-td>"""


# ----------------------------------------------------------------- USUARIOS
def _iniciales(nombre: str) -> str:
    return html.escape("".join(p[0] for p in (nombre or "").split()[:2]).upper() or "?")


@ui.page("/admin/usuarios")
def usuarios() -> None:
    actor = requerir("/admin/usuarios", *ADMIN)
    if not actor:
        return
    cont = c()
    roles = {r.value: r.etiqueta for r in Rol}
    filtro = {"rol": ""}
    with marco("Gestión de usuarios", "/admin/usuarios", actor):
        acciones = encabezado("Gestión de usuarios", "Cuentas, roles y estado de acceso (RBAC).", clave_rol(actor))
        with acciones:
            ui.toggle({"": "Todos"} | {k: v for k, v in roles.items()}, value="",
                      on_change=lambda e: (filtro.update(rol=e.value), tabla.refresh())) \
                .props("no-caps unelevated toggle-color=cyan-13 toggle-text-color=teal-10 color=teal-10 text-color=white")
            ui.button("Nuevo usuario", icon="person_add", on_click=lambda: dialogo_nuevo()) \
                .props("unelevated no-caps color=primary")

        @ui.refreshable
        def tabla() -> None:
            lista = cont.gestionar_usuarios.listar(actor)
            kpi_tira([("Usuarios", str(len(lista)), "#006666", "group"),
                      ("Activos", str(sum(u.activo for u in lista)), "#008080", "verified_user"),
                      ("Funcionarios y responsables",
                       str(sum(u.rol in (Rol.FUNCIONARIO, Rol.RESPONSABLE) for u in lista)), "#004c4c", "badge")])
            visibles = [u for u in lista if not filtro["rol"] or u.rol.value == filtro["rol"]]
            if not visibles:
                with ui.card().classes("tarjeta w-full").props("flat"):
                    vacio("No hay usuarios con este rol")
                return
            with ui.element("div").classes("grid-auto"):
                for u in visibles:
                    fila = {"id": u.id, "nombre": u.nombre, "correo": u.correo, "rol": roles[u.rol.value],
                            "rol_key": u.rol.value, "activo": u.activo}
                    with ui.card().classes("tarjeta usuario-card" + ("" if u.activo else " inactivo")).props("flat"):
                        with ui.row().classes("items-center gap-3 no-wrap"):
                            ui.html(f'<div class="avatar" aria-hidden="true">{_iniciales(u.nombre)}</div>')
                            with ui.column().classes("gap-0 min-w-0"):
                                ui.label(u.nombre).classes("font-bold")
                                ui.label(u.correo).classes("mono").style("word-break:break-all")
                        with ui.row().classes("items-center justify-between w-full"):
                            ui.label(roles[u.rol.value]).classes(f"chip chip-rol-{u.rol.value}")
                            ui.switch("Activo", value=u.activo, on_change=lambda _e, f=fila: alternar(f)).props("dense")
                        ui.button("Cambiar rol", icon="edit", on_click=lambda f=fila: dialogo_rol(f)) \
                            .props("flat no-caps dense align=left")

        def alternar(fila: dict) -> None:
            try:
                cont.gestionar_usuarios.cambiar_activo(actor, fila["id"], not fila["activo"])
                ui.notify("Estado de la cuenta actualizado", type="positive")
            except DominioError as e:
                notificar_error(e)
            tabla.refresh()

        def dialogo_rol(fila: dict) -> None:
            with ui.dialog() as dlg, ui.card().classes("p-5 gap-3 w-[380px]"):
                ui.label(f"Cambiar rol de {fila['nombre']}").classes("font-bold")
                sel = ui.select(roles, value=fila["rol_key"], label="Rol").props("outlined dense").classes("w-full")

                def guardar() -> None:
                    try:
                        cont.gestionar_usuarios.cambiar_rol(actor, fila["id"], Rol(sel.value))
                        ui.notify("Rol actualizado", type="positive")
                        dlg.close()
                        tabla.refresh()
                    except DominioError as e:
                        notificar_error(e)
                with ui.row().classes("justify-end w-full"):
                    ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                    ui.button("Guardar", on_click=guardar).props("unelevated no-caps color=primary")
            dlg.open()

        def dialogo_nuevo() -> None:
            with ui.dialog() as dlg, ui.card().classes("p-5 gap-3 w-[420px]"):
                ui.label("Nuevo usuario").classes("seccion-titulo")
                nombre = ui.input("Nombre completo").props("outlined dense").classes("w-full")
                correo = ui.input("Correo electrónico").props("outlined dense").classes("w-full")
                clave = ui.input("Contraseña inicial", password=True).props("outlined dense").classes("w-full")
                rol = ui.select(roles, value="FUNCIONARIO", label="Rol").props("outlined dense").classes("w-full")
                unidad = ui.input("Unidad / cuadrilla (solo responsables)").props("outlined dense").classes("w-full")

                def crear() -> None:
                    try:
                        cont.gestionar_usuarios.crear(actor, nombre.value, correo.value, clave.value,
                                                      Rol(rol.value), unidad.value)
                        ui.notify("Usuario creado", type="positive")
                        dlg.close()
                        tabla.refresh()
                    except DominioError as e:
                        notificar_error(e)
                with ui.row().classes("justify-end w-full"):
                    ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                    ui.button("Crear", on_click=crear).props("unelevated no-caps color=primary")
            dlg.open()

        tabla()


# --------------------------------------------------------------- CATEGORÍAS
_ICONO_PERFIL = {"RESIDUOS": "delete_sweep", "AGUA": "water_drop", "AIRE": "air", "RUIDO": "volume_up",
                 "AREAS_VERDES": "park", "GENERICO": "eco"}


@ui.page("/admin/categorias")
def categorias() -> None:
    actor = requerir("/admin/categorias", *ADMIN)
    if not actor:
        return
    cont = c()
    with marco("Categorías", "/admin/categorias", actor):
        acciones = encabezado("Configuración de categorías",
                              "Catálogo dinámico: las categorías se desactivan, nunca se eliminan (conserva el histórico).",
                              clave_rol(actor))
        with acciones:
            ui.button("Nueva categoría", icon="add", on_click=lambda: dialogo(None)).props("unelevated no-caps color=primary")

        @ui.refreshable
        def tabla() -> None:
            lista = cont.listar_categorias.ejecutar(solo_activas=False)
            kpi_tira([("Categorías", str(len(lista)), "#006666", "category"),
                      ("Activas", str(sum(1 for x in lista if x.activa)), "#008080", "check_circle"),
                      ("Inactivas", str(sum(1 for x in lista if not x.activa)), "#004c4c", "block")])
            with ui.element("div").classes("grid-auto"):
                for x in lista:
                    fila = {"id": x.id, "nombre": x.nombre, "descripcion": x.descripcion,
                            "perfil": PERFILES[x.perfil], "perfil_key": x.perfil, "activo": x.activa}
                    with ui.card().classes("tarjeta cat-card" + ("" if x.activa else " usuario-card inactivo")).props("flat"):
                        with ui.row().classes("items-center justify-between w-full no-wrap"):
                            with ui.element("div").classes("ic"):
                                ui.icon(_ICONO_PERFIL.get(x.perfil, "eco")).props('aria-hidden="true"')
                            ui.switch("Activa", value=x.activa, on_change=lambda _e, f=fila: alternar(f)).props("dense")
                        ui.label(x.nombre).classes("font-bold text-base")
                        ui.label(x.descripcion).classes("sub")
                        ui.label(PERFILES[x.perfil]).classes("chip chip-MEDIA").style("white-space:normal")
                        ui.button("Editar", icon="edit", on_click=lambda f=fila: dialogo(f)) \
                            .props("flat no-caps dense align=left")

        def alternar(fila: dict) -> None:
            try:
                cont.gestionar_categorias.cambiar_activa(actor, fila["id"], not fila["activo"])
            except DominioError as e:
                notificar_error(e)
            tabla.refresh()

        def dialogo(fila: dict | None) -> None:
            with ui.dialog() as dlg, ui.card().classes("p-5 gap-3 w-[460px] max-w-[95vw]"):
                ui.label("Editar categoría" if fila else "Nueva categoría").classes("seccion-titulo")
                nombre = ui.input("Nombre", value=fila["nombre"] if fila else "").props("outlined dense").classes("w-full")
                desc = ui.textarea("Descripción", value=fila["descripcion"] if fila else "").props("outlined dense autogrow").classes("w-full")
                perfil = ui.select(PERFILES, value=fila["perfil_key"] if fila else "GENERICO",
                                   label="Política de atención (prioridad y plazo)").props("outlined dense").classes("w-full")

                def guardar() -> None:
                    try:
                        if fila:
                            cont.gestionar_categorias.editar(actor, fila["id"], nombre.value, desc.value, perfil.value)
                        else:
                            cont.gestionar_categorias.crear(actor, nombre.value, desc.value, perfil.value)
                        ui.notify("Categoría guardada", type="positive")
                        dlg.close()
                        tabla.refresh()
                    except DominioError as e:
                        notificar_error(e)
                with ui.row().classes("justify-end w-full"):
                    ui.button("Cancelar", on_click=dlg.close).props("flat no-caps")
                    ui.button("Guardar", on_click=guardar).props("unelevated no-caps color=primary")
            dlg.open()

        tabla()


# ---------------------------------------------------------------- AUDITORÍA
_MAX_EVENTOS = 150


@ui.page("/admin/auditoria")
def auditoria() -> None:
    actor = requerir("/admin/auditoria", *ADMIN)
    if not actor:
        return
    registros = c().consultar_auditoria.ejecutar(actor)
    termino = {"v": ""}
    with marco("Auditoría", "/admin/auditoria", actor):
        encabezado("Auditoría del sistema", "Registro de acciones realizadas en la plataforma.", clave_rol(actor))

        def exportar() -> None:
            buf = io.StringIO()
            w = csv.writer(buf)
            w.writerow(["fecha", "usuario", "accion", "recurso", "detalle"])
            for r in registros:
                w.writerow([r.fecha.isoformat(sep=" ", timespec="seconds"), r.usuario_nombre,
                            r.accion, r.recurso, r.detalle])
            ui.download.content(buf.getvalue().encode("utf-8-sig"), "auditoria_sirima.csv", "text/csv")

        with ui.element("div").classes("dos-col"):
            with ui.column().classes("gap-3 min-w-0 w-full"):
                @ui.refreshable
                def linea_tiempo() -> None:
                    q = termino["v"].strip().lower()
                    coincidencias = [r for r in registros if not q or q in
                                     f"{r.usuario_nombre} {r.accion} {r.recurso} {r.detalle}".lower()]
                    ui.label(f"{len(coincidencias)} registro(s)").classes("sub")
                    if not coincidencias:
                        with ui.card().classes("tarjeta w-full").props("flat"):
                            vacio("Sin registros para esta búsqueda")
                        return
                    with ui.element("div").classes("feed"):
                        dia = None
                        for r in coincidencias[:_MAX_EVENTOS]:
                            if r.fecha.date() != dia:
                                dia = r.fecha.date()
                                ui.label(dia.strftime("%d/%m/%Y")).classes("dia")
                            with ui.element("div").classes("ev"):
                                with ui.row().classes("items-center gap-2"):
                                    ui.label(r.accion).classes("chip chip-rol-FUNCIONARIO")
                                    ui.label(r.recurso).classes("mono")
                                    ui.label(r.fecha.strftime("%H:%M:%S")).classes("hora")
                                ui.label(f"{r.usuario_nombre} · {r.detalle}").classes("text-sm")
                    if len(coincidencias) > _MAX_EVENTOS:
                        ui.label(f"Se muestran los {_MAX_EVENTOS} más recientes. Afine la búsqueda o exporte el CSV completo.").classes("sub")
                linea_tiempo()
            with ui.element("aside"):
                with ui.card().classes("tarjeta aside-ayuda").props("flat"):
                    ui.label("Buscar en el registro").classes("seccion-titulo")
                    ui.input("Usuario, acción o recurso", on_change=lambda e: (
                        termino.update(v=e.value or ""), linea_tiempo.refresh())) \
                        .props("outlined dense clearable").classes("w-full")
                    ui.button("Exportar CSV", icon="download", on_click=exportar).props("unelevated no-caps color=primary")
                kpi_tira([("Acciones registradas", str(len(registros)), "#006666", "history"),
                          ("Usuarios distintos", str(len({r.usuario_nombre for r in registros})), "#004c4c", "group")])
