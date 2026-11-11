"""Patrones Factory (OCP) y Adapter (DIP) + almacenamiento y hashing."""
from datetime import datetime, timedelta

import pytest

from domain.entities.categoria import Categoria
from domain.exceptions import EvidenciaInvalidaError, ValidacionError
from domain.factories.incidente_factory import IncidenteFactory, PoliticaCategoria
from domain.ports.servicio_geografico import ServicioGeografico
from domain.value_objects.prioridad import Prioridad
from domain.value_objects.ubicacion import Ubicacion
from infrastructure.maps.adaptadores import (
    AdaptadorCartoClaro, AdaptadorOpenStreetMap, crear_servicio_geografico)
from infrastructure.security.hasher import HasheadorPBKDF2
from infrastructure.storage.almacenamiento_local import AlmacenamientoLocal
from tests.conftest import JPG, PNG

AHORA = datetime(2026, 10, 1, 9, 0)
UBI = Ubicacion(-17.38, -66.31, "Plaza")


def crear(factory, categoria, descripcion="Descripción suficientemente larga y clara."):
    return factory.crear(categoria=categoria, codigo="C-1", titulo="Título", descripcion=descripcion,
                         fecha_incidente=AHORA, fecha_reporte=AHORA, ubicacion=UBI)


# ----------------------------------------------------------------- Factory
@pytest.mark.parametrize("perfil,prioridad,plazo", [
    ("AGUA", Prioridad.URGENTE, 24), ("AIRE", Prioridad.ALTA, 48), ("RESIDUOS", Prioridad.MEDIA, 72),
    ("RUIDO", Prioridad.BAJA, 120), ("GENERICO", Prioridad.MEDIA, 72)])
def test_factory_aplica_politica_por_perfil(perfil, prioridad, plazo):
    i = crear(IncidenteFactory(), Categoria("Categoría X", "", perfil, True, 1))
    assert (i.prioridad, i.plazo_horas) == (prioridad, plazo)


def test_factory_rechaza_categoria_inactiva_fecha_futura_y_descripcion_corta():
    f = IncidenteFactory()
    with pytest.raises(ValidacionError):
        crear(f, Categoria("Categoría X", "", "AGUA", False, 1))
    with pytest.raises(ValidacionError):
        f.crear(categoria=Categoria("Categoría X", id=1), codigo="C", titulo="T", descripcion="d" * 30,
                fecha_incidente=AHORA + timedelta(days=1), fecha_reporte=AHORA, ubicacion=UBI)
    with pytest.raises(ValidacionError):   # AGUA exige 20 caracteres
        crear(f, Categoria("Categoría X", "", "AGUA", True, 1), "muy corta aaaa")


def test_factory_es_extensible_sin_modificarla_ocp():
    class PoliticaSismo(PoliticaCategoria):
        prioridad, plazo_horas = Prioridad.URGENTE, 2
    f = IncidenteFactory()
    f.registrar_politica("SISMO", PoliticaSismo())
    cat = Categoria("Categoría X", "", "GENERICO", True, 1)
    cat.perfil = "SISMO"   # perfil nuevo registrado en runtime
    assert crear(f, cat).plazo_horas == 2


# ----------------------------------------------------------------- Adapter
def test_adaptadores_cumplen_el_mismo_puerto():
    for proveedor in ("osm", "carto", "desconocido"):
        assert isinstance(crear_servicio_geografico(proveedor), ServicioGeografico)
    assert "openstreetmap" in AdaptadorOpenStreetMap().configuracion().url_teselas
    assert "cartocdn" in AdaptadorCartoClaro().configuracion().url_teselas


def test_adaptador_zona_y_cobertura():
    g = AdaptadorOpenStreetMap()
    assert g.zona_para(-17.3745, -66.3140) == "Zona Norte"
    assert g.zona_para(-17.3985, -66.3140) == "Zona Sur"
    assert g.coordenadas_validas(-17.3865, -66.3140)
    assert not g.coordenadas_validas(-12.0, -77.0)      # Lima


def test_adaptador_crea_marcador_con_color_por_estado(mundo):
    i = mundo.nuevo()
    m = mundo.geo.crear_marcador(i)
    assert (m.latitud, m.codigo, m.estado) == (i.ubicacion.latitud, i.codigo, "REPORTADO")
    assert m.color.startswith("#")


# -------------------------------------------------------- almacenamiento / hash
def test_almacen_acepta_png_jpg_y_rechaza_otros(tmp_path):
    a = AlmacenamientoLocal(tmp_path)
    assert a.guardar("f.png", PNG).endswith(".png")
    assert a.guardar("f.jpg", JPG).endswith(".jpg")
    with pytest.raises(EvidenciaInvalidaError):
        a.guardar("virus.png", b"MZ\x90\x00 no es imagen")       # extensión engañosa
    with pytest.raises(EvidenciaInvalidaError):
        a.guardar("vacio.png", b"")
    with pytest.raises(EvidenciaInvalidaError):
        a.guardar("grande.png", PNG + b"0" * (5 * 1024 * 1024))
    assert a.url_publica("x.png") == "/evidencias/x.png"


def test_hasher_pbkdf2():
    h = HasheadorPBKDF2(iteraciones=1000)
    hs = h.hashear("Vinto2026")
    assert hs != "Vinto2026" and h.verificar("Vinto2026", hs)
    assert not h.verificar("otra", hs) and not h.verificar("x", "basura")
    assert h.hashear("a") != h.hashear("a")      # sal distinta
