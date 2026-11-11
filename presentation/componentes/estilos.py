"""Tema visual SIRIMA Vinto (paleta verde institucional del prototipo) y chips reutilizables."""
from __future__ import annotations

from nicegui import ui

from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.prioridad import Prioridad

CSS = """
:root { --verde:#2d6a4f; --verde-claro:#e8f3ec; --fondo:#f1f7f3; --texto:#1b3a2d; --suave:#5b7a6a; --borde:#cfe3d7; }
body { background: var(--fondo); color: var(--texto);
       font-family: 'Nunito','Segoe UI',system-ui,-apple-system,Roboto,sans-serif; }
.q-header { background:#fff !important; color: var(--texto) !important; box-shadow: 0 1px 6px rgba(45,106,79,.12); }
.logo { width:40px; height:40px; border-radius:12px; background:var(--verde); display:flex; align-items:center; justify-content:center; }
.marca { line-height:1.15; } .marca b { font-size:15px; } .marca span { font-size:12px; color:var(--suave); }
.titulo-sistema { letter-spacing:.12em; font-size:11px; color:var(--suave); text-transform:uppercase; }
.nav { display:flex; gap:4px; overflow-x:auto; padding:0 16px; border-top:1px solid #eef3f0; background:#fff; }
.nav a { padding:12px 16px; font-size:14px; color:var(--suave); text-decoration:none; border-bottom:2px solid transparent; white-space:nowrap; }
.nav a:hover { color:var(--verde); }
.nav a.activa { color:var(--verde); font-weight:700; border-bottom-color:var(--verde); }
.pagina { width:100%; max-width:1240px; margin:0 auto; padding:24px 20px 48px; }
.tarjeta { background:#fff; border:1px solid var(--borde); border-radius:14px; box-shadow:0 1px 3px rgba(45,106,79,.06); }
.kpi { padding:18px 20px; } .kpi .t { font-size:13px; color:var(--suave); } .kpi .v { font-size:30px; font-weight:800; line-height:1.1; }
h1.h { font-size:26px; line-height:1.2; font-weight:800; margin:0; } .sub { color:var(--suave); font-size:14px; }
.chip { display:inline-block; padding:2px 10px; border-radius:999px; font-size:12px; font-weight:700; border:1px solid transparent; white-space:nowrap; }
.chip-REPORTADO { background:#fff7e0; color:#b45309; border-color:#fcd78a; }
.chip-EN_REVISION { background:#e3efff; color:#1d4ed8; border-color:#b6d3ff; }
.chip-EN_ATENCION { background:#efe7ff; color:#6d28d9; border-color:#d3bfff; }
.chip-ATENDIDO { background:#dcf5ea; color:#047857; border-color:#a7e3c9; }
.chip-CERRADO { background:#eceff1; color:#4b5563; border-color:#d4d9dd; }
.chip-BAJA { background:#eef2ff; color:#4338ca; } .chip-MEDIA { background:#e0f2fe; color:#0369a1; }
.chip-ALTA { background:#fff1d6; color:#b45309; } .chip-URGENTE { background:#ffe1e1; color:#b91c1c; }
.chip-VENCIDO { background:#ffe1e1; color:#b91c1c; }
.mono { font-family: ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace; font-size:12.5px; }
.hero { background:linear-gradient(135deg,#2d6a4f,#40916c); color:#fff; border-radius:18px; padding:40px 36px; }
.hero h1 { font-size:34px; font-weight:800; line-height:1.15; margin:0 0 10px; }
.q-table th { color:var(--suave); font-size:12px; text-transform:uppercase; letter-spacing:.04em; }
.q-table tbody tr { cursor:pointer; } .q-table tbody tr:hover { background:#f3faf6; }
.linea { border-left:2px solid var(--borde); margin-left:6px; padding-left:16px; }
.punto { width:12px; height:12px; border-radius:50%; background:var(--verde); margin-left:-23px; margin-top:4px; position:absolute; border:2px solid #fff; }
.paso { display:flex; align-items:center; gap:8px; } .paso .c { width:28px; height:28px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:12px; font-weight:800; background:#e5ede8; color:var(--suave); }
.paso.hecho .c { background:var(--verde); color:#fff; } .paso.actual .c { background:#fff; color:var(--verde); border:2px solid var(--verde); }
.nicegui-leaflet { z-index:0; }
.leyenda i { display:inline-block; width:10px; height:10px; border-radius:50%; margin-right:6px; }
"""


def aplicar_tema() -> None:
    ui.colors(primary="#2d6a4f", secondary="#52b788", accent="#40916c", positive="#10b981")
    ui.add_css(CSS)


def chip_estado(estado: EstadoIncidente | str):
    e = EstadoIncidente(estado)
    return ui.label(e.etiqueta).classes(f"chip chip-{e.value}")


def chip_prioridad(prioridad: Prioridad | str):
    p = Prioridad(prioridad)
    return ui.label(p.etiqueta).classes(f"chip chip-{p.value}")


def kpi(titulo: str, valor: str, color: str = "#2d6a4f", icono: str | None = None) -> None:
    with ui.card().classes("tarjeta kpi gap-1 flex-1 min-w-[190px]").props("flat"):
        with ui.row().classes("items-center justify-between w-full no-wrap"):
            ui.label(titulo).classes("t")
            if icono:
                ui.icon(icono).style(f"color:{color}; font-size:22px")
        ui.label(valor).classes("v").style(f"color:{color}")


def fmt_horas(h: float | None) -> str:
    if h is None:
        return "—"
    return f"{h / 24:.1f} días" if h >= 48 else f"{h:.1f} h"


def fmt_fecha(d, con_hora: bool = True) -> str:
    return d.strftime("%d/%m/%Y %H:%M") if con_hora else d.strftime("%d/%m/%Y")
