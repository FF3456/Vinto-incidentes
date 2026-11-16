"""Sistema de diseño SIRIMA Vinto.

Un solo producto, cuatro interfaces: todas comparten marca, paleta, tipografía y componentes base
(tarjeta, chip, KPI, encabezado de página, menú lateral derecho); cada rol cambia la composición.

Paleta base (de más clara a más oscura): #00ffff · #00e6e6 · #00cccc · #00b3b3 · #009999 ·
#008080 · #006666 · #004c4c · #003333 · #001919 · #000000.
Regla de contraste: el texto sobre fondo claro usa #006666 o más oscuro; sobre fondo oscuro, blanco o
#00ffff. Los tonos claros se reservan para fondos y acentos, nunca para texto pequeño sobre blanco.
"""
from __future__ import annotations

from nicegui import ui

from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.prioridad import Prioridad

FUENTES = (
    '<link rel="preconnect" href="https://fonts.googleapis.com">'
    '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
    '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible:'
    'ital,wght@0,400;0,700;1,400&family=Fraunces:opsz,wght@9..144,600;9..144,700&display=swap">'
)

# Preferencias de accesibilidad (tamaño de texto y alto contraste) recordadas en el navegador.
SCRIPT = """
<script>
(function () {
  var d = document.documentElement;
  function leer(k) { try { return localStorage.getItem(k); } catch (e) { return null; } }
  function guardar(k, v) { try { localStorage.setItem(k, v); } catch (e) {} }
  var escala = parseFloat(leer('sirima_escala')) || 1;
  function aplicar() {
    d.style.fontSize = (escala * 100) + '%';
    d.classList.toggle('alto-contraste', leer('sirima_contraste') === '1');
  }
  window.sirima = {
    fuente: function (delta) {
      escala = delta === 0 ? 1 : Math.min(1.4, Math.max(0.85, Math.round((escala + delta * 0.1) * 100) / 100));
      guardar('sirima_escala', escala); aplicar();
    },
    contraste: function () {
      guardar('sirima_contraste', leer('sirima_contraste') === '1' ? '0' : '1'); aplicar();
    }
  };
  aplicar();
  // Las filas de las tablas de incidentes se recorren y abren con el teclado (Tab + Enter).
  function filas() {
    document.querySelectorAll('.tabla-incidentes tbody tr:not([data-a11y])').forEach(function (tr) {
      tr.setAttribute('data-a11y', '1'); tr.setAttribute('tabindex', '0');
    });
  }
  document.addEventListener('keydown', function (e) {
    if ((e.key === 'Enter' || e.key === ' ') && e.target.matches && e.target.matches('.tabla-incidentes tbody tr')) {
      e.preventDefault(); e.target.click();
    }
  });
  new MutationObserver(filas).observe(d, { childList: true, subtree: true });
  document.addEventListener('DOMContentLoaded', filas);
})();
</script>
"""

