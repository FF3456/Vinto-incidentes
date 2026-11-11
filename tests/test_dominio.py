"""Pruebas del dominio puro: estados, ubicación, entidades y reglas (sin infraestructura)."""
from datetime import datetime, timedelta

import pytest

from domain.entities.categoria import Categoria
from domain.entities.incidente import IncidenteAmbiental
from domain.entities.usuario import Usuario
from domain.exceptions import TransicionInvalidaError, ValidacionError
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.ubicacion import Ubicacion

AHORA = datetime(2026, 10, 1, 9, 0)


def incidente(**kw) -> IncidenteAmbiental:
    datos = dict(codigo="VINTO-2026-0001", titulo="Basura", descripcion="Basura acumulada",
                 categoria_id=1, categoria_nombre="Basura", fecha_incidente=AHORA,
                 fecha_reporte=AHORA, ubicacion=Ubicacion(-17.38, -66.31, "Plaza"))
    datos.update(kw)
    i = IncidenteAmbiental(**datos)
    i.registrar_creacion("Vecino")
    return i


# ----------------------------------------------------------------- RF-06 flujo
def test_flujo_completo_en_orden():
    i = incidente()
    i.cambiar_estado(E.EN_REVISION, AHORA, "func")
    i.asignar_responsable(1, "Carlos")
    i.cambiar_estado(E.EN_ATENCION, AHORA, "func")
    i.cambiar_estado(E.ATENDIDO, AHORA, "resp")
    i.cambiar_estado(E.CERRADO, AHORA, "func")
    assert i.estado == E.CERRADO
    assert [h.estado_nuevo for h in i.historial] == list(E)


@pytest.mark.parametrize("origen,destino", [
    (E.REPORTADO, E.EN_ATENCION), (E.REPORTADO, E.CERRADO), (E.EN_REVISION, E.REPORTADO),
    (E.EN_REVISION, E.ATENDIDO), (E.ATENDIDO, E.EN_ATENCION), (E.CERRADO, E.REPORTADO),
    (E.REPORTADO, E.REPORTADO)])
def test_saltos_y_retrocesos_prohibidos(origen, destino):
    assert not origen.puede_pasar_a(destino)


def test_transicion_invalida_lanza_error_y_no_modifica():
    i = incidente()
    with pytest.raises(TransicionInvalidaError):
        i.cambiar_estado(E.CERRADO, AHORA, "func")
    assert i.estado == E.REPORTADO and len(i.historial) == 1


def test_en_atencion_exige_responsable():
    i = incidente()
    i.cambiar_estado(E.EN_REVISION, AHORA, "func")
    with pytest.raises(TransicionInvalidaError, match="responsable"):
        i.cambiar_estado(E.EN_ATENCION, AHORA, "func")


def test_asignar_responsable_solo_en_revision_o_atencion():
    with pytest.raises(TransicionInvalidaError):
        incidente().asignar_responsable(1, "Carlos")


def test_cierre_conserva_historial_rf14():
    i = incidente()
    i.cambiar_estado(E.EN_REVISION, AHORA + timedelta(hours=1), "func", "Revisado")
    h = i.historial[-1]
    assert (h.estado_anterior, h.estado_nuevo, h.observacion) == (E.REPORTADO, E.EN_REVISION, "Revisado")


def test_registrar_atencion_exige_resumen():
    i = incidente()
    i.cambiar_estado(E.EN_REVISION, AHORA, "f")
    i.asignar_responsable(1, "C")
    i.cambiar_estado(E.EN_ATENCION, AHORA, "f")
    with pytest.raises(ValidacionError):
        i.registrar_atencion("corto", AHORA, "C")
    i.registrar_atencion("Se recogió la basura con el camión.", AHORA, "C")
    assert i.estado == E.ATENDIDO and i.resumen_atencion.startswith("Se recogió")


def test_horas_hasta_y_vencimiento():
    i = incidente(plazo_horas=24)
    assert not i.esta_vencido(AHORA + timedelta(hours=23))
    assert i.esta_vencido(AHORA + timedelta(hours=25))
    i.cambiar_estado(E.EN_REVISION, AHORA + timedelta(hours=6), "f")
    assert i.horas_hasta(E.EN_REVISION) == 6
    assert i.horas_hasta(E.ATENDIDO) is None


# ------------------------------------------------------------- RF-03 ubicación
@pytest.mark.parametrize("lat,lon", [(91, 0), (-91, 0), (0, 181), (0, -181)])
def test_ubicacion_fuera_de_rango(lat, lon):
    with pytest.raises(ValidacionError):
        Ubicacion(lat, lon)


def test_ubicacion_valida_e_inmutable():
    u = Ubicacion(-17.38, -66.31, "  Plaza  ", " Zona Central ")
    assert u.referencia == "Plaza" and u.zona == "Zona Central"
    assert u.coordenadas == (-17.38, -66.31)
    with pytest.raises(Exception):
        u.latitud = 0   # type: ignore[misc]


def test_ubicacion_no_numerica():
    with pytest.raises(ValidacionError):
        Ubicacion("a", "b")  # type: ignore[arg-type]


# -------------------------------------------------------------- invariantes
def test_titulo_y_descripcion_obligatorios():
    with pytest.raises(ValidacionError):
        incidente(titulo="  ")
    with pytest.raises(ValidacionError):
        incidente(descripcion="")


def test_categoria_y_usuario_validan():
    with pytest.raises(ValidacionError):
        Categoria("ab")
    with pytest.raises(ValidacionError):
        Categoria("Válida", perfil="INEXISTENTE")
    with pytest.raises(ValidacionError):
        Usuario("Nombre Ok", "no-es-correo", "h")
    assert Usuario("Nombre Ok", " A@B.CO ", "h").correo == "a@b.co"
