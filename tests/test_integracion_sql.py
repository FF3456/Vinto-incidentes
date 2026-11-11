"""Integración con SQLAlchemy/SQLite real, concurrencia y rendimiento (RNF-03, RNF-04)."""
import ast
import threading
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import pytest

from application.dto import ComandoRegistrarIncidente
from bootstrap import construir_contenedor
from domain.exceptions import AutenticacionError
from domain.policies.actor import Actor
from domain.ports.repositorios import FiltroIncidentes
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from tests.conftest import PNG

RAIZ = Path(__file__).resolve().parent.parent


@pytest.fixture
def app(tmp_path):
    return construir_contenedor(f"sqlite:///{tmp_path / 't.db'}", tmp_path / "ev", demo=True)


def cmd(app, **kw):
    cat = app.listar_categorias.ejecutar()[0]
    base = dict(categoria_id=cat.id, titulo="Basura en el canal", descripcion="Bolsas y escombros en el canal.",
                fecha_incidente=datetime.now() - timedelta(hours=1), latitud=-17.3868, longitud=-66.3142,
                referencia="Canal de riego")
    base.update(kw)
    return ComandoRegistrarIncidente(**base)


def test_semilla_crea_catalogo_cuentas_e_incidentes_demo(app):
    assert len(app.listar_categorias.ejecutar()) == 9
    a = app.autenticar.ejecutar("admin@vinto.gob.bo", "Vinto2026")
    assert a.rol == Rol.ADMINISTRADOR
    with pytest.raises(AutenticacionError):
        app.autenticar.ejecutar("admin@vinto.gob.bo", "incorrecta")
    est = app.estadisticas.ejecutar(a)
    assert est.total == 12 and set(est.por_estado) == {e.value for e in E}
    assert all(v > 0 for v in est.por_estado.values())   # la demo cubre todos los estados


def test_persistencia_ciclo_completo_en_bd(app):
    func = app.autenticar.ejecutar("funcionario@vinto.gob.bo", "Vinto2026")
    resp = app.autenticar.ejecutar("responsable@vinto.gob.bo", "Vinto2026")
    ficha = app.responsables.buscar_por_usuario(resp.usuario_id)
    i = app.registrar_incidente.ejecutar(Actor.anonimo(), cmd(app, archivos=[]))
    app.cambiar_estado.ejecutar(func, i.codigo, E.EN_REVISION)
    app.asignar_responsable.ejecutar(func, i.codigo, ficha.id)
    app.registrar_atencion.ejecutar(resp, i.codigo, "Se limpió el canal con la cuadrilla.")
    app.cambiar_estado.ejecutar(func, i.codigo, E.CERRADO, "Verificado")
    g = app.incidentes.buscar_por_codigo(i.codigo)          # relectura desde la base
    assert g.estado == E.CERRADO and g.responsable_nombre == ficha.nombre
    assert [h.estado_nuevo for h in g.historial] == list(E)
    assert g.resumen_atencion.startswith("Se limpió")


def test_evidencia_persistida_en_bd_y_disco(app, png):
    i = app.registrar_incidente.ejecutar(Actor.anonimo(), cmd(app, archivos=[png]))
    g = app.incidentes.buscar_por_codigo(i.codigo)
    assert len(g.evidencias) == 1
    assert (app.carpeta_evidencias / g.evidencias[0].ruta_archivo).read_bytes() == PNG


def test_filtros_sql_coinciden_con_los_de_memoria(app):
    func = app.autenticar.ejecutar("funcionario@vinto.gob.bo", "Vinto2026")
    todos = app.listar_incidentes.ejecutar(func)
    cat = todos[0].categoria_id
    zona = todos[0].ubicacion.zona
    esperado = [i for i in todos if i.categoria_id == cat and i.ubicacion.zona == zona and i.estado == todos[0].estado]
    obtenido = app.listar_incidentes.ejecutar(func, FiltroIncidentes(categoria_id=cat, zona=zona, estado=todos[0].estado))
    assert {i.id for i in obtenido} == {i.id for i in esperado} and obtenido
    hoy = date.today()
    assert app.listar_incidentes.ejecutar(func, FiltroIncidentes(desde=hoy + timedelta(days=1))) == []
    assert len(app.listar_incidentes.ejecutar(func, FiltroIncidentes(texto=todos[0].codigo[-4:]))) >= 1


def test_codigos_unicos_bajo_concurrencia(app):
    """Varios hilos registrando a la vez no deben obtener el mismo código de seguimiento."""
    errores, codigos = [], []

    def worker():
        try:
            codigos.append(app.registrar_incidente.ejecutar(Actor.anonimo(), cmd(app)).codigo)
        except Exception as e:   # pragma: no cover
            errores.append(e)
    hilos = [threading.Thread(target=worker) for _ in range(20)]
    [h.start() for h in hilos]
    [h.join() for h in hilos]
    assert not errores and len(set(codigos)) == 20


def test_rendimiento_consulta_menor_a_2_segundos_rnf03(app):
    func = app.autenticar.ejecutar("funcionario@vinto.gob.bo", "Vinto2026")
    for _ in range(300):
        app.registrar_incidente.ejecutar(Actor.anonimo(), cmd(app))
    t = time.perf_counter()
    lista = app.listar_incidentes.ejecutar(func, FiltroIncidentes(estado=E.REPORTADO))
    est = app.estadisticas.ejecutar(func)
    por_codigo = app.consultar_por_codigo.ejecutar(Actor.anonimo(), lista[0].codigo)
    assert time.perf_counter() - t < 2.0
    assert est.total == 312 and por_codigo.id


def test_sin_demo_no_hay_cuentas_ni_incidentes(tmp_path):
    limpio = construir_contenedor(f"sqlite:///{tmp_path / 'l.db'}", tmp_path / "e", demo=False)
    assert limpio.usuarios.listar() == [] and len(limpio.listar_categorias.ejecutar()) == 9


# ---------------------------------------------- arquitectura limpia (RNF-04)
def _imports(ruta: Path) -> set[str]:
    out = set()
    for f in ruta.rglob("*.py"):
        for n in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(n, ast.Import):
                out |= {a.name.split(".")[0] for a in n.names}
            elif isinstance(n, ast.ImportFrom) and n.module and n.level == 0:
                out.add(n.module.split(".")[0])
    return out


@pytest.mark.parametrize("capa,prohibidos", [
    ("domain", {"sqlalchemy", "nicegui", "infrastructure", "presentation", "application", "fastapi"}),
    ("application", {"sqlalchemy", "nicegui", "infrastructure", "presentation", "fastapi"}),
    ("infrastructure", {"nicegui", "presentation"}),
])
def test_la_regla_de_dependencia_se_cumple(capa, prohibidos):
    """Las dependencias apuntan hacia adentro: el dominio no conoce frameworks ni otras capas."""
    assert not (_imports(RAIZ / capa) & prohibidos)