CSS = """
:root {
  --c0:#00ffff; --c1:#00e6e6; --c2:#00cccc; --c3:#00b3b3; --c4:#009999; --c5:#008080;
  --c6:#006666; --c7:#004c4c; --c8:#003333; --c9:#001919;
  --tinta:#001919; --suave:#3a6666; --fondo:#eefafa; --superficie:#ffffff; --borde:#b3e6e6;
  --acento:#006666; --acento-suave:#e0f8f8; --foco:#006666;
  --cab-fondo:#ffffff; --cab-texto:#001919; --cab-suave:#3a6666;
  --menu-fondo:#ffffff; --menu-texto:#004c4c; --menu-suave:#3a6666; --menu-hover:#e0f8f8;
  --menu-activo-fondo:#006666; --menu-activo-texto:#ffffff; --menu-linea:#b3e6e6;
  --radio:16px; --sombra:0 1px 2px rgba(0,51,51,.06), 0 8px 24px -12px rgba(0,51,51,.18);
  --titulos:'Fraunces',Georgia,'Times New Roman',serif;
}

/* ===== Identidad por rol: mismo sistema, distinta personalidad ===== */
body.rol-publico, body.rol-ciudadano { --acento:#006666; --fondo:#eefafa; }
body.rol-funcionario { --acento:#004c4c; --acento-suave:#d9f4f4; --fondo:#e8f4f4; --foco:#004c4c;
  --cab-fondo:#004c4c; --cab-texto:#ffffff; --cab-suave:#b3f5f5;
  --menu-fondo:#003333; --menu-texto:#d6f7f7; --menu-suave:#7fe0e0; --menu-hover:rgba(0,255,255,.10);
  --menu-activo-fondo:#00e6e6; --menu-activo-texto:#001919; --menu-linea:rgba(0,255,255,.2); }
body.rol-responsable { --acento:#006666; --acento-suave:#d4f9f9; --fondo:#e6fafa;
  --cab-fondo:#006666; --cab-texto:#ffffff; --cab-suave:#c9fafa;
  --menu-fondo:#d4f6f6; --menu-texto:#003333; --menu-suave:#1f5555; --menu-hover:#b8efef;
  --menu-activo-fondo:#006666; --menu-activo-texto:#ffffff; --menu-linea:#8fe3e3; }
body.rol-administrador { --acento:#003333; --acento-suave:#d6eeee; --fondo:#e9f2f2; --foco:#003333;
  --cab-fondo:#001919; --cab-texto:#ffffff; --cab-suave:#8ff0f0;
  --menu-fondo:#001919; --menu-texto:#b8eded; --menu-suave:#6fcfcf; --menu-hover:rgba(255,255,255,.07);
  --menu-activo-fondo:rgba(0,255,255,.14); --menu-activo-texto:#00ffff; --menu-linea:rgba(255,255,255,.14); }

html { scroll-behavior:smooth; }
body { background:var(--fondo) url('/ilustraciones/hojas.svg'); color:var(--tinta); line-height:1.55;
  font-family:'Atkinson Hyperlegible','Segoe UI',system-ui,-apple-system,Roboto,sans-serif; font-size:1rem; }
h1,h2,h3 { font-family:var(--titulos); }
a { color:var(--c6); text-underline-offset:3px; }
:focus-visible { outline:3px solid var(--foco); outline-offset:2px; border-radius:6px; }
.q-header :focus-visible, .hero :focus-visible, .q-drawer.menu-oscuro :focus-visible, .acceso-ilus :focus-visible { outline-color:var(--c0); }
.nicegui-content { padding:0 !important; gap:0 !important; align-items:stretch !important; min-height:calc(100vh - 70px); }
.pagina { width:100%; max-width:1280px; margin:0 auto; padding:24px 24px 56px; }

/* ===== Accesibilidad ===== */
.saltar { position:absolute; left:12px; top:-60px; z-index:3000; background:var(--c9); color:#fff !important; padding:12px 18px; border-radius:10px; font-weight:700; transition:top .15s; }
.saltar:focus { top:12px; outline:3px solid var(--c0); }
.herramientas { display:flex; align-items:center; gap:2px; padding:2px; border-radius:999px; border:1px solid color-mix(in srgb, var(--cab-texto) 28%, transparent); }
.herramientas .q-btn { color:var(--cab-texto) !important; min-height:36px !important; min-width:36px !important; padding:0 !important; }
.herramientas .q-btn:hover { background:color-mix(in srgb, var(--cab-texto) 14%, transparent); }
html.alto-contraste { --fondo:#ffffff; --tinta:#000000; --suave:#001919; --borde:#003333; --c6:#003333; --acento:#003333;
  --acento-suave:#e6ffff; --cab-fondo:#000000; --cab-texto:#ffffff; --cab-suave:#00ffff; --foco:#000000;
  --menu-fondo:#000000; --menu-texto:#ffffff; --menu-suave:#00ffff; --menu-hover:rgba(255,255,255,.16);
  --menu-activo-fondo:#00ffff; --menu-activo-texto:#000000; --menu-linea:#ffffff; }
html.alto-contraste body { background-image:none; }
html.alto-contraste .tarjeta, html.alto-contraste .tile, html.alto-contraste .acceso, html.alto-contraste .caso { border:2px solid #000 !important; box-shadow:none !important; }
html.alto-contraste a { text-decoration:underline; }
html.alto-contraste .chip { border:2px solid #000 !important; }
@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation:none !important; transition:none !important; scroll-behavior:auto !important; } }

/* ===== Cabecera ===== */
.q-header { background:var(--cab-fondo) !important; color:var(--cab-texto) !important;
  box-shadow:0 1px 0 color-mix(in srgb, var(--cab-texto) 12%, transparent), 0 6px 20px -10px rgba(0,51,51,.35); }
.logo { width:46px; height:46px; border-radius:14px; background:linear-gradient(145deg,var(--c5),var(--c8)); display:flex; align-items:center; justify-content:center; box-shadow:inset 0 0 0 2px rgba(0,255,255,.35); flex-shrink:0; }
.marca { line-height:1.15; text-decoration:none; color:inherit !important; }
.marca b { font-family:var(--titulos); font-size:1.2rem; font-weight:700; }
.marca span { font-size:.78rem; color:var(--cab-suave); }
.ambito { display:inline-flex; align-items:center; gap:8px; font-weight:700; font-size:.9rem; padding:6px 14px; border-radius:999px;
  background:color-mix(in srgb, var(--cab-texto) 10%, transparent); }
.btn-cab.q-btn { color:var(--cab-texto) !important; }

/* ===== Menú lateral derecho (desplazable e independiente del contenido) ===== */
.q-drawer { background:var(--menu-fondo) !important; color:var(--menu-texto); }
.q-drawer__content { overflow-y:auto !important; overflow-x:hidden; overscroll-behavior:contain; scrollbar-width:thin; scrollbar-color:var(--menu-suave) transparent; }
.menu { display:flex; flex-direction:column; gap:4px; padding:0 14px 28px; min-height:100%; }
.menu-banda { height:104px; margin:0 -14px 8px; background-repeat:no-repeat; background-position:right bottom; background-size:cover; flex-shrink:0; }
.menu-perfil { display:flex; align-items:center; gap:12px; padding:6px 6px 14px; border-bottom:1px solid var(--menu-linea); margin-bottom:6px; }
.avatar { width:44px; height:44px; border-radius:50%; background:var(--c6); color:#fff; display:flex; align-items:center; justify-content:center; font-weight:700; font-family:var(--titulos); flex-shrink:0; }
.menu-perfil b { display:block; line-height:1.2; color:var(--menu-texto); }
.menu-perfil span { font-size:.8rem; color:var(--menu-suave); }
.menu-grupo { font-size:.72rem; letter-spacing:.09em; text-transform:uppercase; padding:14px 12px 4px; color:var(--menu-suave); font-weight:700; }
.menu-item { display:flex; align-items:center; gap:12px; padding:11px 14px; border-radius:14px; text-decoration:none !important; color:var(--menu-texto) !important; font-weight:700; transition:background .15s, transform .15s; }
.menu-item:hover { background:var(--menu-hover); transform:translateX(-3px); }
.menu-item.activa { background:var(--menu-activo-fondo); color:var(--menu-activo-texto) !important; }
.menu-item .q-icon { font-size:1.3rem; }
.menu-item .conteo { margin-left:auto; min-width:26px; text-align:center; font-size:.78rem; padding:1px 8px; border-radius:999px; background:var(--c0); color:var(--c9); }
.menu-widget { margin-top:14px; padding:14px; border-radius:16px; border:1px solid var(--menu-linea); background:color-mix(in srgb, var(--menu-texto) 6%, transparent); display:flex; flex-direction:column; gap:8px; }
.menu-widget h3 { font-size:1rem; margin:0; font-weight:700; color:var(--menu-texto); }
.menu-widget .fila { display:flex; justify-content:space-between; font-size:.92rem; }
.menu-widget .fila b { font-family:var(--titulos); font-size:1.15rem; }
.menu-pie { margin-top:auto; padding-top:16px; }
.menu-pie .q-btn { width:100%; border:1.5px solid var(--menu-linea) !important; color:var(--menu-texto) !important; }
/* Personalidad del menú por rol */
body.rol-responsable .menu-item { padding:15px 16px; border-radius:20px; font-size:1.05rem; }
body.rol-responsable .menu-item .q-icon { font-size:1.6rem; }
body.rol-administrador .menu-item { border-radius:6px; padding:10px 12px; border-left:3px solid transparent; }
body.rol-administrador .menu-item.activa { border-left-color:var(--c0); }
body.rol-funcionario .menu-item.activa .conteo { background:var(--c9); color:var(--c0); }

/* ===== Encabezado de página (común, con matiz por rol) ===== */
.cab { display:flex; flex-wrap:wrap; align-items:flex-end; justify-content:space-between; gap:14px; width:100%; }
.cab .migas { display:flex; align-items:center; gap:6px; font-size:.82rem; font-weight:700; color:var(--suave); }
h1.h { font-size:clamp(1.6rem,2.8vw,2.1rem); line-height:1.15; font-weight:700; margin:0; color:var(--c9); }
.sub { color:var(--suave); font-size:.95rem; }
body.rol-funcionario .cab { padding-bottom:12px; border-bottom:2px solid var(--borde); }
body.rol-funcionario h1.h { font-size:1.6rem; }
body.rol-responsable .cab { padding:20px 24px; border-radius:22px; background:linear-gradient(120deg,var(--c6),var(--c8)); }
body.rol-responsable h1.h, body.rol-responsable .cab .migas, body.rol-responsable .cab .sub { color:#fff; }
body.rol-responsable h1.h { font-size:2rem; }
body.rol-administrador .cab { padding:18px 22px; border-radius:12px; background:var(--c9); border-left:6px solid var(--c0); }
body.rol-administrador h1.h, body.rol-administrador .cab .migas, body.rol-administrador .cab .sub { color:#e0ffff; }
body.rol-administrador h1.h { font-size:1.55rem; }
body.rol-publico h1.h::before, body.rol-ciudadano h1.h::before { content:''; display:inline-block; width:10px; height:30px; border-radius:6px; margin-right:12px; vertical-align:-4px; background:linear-gradient(180deg,var(--c3),var(--c6)); }

/* ===== Superficies base ===== */
.tarjeta { background:var(--superficie); border:1px solid var(--borde); border-radius:var(--radio); box-shadow:var(--sombra); }
.tarjeta h2, .seccion-titulo { font-family:var(--titulos); font-size:1.25rem; font-weight:700; margin:0; }
.mono { font-family:ui-monospace,'SFMono-Regular',Menlo,Consolas,monospace; font-size:.85rem; }
.kpi { padding:18px 20px; transition:transform .15s, box-shadow .15s; }
.kpi:hover { transform:translateY(-2px); box-shadow:0 12px 28px -14px rgba(0,51,51,.35); }
.kpi .t { font-size:.88rem; color:var(--suave); font-weight:700; }
.kpi .v { font-family:var(--titulos); font-size:2.1rem; font-weight:700; line-height:1.1; }
.burbuja { width:44px; height:44px; border-radius:14px; display:flex; align-items:center; justify-content:center; flex-shrink:0; }
.anillo { --p:0; width:170px; height:170px; border-radius:50%; position:relative; display:grid; place-items:center;
  background:conic-gradient(var(--c6) calc(var(--p) * 1%), var(--acento-suave) 0); }
.anillo::before { content:''; position:absolute; inset:18px; background:#fff; border-radius:50%; }
.anillo span { position:relative; font-family:var(--titulos); font-size:2.3rem; font-weight:700; color:var(--c8); }
.kpi-tira { display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); width:100%; padding:6px 0; }
.kpi-item { display:flex; align-items:center; gap:14px; padding:14px 22px; border-right:1px solid var(--borde); }
.kpi-item:last-child { border-right:0; }
.kpi-item .v { font-family:var(--titulos); font-size:1.8rem; font-weight:700; line-height:1; }
.kpi-item .t { font-size:.82rem; color:var(--suave); font-weight:700; }

/* Estados y prioridades (semánticos: coinciden con mapa y gráficos) */
.chip { display:inline-flex; align-items:center; gap:6px; padding:3px 11px; border-radius:999px; font-size:.8rem; font-weight:700; border:1px solid transparent; white-space:nowrap; }
.chip::before { content:''; width:8px; height:8px; border-radius:50%; background:currentColor; }
.chip-REPORTADO { background:#fff3d1; color:#7a3d00; border-color:#f5c660; }
.chip-EN_REVISION { background:#dce9ff; color:#173f94; border-color:#a9c6ff; }
.chip-EN_ATENCION { background:#ece3ff; color:#4c1d95; border-color:#c9b3ff; }
.chip-ATENDIDO { background:#d3f7e6; color:#065f46; border-color:#8fdcbc; }
.chip-CERRADO { background:#e6ecec; color:#37474a; border-color:#c3cfcf; }
.chip-BAJA { background:#e8eaff; color:#3730a3; } .chip-MEDIA { background:#d9f4f4; color:#004c4c; }
.chip-ALTA { background:#ffe9c2; color:#7a3d00; } .chip-URGENTE { background:#ffdede; color:#8f1414; } .chip-VENCIDO { background:#ffdede; color:#8f1414; }
.chip-BAJA::before,.chip-MEDIA::before,.chip-ALTA::before,.chip-URGENTE::before,.chip-VENCIDO::before { border-radius:2px; }
.chip-rol-CIUDADANO { background:#d9f4f4; color:#004c4c; } .chip-rol-FUNCIONARIO { background:#c9f0f0; color:#003333; }
.chip-rol-RESPONSABLE { background:#b8eded; color:#001919; } .chip-rol-ADMINISTRADOR { background:#001919; color:#00ffff; }

/* ===== Rejillas y composiciones ===== */
.bento { display:grid; grid-template-columns:repeat(12,minmax(0,1fr)); gap:18px; width:100%; }
.b-4 { grid-column:span 4; } .b-5 { grid-column:span 5; } .b-6 { grid-column:span 6; } .b-7 { grid-column:span 7; } .b-8 { grid-column:span 8; } .b-12 { grid-column:span 12; }
.dos-col { display:grid; grid-template-columns:minmax(0,1fr) 330px; gap:22px; width:100%; align-items:start; }
.dos-col > aside { position:sticky; top:86px; display:flex; flex-direction:column; gap:16px; }
.rail-trabajo { display:grid; grid-template-columns:290px minmax(0,1fr); gap:20px; width:100%; align-items:start; }
.rail-trabajo > aside { position:sticky; top:86px; }
.lista-campo { display:grid; grid-template-columns:380px minmax(0,1fr); gap:20px; width:100%; align-items:start; }
.grid-2 { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:18px; width:100%; }
.grid-3 { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:16px; width:100%; }
.grid-auto { display:grid; grid-template-columns:repeat(auto-fill,minmax(270px,1fr)); gap:16px; width:100%; }
.tira { display:flex; gap:14px; overflow-x:auto; padding:4px 2px 12px; width:100%; scroll-snap-type:x proximity; scrollbar-width:thin; }
.tira > * { flex:0 0 290px; scroll-snap-align:start; }
.form-grid { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; width:100%; }
.form-grid .ancho { grid-column:1 / -1; }
.panel-indic { display:grid; grid-template-columns:minmax(0,1fr) minmax(0,1.6fr); gap:18px; width:100%; align-items:stretch; }
.tablero { display:grid; grid-template-columns:minmax(260px,1fr) minmax(0,2fr); gap:18px; width:100%; align-items:stretch; }
.tablero .rejilla-kpi { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:14px; }
@media (max-width:1100px) {
  .dos-col, .rail-trabajo, .lista-campo, .panel-indic, .tablero { grid-template-columns:1fr; }
  .dos-col > aside, .rail-trabajo > aside { position:static; }
  .b-4,.b-5,.b-6,.b-7,.b-8 { grid-column:span 12; }
  .grid-3 { grid-template-columns:repeat(2,minmax(0,1fr)); }
}
@media (max-width:640px) { .grid-2,.grid-3,.form-grid,.tablero .rejilla-kpi { grid-template-columns:1fr; } .pagina { padding:16px 14px 40px; } }

/* ===== Portal ciudadano ===== */
.hero { position:relative; overflow:hidden; isolation:isolate; border-radius:28px; min-height:400px; color:#fff; padding:44px clamp(22px,4vw,48px);
  display:flex; flex-direction:column; justify-content:center; background:var(--c8) url('/ilustraciones/bosque.svg') center/cover no-repeat; box-shadow:var(--sombra); }
.hero::before { content:''; position:absolute; inset:0; z-index:-1; background:linear-gradient(90deg, rgba(0,25,25,.94) 0%, rgba(0,25,25,.78) 45%, rgba(0,25,25,.12) 88%); }
.hero h1 { font-size:clamp(1.9rem,3.6vw,2.8rem); font-weight:700; line-height:1.12; margin:0 0 14px; max-width:600px; }
.hero .lead { max-width:540px; font-size:1.08rem; color:#e6fcfc; }
.insignia { display:inline-flex; align-items:center; gap:8px; align-self:flex-start; padding:6px 14px; border-radius:999px; background:rgba(0,255,255,.14); border:1px solid rgba(0,255,255,.45); color:#b3ffff; font-weight:700; font-size:.88rem; margin-bottom:16px; }
.btn-hero-1 { background:var(--c0) !important; color:var(--c9) !important; font-weight:700; }
.btn-hero-1:hover { background:#fff !important; }
.btn-hero-2 { color:#fff !important; border:2px solid rgba(255,255,255,.85) !important; font-weight:700; }
.hoja-flota { position:absolute; z-index:-1; width:24px; height:24px; opacity:.5; pointer-events:none; background:radial-gradient(ellipse at 30% 30%, var(--c1), var(--c4)); border-radius:0 100% 0 100%; animation:flotar 11s ease-in-out infinite; }
@keyframes flotar { 0%{transform:translate(0,-30px) rotate(0)} 50%{transform:translate(-40px,190px) rotate(160deg)} 100%{transform:translate(10px,400px) rotate(320deg); opacity:0} }
.consulta { padding:22px; display:flex; flex-direction:column; gap:10px; background:linear-gradient(160deg,#fff,var(--acento-suave)); }
.consejo { padding:20px 22px; background:linear-gradient(135deg,var(--c8),var(--c6)); color:#fff; border-radius:var(--radio); display:flex; flex-direction:column; gap:8px; height:100%; }
.consejo .q-icon { color:var(--c0); } .consejo .txt { font-size:1.02rem; min-height:4.6em; }
.consejo .q-btn { color:var(--c0) !important; border:1.5px solid rgba(0,255,255,.6) !important; align-self:flex-start; }
.pasos-linea { display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:0; position:relative; padding:8px 4px 0; }
.pasos-linea::before { content:''; position:absolute; left:8%; right:8%; top:36px; height:3px; background:repeating-linear-gradient(90deg,var(--c3) 0 10px,transparent 10px 18px); }
.pasos-linea .p { display:flex; flex-direction:column; align-items:center; text-align:center; gap:6px; padding:0 14px; position:relative; }
.pasos-linea .num { width:56px; height:56px; border-radius:50%; background:linear-gradient(145deg,var(--c2),var(--c5)); color:var(--c9); display:flex; align-items:center; justify-content:center; box-shadow:0 0 0 6px #fff; }
.pasos-linea .t2 { font-family:var(--titulos); font-size:1.1rem; font-weight:700; }
@media (max-width:700px) { .pasos-linea { grid-template-columns:1fr; gap:18px; } .pasos-linea::before { display:none; } }
.tiles { display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:14px; width:100%; }
.tile { display:flex; flex-direction:column; gap:6px; padding:18px; text-decoration:none !important; color:var(--tinta) !important; background:var(--superficie); border:1px solid var(--borde); border-radius:var(--radio); box-shadow:var(--sombra); transition:transform .18s, border-color .18s, background .18s; }
.tile:hover, .tile:focus-visible { transform:translateY(-4px); border-color:var(--c4); background:var(--acento-suave); }
.tile .ic { width:46px; height:46px; border-radius:14px; display:flex; align-items:center; justify-content:center; background:var(--c8); color:var(--c0); transition:transform .18s; }
.tile:hover .ic { transform:rotate(-6deg) scale(1.06); } .tile .d { font-size:.9rem; color:var(--suave); }
.aside-ayuda { padding:20px; display:flex; flex-direction:column; gap:10px; }
.aside-ayuda img, .aside-ayuda .q-img { border-radius:14px; }
.check { display:flex; gap:10px; align-items:flex-start; font-size:.93rem; }
.check .q-icon { color:var(--c5); margin-top:2px; }
.buscador { padding:22px; display:flex; gap:12px; align-items:center; flex-wrap:wrap; background:linear-gradient(120deg,var(--c8),var(--c6)); border-radius:var(--radio); color:#fff; }
.buscador .q-field--outlined .q-field__control { background:#fff; }
.caso { background:var(--superficie); border:1px solid var(--borde); border-radius:var(--radio); box-shadow:var(--sombra); padding:16px 18px; display:flex; flex-direction:column; gap:8px; cursor:pointer; text-align:left; transition:transform .15s, border-color .15s; border-left:6px solid var(--c4); }
.caso:hover, .caso:focus-visible { transform:translateY(-3px); border-color:var(--c5); }
.caso .titulo { font-weight:700; font-size:1.02rem; }
.caso.e-REPORTADO { border-left-color:#f59e0b; } .caso.e-EN_REVISION { border-left-color:#3b82f6; } .caso.e-EN_ATENCION { border-left-color:#8b5cf6; }
.caso.e-ATENDIDO { border-left-color:#10b981; } .caso.e-CERRADO { border-left-color:#6b7280; }
.caso.grande { padding:20px 22px; gap:10px; } .caso.grande .titulo { font-size:1.2rem; font-family:var(--titulos); }

/* Acceso y registro */
.acceso { display:grid; grid-template-columns:1fr 1.05fr; width:100%; max-width:940px; margin:8px auto; border-radius:26px; overflow:hidden; background:var(--superficie); border:1px solid var(--borde); box-shadow:var(--sombra); }
.acceso-ilus { position:relative; isolation:isolate; min-height:480px; padding:34px; color:#fff; display:flex; flex-direction:column; justify-content:flex-end; gap:8px; background:var(--c8) url('/ilustraciones/bosque.svg') 70% center/cover no-repeat; }
.acceso-ilus::before { content:''; position:absolute; inset:0; z-index:-1; background:linear-gradient(0deg, rgba(0,25,25,.92) 0%, rgba(0,25,25,.5) 55%, rgba(0,25,25,.08) 100%); }
.acceso-ilus h2 { font-size:1.8rem; font-weight:700; line-height:1.15; margin:0; } .acceso-ilus p { color:#d6fafa; margin:0; }
.acceso-form { padding:34px clamp(20px,4vw,38px); display:flex; flex-direction:column; gap:14px; justify-content:center; }
@media (max-width:800px) { .acceso { grid-template-columns:1fr; } .acceso-ilus { min-height:190px; } }

/* ===== Centro de gestión / Consola ===== */
.filtros-rail { padding:18px; display:flex; flex-direction:column; gap:12px; }
.filtros-rail h2 { font-size:1.1rem; }
.barra-filtros { padding:14px 16px; display:flex; flex-wrap:wrap; gap:12px; align-items:flex-end; width:100%; }
.usuario-card { padding:18px; display:flex; flex-direction:column; gap:10px; }
.usuario-card .avatar { width:52px; height:52px; font-size:1.15rem; }
.usuario-card.inactivo { opacity:.72; background:#f1f5f5; }
.cat-card { padding:18px; display:flex; flex-direction:column; gap:8px; }
.cat-card .ic { width:46px; height:46px; border-radius:14px; background:var(--c8); color:var(--c0); display:flex; align-items:center; justify-content:center; }
.feed { position:relative; margin-left:12px; padding-left:26px; border-left:3px solid var(--c3); display:flex; flex-direction:column; gap:14px; }
.feed .dia { font-family:var(--titulos); font-weight:700; margin-top:6px; position:relative; }
.feed .dia::before { content:''; position:absolute; left:-37px; top:5px; width:18px; height:18px; border-radius:50%; background:var(--c9); border:4px solid var(--c0); }
.feed .ev { position:relative; padding:12px 16px; border-radius:12px; background:#fff; border:1px solid var(--borde); }
.feed .ev::before { content:''; position:absolute; left:-34px; top:18px; width:12px; height:12px; border-radius:50%; background:var(--c6); border:3px solid #fff; box-shadow:0 0 0 2px var(--c4); }
.feed .ev .hora { font-size:.78rem; color:var(--suave); }
.vacio { padding:28px 16px; text-align:center; align-items:center; gap:6px; width:100%; }

/* ===== Detalle del caso (panel lateral y seguimiento) ===== */
.detalle-grid { display:grid; grid-template-columns:minmax(0,1.5fr) minmax(0,1fr); gap:22px; width:100%; align-items:start; }
.detalle-datos { display:grid; grid-template-columns:repeat(2,minmax(0,1fr)); gap:10px 18px; font-size:.92rem; width:100%; }
.detalle-datos .dato span { display:block; font-size:.76rem; font-weight:700; color:var(--suave); text-transform:uppercase; letter-spacing:.04em; }
@media (max-width:900px) { .detalle-grid { grid-template-columns:1fr; } }
.linea { border-left:3px solid var(--c2); margin-left:6px; padding-left:18px; }
.punto { width:14px; height:14px; border-radius:50%; background:var(--c6); margin-left:-27px; margin-top:4px; position:absolute; border:3px solid #fff; box-shadow:0 0 0 2px var(--c4); }
.paso { display:flex; align-items:center; gap:8px; }
.paso .c { width:30px; height:30px; border-radius:50%; display:flex; align-items:center; justify-content:center; font-size:.8rem; font-weight:700; background:#dff0f0; color:var(--c7); }
.paso.hecho .c { background:var(--c6); color:#fff; } .paso.actual .c { background:#fff; color:var(--c6); border:3px solid var(--c5); }
.q-dialog__inner--right { padding:0 !important; }
.panel-lateral { height:100vh; max-height:100vh !important; width:680px; max-width:100vw !important; border-radius:22px 0 0 22px !important; padding:26px !important; }

/* ===== Pie ===== */
.pie { background:var(--c9); color:#d6f7f7; margin-top:auto; }
.pie-int { max-width:1280px; margin:0 auto; padding:20px 24px; display:flex; flex-wrap:wrap; gap:12px 32px; align-items:center; justify-content:space-between; font-size:.9rem; }
.pie b { font-family:var(--titulos); color:#fff; }

/* ===== Componentes Quasar ===== */
.q-btn { border-radius:12px; font-weight:700; }
.q-btn:not(.q-btn--round):not(.q-btn--dense) { min-height:44px; padding:0 18px; }
.q-btn--outline { border-width:2px; }
.q-field--outlined .q-field__control { border-radius:12px; }
.q-field--outlined .q-field__control:before { border-color:var(--c5); }
.q-field--outlined:hover .q-field__control:before { border-color:var(--c7); }
.q-field__label { color:var(--c7); }
.q-field--dense .q-field__control { min-height:44px; }
.q-stepper { box-shadow:none; background:transparent; }
.q-stepper__tab--active .q-stepper__dot, .q-stepper__tab--done .q-stepper__dot { background:var(--acento); }
.q-stepper__title { font-weight:700; }
.q-card { border-radius:var(--radio); }
.q-dialog__backdrop { backdrop-filter:blur(3px); background:rgba(0,25,25,.55) !important; }
.q-uploader { border-radius:14px; border:2px dashed var(--c4); box-shadow:none; background:var(--acento-suave); }
.q-uploader__header { background:var(--c6) !important; }
.q-tab { font-weight:700; text-transform:none; }
.q-tabs { border-bottom:2px solid var(--borde); }
.q-linear-progress { border-radius:8px; }
.q-table__card { box-shadow:none; background:transparent; }
.q-table th { background:var(--acento-suave); color:var(--c8); font-size:.85rem; font-weight:700; }
.q-table td { font-size:.92rem; color:var(--tinta); }
.q-table tbody tr:hover { background:var(--acento-suave); }
.tabla-incidentes tbody tr { cursor:pointer; }
.tabla-incidentes tbody tr:focus-visible { outline:3px solid var(--foco); outline-offset:-3px; background:var(--acento-suave); }
.nicegui-leaflet { z-index:0; }
.leyenda i { display:inline-block; width:11px; height:11px; border-radius:50%; margin-right:6px; }
"""

