"""Casos de uso (RF-01…RF-14) con repositorios en memoria y reloj controlado."""
from datetime import date, timedelta

import pytest

from application.dto import ArchivoSubido
from domain.exceptions import (
    AutenticacionError, DuplicadoError, EvidenciaInvalidaError, NoEncontradoError,
    PermisoDenegadoError, TransicionInvalidaError, ValidacionError)
from domain.ports.repositorios import FiltroIncidentes
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from tests.conftest import PNG


# ------------------------------------------------- RF-01 / RF-02 / RF-03 / RF-12
def test_registrar_incidente_ok_genera_codigo_estado_y_zona(mundo):
    i = mundo.nuevo()
    assert i.codigo == "VINTO-2026-0001" and i.estado == E.REPORTADO
    assert i.ubicacion.zona == "Zona Central"          # RF-03: zona derivada de coordenadas
    assert i.reportante_id == mundo.vecino.usuario_id
    assert i.historial[0].estado_nuevo == E.REPORTADO   # RF-14
    assert mundo.auditoria.registros[-1].accion == "Incidente registrado"


def test_codigos_unicos_y_consecutivos(mundo):
    codigos = [mundo.nuevo().codigo for _ in range(5)]
    assert len(set(codigos)) == 5 and codigos[-1] == "VINTO-2026-0005"


def test_registro_anonimo_permitido(mundo):
    i = mundo.nuevo(actor=mundo.anonimo)
    assert i.reportante_id is None


@pytest.mark.parametrize("cambio,error", [
    ({"categoria_id": 999}, "categoría"),
    ({"latitud": -12.0, "longitud": -77.0}, "fuera del área"),
    ({"referencia": " "}, "referencia"),
    ({"titulo": ""}, "título"),
    ({"descripcion": "corta"}, "descripción"),
    ({"fecha_incidente": None}, None)])
def test_registro_rechaza_datos_invalidos(mundo, cambio, error):
    if error is None:
        cambio = {"fecha_incidente": mundo.reloj.ahora + timedelta(days=2)}
        error = "futura"
    with pytest.raises(ValidacionError, match=f"(?i){error}"):
        mundo.nuevo(**cambio)
    assert mundo.incidentes.listar() == []     # nada se guardó


def test_categoria_inactiva_no_permite_registrar(mundo):
    mundo.categorias_uc.cambiar_activa(mundo.admin, mundo.cat_basura.id, False)
    with pytest.raises(ValidacionError):
        mundo.nuevo()


# ------------------------------------------------------------------- RF-04
def test_adjuntar_evidencia_ok(mundo, png):
    i = mundo.nuevo(archivos=[png, png])
    assert len(i.evidencias) == 2 and i.evidencias[0].tipo == "REPORTE"
    assert mundo.almacen.url_publica(i.evidencias[0].ruta_archivo).startswith("/evidencias/")


def test_evidencia_invalida_rechazada(mundo):
    with pytest.raises(EvidenciaInvalidaError):
        mundo.nuevo(archivos=[ArchivoSubido("x.png", b"no soy imagen")])


def test_maximo_tres_fotos(mundo, png):
    with pytest.raises(ValidacionError, match="máximo"):
        mundo.nuevo(archivos=[png] * 4)


# ------------------------------------------------------------ RF-05 filtros
@pytest.fixture
def poblado(mundo):
    a = mundo.nuevo(titulo="Basura plaza")                                   # Zona Central
    mundo.reloj.avanzar(days=2)
    b = mundo.nuevo(categoria_id=mundo.cat_rio.id, titulo="Río contaminado",
                    descripcion="El río lleva espuma y aceite desde ayer.",
                    latitud=-17.3745, longitud=-66.3140)                    # Zona Norte
    mundo.reloj.avanzar(days=2)
    c = mundo.nuevo(titulo="Basura mercado", latitud=-17.3985, longitud=-66.3140)  # Zona Sur
    mundo.cambiar.ejecutar(mundo.func, a.codigo, E.EN_REVISION)
    return a, b, c


