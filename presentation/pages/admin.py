"""Administración: usuarios, categorías y auditoría (RF-02, RF-10, HU-06)."""
from __future__ import annotations

import csv
import io

from nicegui import ui

from domain.entities.categoria import PERFILES_VALIDOS
from domain.exceptions import DominioError
from domain.value_objects.rol import Rol
from presentation.componentes.estilos import fmt_fecha, kpi
from presentation.componentes.marco import marco
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
@ui.page("/admin/usuarios")
def usuarios() -> None:
    actor = requerir("/admin/usuarios", *ADMIN)
    if not actor:
        return
    cont = c()
    roles = {r.value: r.etiqueta for r in Rol}
    with marco("Gestión de usuarios", "/admin/usuarios", actor):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.html('<h1 class="h">Gestión de usuarios</h1>')
                ui.label("Cuentas, roles y estado de acceso (RBAC).").classes("sub")
            ui.button("Nuevo usuario", icon="person_add", on_click=lambda: dialogo_nuevo()) \
                .props("unelevated no-caps color=primary")

        @ui.refreshable
        def tabla() -> None:
            lista = cont.gestionar_usuarios.listar(actor)
            with ui.row().classes("w-full gap-4"):
                kpi("Usuarios", str(len(lista)), "#2d6a4f", "group")
                kpi("Activos", str(sum(u.activo for u in lista)), "#059669", "verified_user")
                kpi("Funcionarios y responsables",
                    str(sum(u.rol in (Rol.FUNCIONARIO, Rol.RESPONSABLE) for u in lista)), "#2563eb", "badge")
            filas = [{"id": u.id, "nombre": u.nombre, "correo": u.correo, "rol": roles[u.rol.value],
                      "rol_key": u.rol.value, "activo": u.activo} for u in lista]
            cols = [{"name": "nombre", "label": "Nombre", "field": "nombre", "align": "left"},
                    {"name": "correo", "label": "Correo", "field": "correo", "align": "left"},
                    {"name": "rol", "label": "Rol", "field": "rol", "align": "left"},
                    {"name": "activo", "label": "Estado", "field": "activo", "align": "left"},
                    {"name": "acciones", "label": "", "field": "id"}]
            with ui.card().classes("tarjeta w-full p-3").props("flat"):
                t = ui.table(columns=cols, rows=filas, row_key="id", pagination=10).classes("w-full").props("flat")
                t.add_slot("body-cell-activo", _SLOT_ACTIVO)
                t.add_slot("body-cell-acciones", _SLOT_ACCIONES)
                t.on("alternar", lambda e: alternar(e.args))
                t.on("editar", lambda e: dialogo_rol(e.args))

        def alternar(fila: dict) -> None:
            try:
                cont.gestionar_usuarios.cambiar_activo(actor, fila["id"], not fila["activo"])
                ui.notify("Estado de la cuenta actualizado", type="positive")
                tabla.refresh()
            except DominioError as e:
                notificar_error(e)

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
                ui.label("Nuevo usuario").classes("text-lg font-extrabold")
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
@ui.page("/admin/categorias")
def categorias() -> None:
    actor = requerir("/admin/categorias", *ADMIN)
    if not actor:
        return
    cont = c()
    with marco("Categorías", "/admin/categorias", actor):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.html('<h1 class="h">Configuración de categorías</h1>')
                ui.label("Catálogo dinámico: las categorías se desactivan, nunca se eliminan (conserva el histórico).").classes("sub")
            ui.button("Nueva categoría", icon="add", on_click=lambda: dialogo(None)) \
                .props("unelevated no-caps color=primary")

        @ui.refreshable
        def tabla() -> None:
            lista = cont.listar_categorias.ejecutar(solo_activas=False)
            filas = [{"id": x.id, "nombre": x.nombre, "descripcion": x.descripcion,
                      "perfil": PERFILES[x.perfil], "perfil_key": x.perfil, "activo": x.activa} for x in lista]
            cols = [{"name": "nombre", "label": "Categoría", "field": "nombre", "align": "left"},
                    {"name": "descripcion", "label": "Descripción", "field": "descripcion", "align": "left"},
                    {"name": "perfil", "label": "Política de atención", "field": "perfil", "align": "left"},
                    {"name": "activo", "label": "Estado", "field": "activo", "align": "left"},
                    {"name": "acciones", "label": "", "field": "id"}]
            with ui.card().classes("tarjeta w-full p-3").props("flat"):
                t = ui.table(columns=cols, rows=filas, row_key="id", pagination=12).classes("w-full").props("flat")
                t.add_slot("body-cell-activo", _SLOT_ACTIVO)
                t.add_slot("body-cell-acciones", _SLOT_ACCIONES)
                t.on("alternar", lambda e: alternar(e.args))
                t.on("editar", lambda e: dialogo(e.args))

        def alternar(fila: dict) -> None:
            try:
                cont.gestionar_categorias.cambiar_activa(actor, fila["id"], not fila["activo"])
                tabla.refresh()
            except DominioError as e:
                notificar_error(e)

        def dialogo(fila: dict | None) -> None:
            with ui.dialog() as dlg, ui.card().classes("p-5 gap-3 w-[460px] max-w-[95vw]"):
                ui.label("Editar categoría" if fila else "Nueva categoría").classes("text-lg font-extrabold")
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
@ui.page("/admin/auditoria")
def auditoria() -> None:
    actor = requerir("/admin/auditoria", *ADMIN)
    if not actor:
        return
    registros = c().consultar_auditoria.ejecutar(actor)
    with marco("Auditoría", "/admin/auditoria", actor):
        with ui.row().classes("w-full items-center justify-between"):
            with ui.column().classes("gap-0"):
                ui.html('<h1 class="h">Auditoría del sistema</h1>')
                ui.label("Registro de acciones realizadas en la plataforma.").classes("sub")

            def exportar() -> None:
                buf = io.StringIO()
                w = csv.writer(buf)
                w.writerow(["fecha", "usuario", "accion", "recurso", "detalle"])
                for r in registros:
                    w.writerow([r.fecha.isoformat(sep=" ", timespec="seconds"), r.usuario_nombre,
                                r.accion, r.recurso, r.detalle])
                ui.download.content(buf.getvalue().encode("utf-8-sig"), "auditoria_sirima.csv", "text/csv")
            ui.button("Exportar CSV", icon="download", on_click=exportar).props("flat no-caps color=primary")

        with ui.row().classes("w-full gap-4"):
            kpi("Acciones registradas", str(len(registros)), "#2d6a4f", "history")
            kpi("Usuarios distintos", str(len({r.usuario_nombre for r in registros})), "#2563eb", "group")
        filas = [{"id": r.id, "fecha": fmt_fecha(r.fecha), "usuario": r.usuario_nombre, "accion": r.accion,
                  "recurso": r.recurso, "detalle": r.detalle} for r in registros]
        cols = [{"name": k, "label": l, "field": k, "align": "left", "sortable": True} for k, l in
                [("fecha", "Fecha/hora"), ("usuario", "Usuario"), ("accion", "Acción"),
                 ("recurso", "Recurso"), ("detalle", "Detalle")]]
        with ui.card().classes("tarjeta w-full p-3 gap-2").props("flat"):
            buscar = ui.input("Buscar por usuario, acción o recurso").props("outlined dense clearable").classes("w-full")
            t = ui.table(columns=cols, rows=filas, row_key="id", pagination=12).classes("w-full").props("flat")
            t.bind_filter_from(buscar, "value")