AMBITO = {"publico": "Portal ciudadano", "ciudadano": "Portal ciudadano", "funcionario": "Centro de gestión",
          "responsable": "Mesa de campo", "administrador": "Consola de administración"}


def aplicar_tema(rol: str = "publico") -> None:
    ui.colors(primary="#006666", secondary="#004c4c", accent="#00b3b3", positive="#007a6b",
              negative="#b91c1c", warning="#b45309", info="#008080")
    ui.add_head_html(FUENTES)
    ui.add_head_html(SCRIPT)
    ui.add_css(CSS)
    ui.query("body").classes(f"rol-{rol}")


def chip_estado(estado: EstadoIncidente | str):
    e = EstadoIncidente(estado)
    return ui.label(e.etiqueta).classes(f"chip chip-{e.value}")


def chip_prioridad(prioridad: Prioridad | str):
    p = Prioridad(prioridad)
    return ui.label(p.etiqueta).classes(f"chip chip-{p.value}")


def kpi(titulo: str, valor: str, color: str = "#006666", icono: str | None = None) -> None:
    with ui.card().classes("tarjeta kpi gap-2 flex-1 min-w-[180px]").props("flat"):
        with ui.row().classes("items-center justify-between w-full no-wrap"):
            ui.label(titulo).classes("t")
            if icono:
                with ui.element("div").classes("burbuja").style(f"background:{color}1f"):
                    ui.icon(icono).style(f"color:{color}; font-size:1.5rem").props('aria-hidden="true"')
        ui.label(valor).classes("v").style(f"color:{color}")