def test_filtros_individuales_y_combinados(mundo, poblado):
    L = lambda **kw: mundo.listar.ejecutar(mundo.func, FiltroIncidentes(**kw))
    assert len(L()) == 3
    assert len(L(categoria_id=mundo.cat_basura.id)) == 2
    assert [i.titulo for i in L(estado=E.EN_REVISION)] == ["Basura plaza"]
    assert [i.titulo for i in L(zona="Zona Norte")] == ["Río contaminado"]
    assert len(L(desde=date(2026, 10, 3))) == 2
    assert len(L(hasta=date(2026, 10, 3))) == 2
    assert [i.titulo for i in L(texto="mercado")] == ["Basura mercado"]
    assert [i.titulo for i in L(categoria_id=mundo.cat_basura.id, zona="Zona Sur")] == ["Basura mercado"]
    assert L(categoria_id=mundo.cat_rio.id, estado=E.CERRADO) == []


def test_listado_ordenado_mas_reciente_primero(mundo, poblado):
    titulos = [i.titulo for i in mundo.listar.ejecutar(mundo.func)]
    assert titulos[0] == "Basura mercado"


# ------------------------------------------------- RF-06 / RF-07 / RF-14
def test_flujo_completo_con_roles(mundo, png):
    i = mundo.nuevo()
    c = i.codigo
    mundo.cambiar.ejecutar(mundo.func, c, E.EN_REVISION, "Verificado en sitio")
    with pytest.raises(TransicionInvalidaError, match="responsable"):
        mundo.cambiar.ejecutar(mundo.func, c, E.EN_ATENCION)
    mundo.reloj.avanzar(hours=5)
    r = mundo.asignar.ejecutar(mundo.func, c, mundo.resp.id)
    assert r.estado == E.EN_ATENCION and r.responsable_nombre == "Carlos Mamani"  # asigna y avanza
    mundo.reloj.avanzar(hours=3)
    r = mundo.atender.ejecutar(mundo.resp_actor, c, "Se retiró la basura con el camión.", [png])
    assert r.estado == E.ATENDIDO and r.evidencias[-1].tipo == "ATENCION"
    r = mundo.cambiar.ejecutar(mundo.func, c, E.CERRADO, "Verificado")
    assert r.estado == E.CERRADO
    assert [h.estado_nuevo for h in r.historial] == list(E)
    assert len(mundo.por_codigo.ejecutar(mundo.anonimo, c).historial) == 5


def test_cambio_con_transicion_invalida(mundo):
    i = mundo.nuevo()
    with pytest.raises(TransicionInvalidaError):
        mundo.cambiar.ejecutar(mundo.func, i.codigo, E.CERRADO)


def test_asignar_responsable_inexistente_o_inactivo(mundo):
    i = mundo.nuevo()
    mundo.cambiar.ejecutar(mundo.func, i.codigo, E.EN_REVISION)
    with pytest.raises(NoEncontradoError):
        mundo.asignar.ejecutar(mundo.func, i.codigo, 999)
    r = mundo.responsables.buscar_por_id(mundo.resp.id)
    r.activo = False
    mundo.responsables.guardar(r)
    with pytest.raises(NoEncontradoError):
        mundo.asignar.ejecutar(mundo.func, i.codigo, mundo.resp.id)


def test_cambiar_estado_codigo_inexistente(mundo):
    with pytest.raises(NoEncontradoError):
        mundo.cambiar.ejecutar(mundo.func, "VINTO-0000-0000", E.EN_REVISION)


# ------------------------------------------------------------- RF-13 / HU-02
def test_consulta_por_codigo_ignora_mayusculas_y_espacios(mundo):
    i = mundo.nuevo()
    assert mundo.por_codigo.ejecutar(mundo.anonimo, f"  {i.codigo.lower()} ").id == i.id
    with pytest.raises(NoEncontradoError):
        mundo.por_codigo.ejecutar(mundo.anonimo, "NO-EXISTE")


def test_mis_reportes_solo_los_propios(mundo):
    mundo.nuevo(actor=mundo.vecino)
    mundo.nuevo(actor=mundo.anonimo)
    assert len(mundo.mis.ejecutar(mundo.vecino)) == 1
    assert mundo.mis.ejecutar(mundo.anonimo) == []


