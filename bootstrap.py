"""Raíz de composición: único lugar donde se eligen las implementaciones concretas.

Aquí se "cablean" puertos y adaptadores. Cambiar SQLite por PostgreSQL, o
OpenStreetMap por otro proveedor, solo requiere modificar este archivo (DIP).
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from application.auditor import Auditor
from application.use_cases.auditoria import ConsultarAuditoria
from application.use_cases.categorias import GestionarCategorias, ListarCategorias
from application.use_cases.consultas import (
    ConsultarPorCodigo, IncidentesAsignados, ListarIncidentes, MisReportes, ObtenerMarcadoresMapa)
from application.use_cases.estadisticas import ObtenerEstadisticas
from application.use_cases.incidentes import (
    AsignarResponsable, CambiarEstado, RegistrarAtencion, RegistrarIncidente)
from application.use_cases.usuarios import (
    Autenticar, GestionarUsuarios, ListarResponsables, RegistrarCiudadano)
from domain.factories.incidente_factory import IncidenteFactory
from domain.ports.repositorios import (
    IRepositorioAuditoria, IRepositorioCategorias, IRepositorioIncidentes,
    IRepositorioResponsables, IRepositorioUsuarios)
from domain.ports.servicio_geografico import ServicioGeografico
from domain.ports.servicios import AlmacenamientoEvidencias, HasheadorPassword
from infrastructure.database.repositorios_sqlalchemy import (
    RepositorioAuditoriaSQL, RepositorioCategoriasSQL, RepositorioIncidentesSQL,
    RepositorioResponsablesSQL, RepositorioUsuariosSQL)
from infrastructure.database.seed import sembrar_base, sembrar_incidentes_demo
from infrastructure.database.session import crear_fabrica_sesiones, crear_motor, crear_tablas
from infrastructure.maps.adaptadores import crear_servicio_geografico
from infrastructure.security.hasher import HasheadorPBKDF2
from infrastructure.storage.almacenamiento_local import AlmacenamientoLocal

RAIZ = Path(__file__).resolve().parent


@dataclass
class Contenedor:
    """Agrupa los casos de uso ya cableados con sus dependencias."""
    # puertos
    incidentes: IRepositorioIncidentes
    categorias: IRepositorioCategorias
    usuarios: IRepositorioUsuarios
    responsables: IRepositorioResponsables
    auditoria: IRepositorioAuditoria
    geo: ServicioGeografico
    almacen: AlmacenamientoEvidencias
    hasher: HasheadorPassword
    factory: IncidenteFactory
    # casos de uso
    registrar_incidente: RegistrarIncidente
    cambiar_estado: CambiarEstado
    asignar_responsable: AsignarResponsable
    registrar_atencion: RegistrarAtencion
    listar_incidentes: ListarIncidentes
    consultar_por_codigo: ConsultarPorCodigo
    mis_reportes: MisReportes
    incidentes_asignados: IncidentesAsignados
    marcadores_mapa: ObtenerMarcadoresMapa
    estadisticas: ObtenerEstadisticas
    autenticar: Autenticar
    registrar_ciudadano: RegistrarCiudadano
    gestionar_usuarios: GestionarUsuarios
    listar_responsables: ListarResponsables
    listar_categorias: ListarCategorias
    gestionar_categorias: GestionarCategorias
    consultar_auditoria: ConsultarAuditoria
    carpeta_evidencias: Path


def construir_contenedor(url_bd: str | None = None, carpeta_evidencias: str | Path | None = None,
                         proveedor_mapa: str | None = None, demo: bool | None = None) -> Contenedor:
    url_bd = url_bd or os.getenv("VINTO_DB", f"sqlite:///{RAIZ / 'data' / 'vinto.db'}")
    carpeta = Path(carpeta_evidencias or os.getenv("VINTO_EVIDENCIAS", RAIZ / "data" / "evidencias"))
    proveedor_mapa = proveedor_mapa or os.getenv("VINTO_MAPA", "osm")
    demo = (os.getenv("VINTO_DEMO", "1") == "1") if demo is None else demo
    if url_bd.startswith("sqlite:///") and ":memory:" not in url_bd:
        Path(url_bd.replace("sqlite:///", "")).parent.mkdir(parents=True, exist_ok=True)

    engine = crear_motor(url_bd)
    crear_tablas(engine)
    fabrica = crear_fabrica_sesiones(engine)

    incidentes = RepositorioIncidentesSQL(fabrica)
    categorias = RepositorioCategoriasSQL(fabrica)
    usuarios = RepositorioUsuariosSQL(fabrica)
    responsables = RepositorioResponsablesSQL(fabrica)
    auditoria = RepositorioAuditoriaSQL(fabrica)
    geo = crear_servicio_geografico(proveedor_mapa)
    almacen = AlmacenamientoLocal(carpeta)
    hasher = HasheadorPBKDF2()
    factory = IncidenteFactory()
    reloj = datetime.now
    auditor = Auditor(auditoria, reloj)

    sembrar_base(categorias, usuarios, responsables, hasher, con_cuentas_demo=demo)
    if demo:
        sembrar_incidentes_demo(incidentes, categorias, usuarios, responsables, geo, factory)

    return Contenedor(
        incidentes, categorias, usuarios, responsables, auditoria, geo, almacen, hasher, factory,
        registrar_incidente=RegistrarIncidente(incidentes, categorias, factory, geo, almacen, auditor, reloj),
        cambiar_estado=CambiarEstado(incidentes, auditor, reloj),
        asignar_responsable=AsignarResponsable(incidentes, responsables, auditor, reloj),
        registrar_atencion=RegistrarAtencion(incidentes, responsables, almacen, auditor, reloj),
        listar_incidentes=ListarIncidentes(incidentes),
        consultar_por_codigo=ConsultarPorCodigo(incidentes),
        mis_reportes=MisReportes(incidentes),
        incidentes_asignados=IncidentesAsignados(incidentes, responsables),
        marcadores_mapa=ObtenerMarcadoresMapa(incidentes, responsables, geo),
        estadisticas=ObtenerEstadisticas(incidentes, reloj),
        autenticar=Autenticar(usuarios, hasher, auditor),
        registrar_ciudadano=RegistrarCiudadano(usuarios, hasher, auditor),
        gestionar_usuarios=GestionarUsuarios(usuarios, responsables, hasher, auditor),
        listar_responsables=ListarResponsables(responsables),
        listar_categorias=ListarCategorias(categorias),
        gestionar_categorias=GestionarCategorias(categorias, auditor),
        consultar_auditoria=ConsultarAuditoria(auditoria),
        carpeta_evidencias=carpeta,
    )