def kpi_tira(items: list[tuple[str, str, str, str]]) -> None:
    """Franja única de indicadores: (título, valor, color, icono)."""
    with ui.element("div").classes("tarjeta kpi-tira"):
        for titulo, valor, color, icono in items:
            with ui.element("div").classes("kpi-item"):
                with ui.element("div").classes("burbuja").style(f"background:{color}1f"):
                    ui.icon(icono).style(f"color:{color}; font-size:1.5rem").props('aria-hidden="true"')
                with ui.column().classes("gap-0"):
                    ui.label(valor).classes("v").style(f"color:{color}")
                    ui.label(titulo).classes("t")


def encabezado(titulo: str, subtitulo: str = "", rol: str = "publico") -> ui.row:
    """Encabezado de página compartido por todas las interfaces. Devuelve la fila donde van las acciones."""
    with ui.element("div").classes("cab"):
        with ui.column().classes("gap-1"):
            ui.html(f'<div class="migas"><span>{AMBITO.get(rol, "SIRIMA")}</span><span aria-hidden="true">›</span>'
                    f'<span>{titulo}</span></div>')
            ui.html(f'<h1 class="h">{titulo}</h1>')
            if subtitulo:
                ui.label(subtitulo).classes("sub")
        return ui.row().classes("items-center gap-2")


def vacio(mensaje: str, detalle: str = "") -> None:
    with ui.column().classes("vacio"):
        ui.image("/ilustraciones/arbol.svg").classes("w-36").props('alt=""')
        ui.label(mensaje).classes("font-bold text-base")
        if detalle:
            ui.label(detalle).classes("sub")


def fmt_horas(h: float | None) -> str:
    if h is None:
        return "—"
    return f"{h / 24:.1f} días" if h >= 48 else f"{h:.1f} h"


def fmt_fecha(d, con_hora: bool = True) -> str:
    return d.strftime("%d/%m/%Y %H:%M") if con_hora else d.strftime("%d/%m/%Y")