# ------------------------------------------------------------------- RF-08
def test_marcadores_para_funcionario_y_filtrados_para_responsable(mundo):
    a, b = mundo.nuevo(), mundo.nuevo(titulo="Otro caso de basura")
    mundo.llevar_a_atencion(a.codigo)
    assert len(mundo.marcadores.ejecutar(mundo.func)) == 2
    solo_suyos = mundo.marcadores.ejecutar(mundo.resp_actor)
    assert [m.codigo for m in solo_suyos] == [a.codigo]
    assert mundo.marcadores.ejecutar(mundo.otro_actor) == []


# ------------------------------------------------------------------- RF-09
def test_estadisticas_tiempos_y_zonas_criticas(mundo):
    a = mundo.nuevo()                                         # atendido: respuesta 8 h, resolución 20 h
    mundo.reloj.avanzar(hours=2)
    mundo.cambiar.ejecutar(mundo.func, a.codigo, E.EN_REVISION)
    mundo.reloj.avanzar(hours=6)
    mundo.asignar.ejecutar(mundo.func, a.codigo, mundo.resp.id)
    mundo.reloj.avanzar(hours=12)
    mundo.atender.ejecutar(mundo.resp_actor, a.codigo, "Limpieza realizada por la cuadrilla.")
    mundo.nuevo(latitud=-17.3745, longitud=-66.3140)          # abierto, Zona Norte
    mundo.nuevo(latitud=-17.3745, longitud=-66.3140)
    e = mundo.stats.ejecutar(mundo.func)
    assert e.total == 3 and e.pendientes == 2 and e.resueltos == 1
    assert e.tasa_resolucion == 33.3
    assert e.tiempo_medio_respuesta_h == 8.0 and e.tiempo_medio_resolucion_h == 20.0
    assert e.por_estado["REPORTADO"] == 2 and e.por_categoria["Acumulación de basura"] == 3
    assert e.zonas_criticas[0].zona == "Zona Norte" and e.zonas_criticas[0].abiertos == 2
    assert len(e.por_mes) == 6


def test_estadisticas_sin_datos(mundo):
    e = mundo.stats.ejecutar(mundo.admin)
    assert e.total == 0 and e.tiempo_medio_respuesta_h is None and e.zonas_criticas == []


def test_incidentes_vencidos(mundo):
    mundo.nuevo(categoria_id=mundo.cat_rio.id, descripcion="Vertido de aceite en el canal principal.")  # 24 h
    mundo.reloj.avanzar(hours=30)
    assert mundo.stats.ejecutar(mundo.func).vencidos == 1


# ------------------------------------------------------------ RF-10 (RBAC)
@pytest.mark.parametrize("actor,accion", [
    ("vecino", lambda m, c: m.cambiar.ejecutar(m.vecino, c, E.EN_REVISION)),
    ("anonimo", lambda m, c: m.cambiar.ejecutar(m.anonimo, c, E.EN_REVISION)),
    ("responsable", lambda m, c: m.cambiar.ejecutar(m.resp_actor, c, E.EN_REVISION)),
    ("vecino", lambda m, c: m.asignar.ejecutar(m.vecino, c, m.resp.id)),
    ("responsable", lambda m, c: m.asignar.ejecutar(m.resp_actor, c, m.resp.id)),
    ("vecino", lambda m, c: m.listar.ejecutar(m.vecino)),
    ("vecino", lambda m, c: m.stats.ejecutar(m.vecino)),
    ("responsable", lambda m, c: m.stats.ejecutar(m.resp_actor)),
    ("funcionario", lambda m, c: m.usuarios_uc.listar(m.func)),
    ("funcionario", lambda m, c: m.categorias_uc.crear(m.func, "Nueva", "", "GENERICO")),
    ("vecino", lambda m, c: m.atender.ejecutar(m.vecino, c, "Intento de atención indebida")),
    ("funcionario", lambda m, c: m.marcadores.ejecutar(m.anonimo)),
])
def test_rbac_deniega_acciones_no_permitidas(mundo, actor, accion):
    i = mundo.nuevo()
    with pytest.raises(PermisoDenegadoError):
        accion(mundo, i.codigo)


