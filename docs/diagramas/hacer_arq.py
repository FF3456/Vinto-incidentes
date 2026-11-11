import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
fig, ax = plt.subplots(figsize=(13, 7.2)); ax.set_xlim(0, 13); ax.set_ylim(0, 7.2); ax.axis("off")
def box(x, y, w, h, fc, ec, title, lines=(), tc="#14342a"):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.02,rounding_size=0.12", fc=fc, ec=ec, lw=1.6))
    ax.text(x + w/2, y + h - 0.22, title, ha="center", va="top", fontsize=10.5, fontweight="bold", color=tc)
    for k, l in enumerate(lines):
        ax.text(x + w/2, y + h - 0.65 - k*0.36, l, ha="center", va="top", fontsize=8.6, color="#222")
def arrow(a, b, txt="", style="-|>", ls="-", c="#2d6a4f"):
    ax.add_patch(FancyArrowPatch(a, b, arrowstyle=style, mutation_scale=16, lw=1.8, color=c, linestyle=ls))
    if txt: ax.text((a[0]+b[0])/2, (a[1]+b[1])/2+0.12, txt, ha="center", fontsize=8, color=c, style="italic")
box(0.2, 1.2, 2.5, 4.8, "#e8f3ec", "#2d6a4f", "PRESENTACIÓN", ["NiceGUI (UI)", "pages/publicas.py", "pages/panel.py", "pages/admin.py", "componentes/mapa.py", "componentes/detalle.py", "sesion.py · guardas.py"])
box(3.2, 1.2, 2.6, 4.8, "#e6eefb", "#2563eb", "APLICACIÓN", ["Casos de uso", "RegistrarIncidente", "CambiarEstado", "AsignarResponsable", "RegistrarAtencion", "ListarIncidentes", "ObtenerEstadisticas", "Autenticar · Gestionar…"])
box(6.3, 0.6, 3.4, 6.0, "#fff7e0", "#d97706", "DOMINIO (núcleo)", ["IncidenteAmbiental (agregado)", "Ubicacion · Estado · Evidencia", "IncidenteFactory + Políticas", "Permisos RBAC · Actor"])
box(6.55, 0.8, 2.9, 2.3, "#ffffff", "#d97706", "PUERTOS", ["IRepositorio… (4)", "ServicioGeografico", "AlmacenamientoEvidencias", "HasheadorPassword"])
box(10.3, 1.2, 2.5, 4.8, "#f3e8fb", "#7c3aed", "INFRAESTRUCTURA", ["Adaptadores de salida", "SQLAlchemy + SQLite", "AdaptadorOpenStreetMap", "AdaptadorCartoClaro", "AlmacenamientoLocal", "HasheadorPBKDF2", "Repos en memoria (tests)"])
arrow((2.7, 3.6), (3.2, 3.6)); arrow((5.8, 3.6), (6.3, 3.6))
arrow((10.3, 2.0), (9.45, 2.0), "implementa", ls="--", c="#7c3aed")
ax.text(6.5, 6.95, "Regla de dependencia: todas las flechas apuntan hacia el dominio", fontsize=10, color="#444", style="italic")
box(3.2, 0.05, 6.3, 0.0, "w", "w", "")
ax.text(4.5, 0.3, "bootstrap.py (raíz de composición) inyecta los adaptadores concretos en los casos de uso", fontsize=8.6, color="#555")
fig.savefig("arq.png", dpi=170, bbox_inches="tight", facecolor="white")