def test_funcionario_no_puede_marcar_atendido_pero_responsable_si(mundo):
    i = mundo.nuevo()
    mundo.llevar_a_atencion(i.codigo)
    with pytest.raises(PermisoDenegadoError):
        mundo.cambiar.ejecutar(mundo.func, i.codigo, E.ATENDIDO)
    mundo.atender.ejecutar(mundo.resp_actor, i.codigo, "Trabajo concluido en el lugar.")


def test_responsable_no_atiende_casos_ajenos(mundo):
    i = mundo.nuevo()
    mundo.llevar_a_atencion(i.codigo)
    with pytest.raises(PermisoDenegadoError, match="no está asignado"):
        mundo.atender.ejecutar(mundo.otro_actor, i.codigo, "Intento sobre caso ajeno aaa")


def test_administrador_tiene_acceso_total(mundo):
    i = mundo.nuevo()
    mundo.cambiar.ejecutar(mundo.admin, i.codigo, E.EN_REVISION)
    assert mundo.stats.ejecutar(mundo.admin).total == 1
    assert len(mundo.usuarios_uc.listar(mundo.admin)) >= 2


# ----------------------------------------------- autenticación y administración
def test_registro_y_login_ciudadano(mundo):
    a = mundo.reg_ciudadano.ejecutar("Ana Pérez", "ANA@mail.com", "secreto1")
    assert a.rol == Rol.CIUDADANO
    assert mundo.autenticar.ejecutar("ana@mail.com", "secreto1").usuario_id == a.usuario_id
    with pytest.raises(AutenticacionError, match="incorrectos"):
        mundo.autenticar.ejecutar("ana@mail.com", "mala")
    with pytest.raises(AutenticacionError, match="incorrectos"):   # no revela si el correo existe
        mundo.autenticar.ejecutar("nadie@mail.com", "secreto1")
    with pytest.raises(DuplicadoError):
        mundo.reg_ciudadano.ejecutar("Ana Pérez", "ana@mail.com", "secreto1")
    with pytest.raises(ValidacionError):
        mundo.reg_ciudadano.ejecutar("Luis Gómez", "luis@mail.com", "123")


def test_usuario_inactivo_no_ingresa(mundo):
    a = mundo.reg_ciudadano.ejecutar("Ana Pérez", "ana@mail.com", "secreto1")
    mundo.usuarios_uc.cambiar_activo(mundo.admin, a.usuario_id, False)
    with pytest.raises(AutenticacionError):
        mundo.autenticar.ejecutar("ana@mail.com", "secreto1")


def test_admin_crea_responsable_con_ficha_y_no_se_autodesactiva(mundo):
    u = mundo.usuarios_uc.crear(mundo.admin, "Nuevo Resp", "nr@vinto.test", "clave123", Rol.RESPONSABLE, "Cuadrilla Norte")
    assert mundo.responsables.buscar_por_usuario(u.id).unidad == "Cuadrilla Norte"
    with pytest.raises(ValidacionError):
        mundo.usuarios_uc.cambiar_activo(mundo.admin, mundo.admin.usuario_id, False)


def test_categorias_crud_sin_borrar_historicos(mundo):
    c = mundo.categorias_uc.crear(mundo.admin, "Contaminación lumínica", "Exceso de luz", "GENERICO")
    with pytest.raises(DuplicadoError):
        mundo.categorias_uc.crear(mundo.admin, "contaminación lumínica", "", "GENERICO")
    mundo.categorias_uc.editar(mundo.admin, c.id, "Contaminación lumínica urbana", "", "RUIDO")
    mundo.categorias_uc.cambiar_activa(mundo.admin, c.id, False)
    assert c.id not in [x.id for x in mundo.listar_cat.ejecutar(solo_activas=True)]
    assert c.id in [x.id for x in mundo.listar_cat.ejecutar(solo_activas=False)]


def test_privacidad_contacto_oculto_para_ciudadanos_pero_visible_para_personal(mundo):
    i = mundo.nuevo(contacto_nombre="Ana Pérez", contacto_medio="70000000")
    publico = mundo.por_codigo.ejecutar(mundo.anonimo, i.codigo)
    assert publico.contacto_nombre == "" and publico.contacto_medio == ""
    interno = mundo.por_codigo.ejecutar(mundo.func, i.codigo)
    assert interno.contacto_nombre == "Ana Pérez" and interno.contacto_medio == "70000000"
