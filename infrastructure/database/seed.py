"""Datos iniciales: catálogo, cuentas de demostración e incidentes de ejemplo.

Las cuentas y reportes de demostración son SOLO para pruebas y sustentación;
deben eliminarse (variable VINTO_DEMO=0) en una puesta en producción real.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from domain.entities.categoria import Categoria
from domain.entities.responsable import Responsable
from domain.entities.usuario import Usuario
from domain.factories.incidente_factory import IncidenteFactory
from domain.ports.repositorios import (
    IRepositorioCategorias, IRepositorioIncidentes, IRepositorioResponsables, IRepositorioUsuarios)
from domain.ports.servicio_geografico import ServicioGeografico
from domain.ports.servicios import HasheadorPassword
from domain.value_objects.estado import EstadoIncidente as E
from domain.value_objects.rol import Rol
from domain.value_objects.ubicacion import Ubicacion

CATEGORIAS = [
    ("Acumulación de basura", "Residuos sólidos acumulados en vía pública o terrenos.", "RESIDUOS"),
    ("Vertido ilegal", "Descarga clandestina de escombros, aceites o residuos.", "AGUA"),
    ("Quema de basura", "Quema de residuos a cielo abierto.", "AIRE"),
    ("Contaminación de ríos y canales", "Residuos o descargas en cuerpos de agua.", "AGUA"),
    ("Contaminación del aire", "Humo, polvo o emisiones que afectan el aire.", "AIRE"),
    ("Deterioro de áreas verdes", "Daño o abandono de parques, árboles y áreas verdes.", "AREAS_VERDES"),
    ("Aguas residuales", "Desbordes o descargas de aguas servidas.", "AGUA"),
    ("Contaminación acústica", "Ruido excesivo que afecta a los vecinos.", "RUIDO"),
    ("Afectación de animales", "Maltrato o riesgo sanitario relacionado con animales.", "GENERICO"),
]

PASS_DEMO = "Vinto2026"
USUARIOS = [  # nombre, correo, rol, unidad (solo responsables)
    ("Administrador SIRIMA", "admin@vinto.gob.bo", Rol.ADMINISTRADOR, ""),
    ("Lic. Patricia Quispe", "funcionario@vinto.gob.bo", Rol.FUNCIONARIO, ""),
    ("Ing. Carlos Mamani", "responsable@vinto.gob.bo", Rol.RESPONSABLE, "Cuadrilla de Residuos Sólidos"),
    ("Dra. Sofía Herbas", "responsable2@vinto.gob.bo", Rol.RESPONSABLE, "Unidad de Recursos Hídricos"),
    ("María Fernanda Rojas", "vecino@vinto.gob.bo", Rol.CIUDADANO, ""),
]


def sembrar_base(categorias: IRepositorioCategorias, usuarios: IRepositorioUsuarios,
                 responsables: IRepositorioResponsables, hasher: HasheadorPassword,
                 con_cuentas_demo: bool = True) -> None:
    """Idempotente: solo inserta lo que falta."""
    if not categorias.listar():
        for nombre, desc, perfil in CATEGORIAS:
            categorias.guardar(Categoria(nombre, desc, perfil))
    if con_cuentas_demo and not usuarios.listar():
        for nombre, correo, rol, unidad in USUARIOS:
            u = usuarios.guardar(Usuario(nombre, correo, hasher.hashear(PASS_DEMO), rol))
            if rol == Rol.RESPONSABLE:
                responsables.guardar(Responsable(nombre, unidad, correo, True, u.id))


def sembrar_incidentes_demo(incidentes: IRepositorioIncidentes, categorias: IRepositorioCategorias,
                            usuarios: IRepositorioUsuarios, responsables: IRepositorioResponsables,
                            geo: ServicioGeografico, factory: IncidenteFactory,
                            ahora: datetime | None = None) -> None:
    """Crea reportes de ejemplo repartidos en los últimos 5 meses y en todos los estados."""
    if incidentes.listar():
        return
    ahora = ahora or datetime.now()
    cats = {c.nombre: c for c in categorias.listar()}
    resps = responsables.listar()
    vecino = usuarios.buscar_por_correo("vecino@vinto.gob.bo")
    func = "Lic. Patricia Quispe"

    # (cat, título, descripción, lat, lon, referencia, días atrás, estado final, resp_idx, h_a_revision, h_a_atencion, h_a_atendido)
    casos = [
        ("Acumulación de basura", "Basura acumulada en esquina de la plaza",
         "Se observa una acumulación de bolsas y escombros que bloquea parte de la acera.",
         -17.3868, -66.3142, "Esquina Av. Bolivar y calle 1", 4, E.EN_ATENCION, 0, 3, 20, None),
        ("Contaminación de ríos y canales", "Residuos plásticos en el canal de riego",
         "El canal junto al camino presenta botellas, bolsas y restos de aceite sobre el agua.",
         -17.3742, -66.3135, "Canal de riego camino a Sipe Sipe", 3, E.EN_REVISION, None, 5, None, None),
        ("Quema de basura", "Quema de residuos en terreno baldío",
         "Vecinos reportan humo denso por la quema de basura en un terreno baldío desde la tarde.",
         -17.3808, -66.3265, "Calle 3 de Mayo, Barrio San Antonio", 1, E.REPORTADO, None, None, None, None),
        ("Vertido ilegal", "Descarga de escombros junto a la zona industrial",
         "Un camión descargó escombros y residuos líquidos al borde del camino industrial.",
         -17.3930, -66.2985, "Camino vecinal Zona Industrial", 12, E.ATENDIDO, 0, 4, 12, 70),
        ("Aguas residuales", "Desborde de aguas servidas en la calle",
         "Hay un desborde constante de aguas servidas que llega hasta la vereda de varias casas.",
         -17.3990, -66.3150, "Calle Los Pinos, Zona Sur", 20, E.CERRADO, 1, 2, 8, 30),
        ("Contaminación acústica", "Ruido excesivo de taller por las noches",
         "Un taller funciona hasta altas horas de la noche con maquinaria muy ruidosa.",
         -17.3860, -66.3125, "Av. Principal, frente al mercado", 35, E.CERRADO, 0, 10, 40, 100),
        ("Deterioro de áreas verdes", "Árboles secos en parque central",
         "Varios árboles del parque presentan ramas secas que representan riesgo para los niños.",
         -17.3870, -66.3150, "Parque Central de Vinto", 52, E.CERRADO, 0, 6, 30, 120),
        ("Acumulación de basura", "Basura en la ribera del camino rural",
         "Se acumula basura doméstica en la ribera del camino hacia la zona rural.",
         -17.4120, -66.3450, "Camino rural, sector Chilimarca", 70, E.ATENDIDO, 0, 5, 18, 60),
        ("Contaminación del aire", "Polvo y humo de ladrillera",
         "Una ladrillera emite humo negro constantemente, afectando a las viviendas cercanas.",
         -17.3938, -66.3005, "Ladrillera sobre camino industrial", 95, E.CERRADO, 1, 8, 25, 90),
        ("Vertido ilegal", "Aceite usado vertido en el desagüe",
         "Se descubrió aceite de motor vertido en el desagüe pluvial de la calle.",
         -17.3750, -66.3150, "Calle Junín, Zona Norte", 120, E.CERRADO, 1, 3, 10, 36),
        ("Acumulación de basura", "Contenedor desbordado en el mercado",
         "El contenedor del mercado lleva varios días sin recojo y la basura invade la calle.",
         -17.3855, -66.3135, "Mercado Central de Vinto", 140, E.CERRADO, 0, 4, 14, 40),
        ("Afectación de animales", "Animales muertos en acequia",
         "Se encontraron restos de animales en una acequia, con mal olor y riesgo sanitario.",
         -17.4090, -66.3410, "Acequia, Zona Rural", 2, E.EN_REVISION, None, 6, None, None),
    ]
    for (cat, titulo, desc, lat, lon, ref, dias, estado, ri, h_rev, h_ate, h_fin) in reversed(casos):  # cronológico
        reporte = ahora - timedelta(days=dias, hours=2)
        zona = geo.zona_para(lat, lon)
        i = factory.crear(
            categoria=cats[cat], codigo=f"VINTO-{reporte.year}-{incidentes.contar_del_anio(reporte.year) + 1:04d}",
            titulo=titulo, descripcion=desc, fecha_incidente=reporte - timedelta(hours=3),
            fecha_reporte=reporte, ubicacion=Ubicacion(lat, lon, ref, zona),
            reportante_id=vecino.id if vecino and dias % 2 == 0 else None,
            contacto_nombre="María Fernanda Rojas" if dias % 2 == 0 else "", contacto_medio="70000000")
        i.registrar_creacion("Ciudadano")
        if estado != E.REPORTADO:
            i.cambiar_estado(E.EN_REVISION, reporte + timedelta(hours=h_rev), func,
                             "Reporte verificado por la oficina")
        if ri is not None:
            r = resps[ri % len(resps)]
            i.asignar_responsable(r.id, r.nombre)
            i.cambiar_estado(E.EN_ATENCION, reporte + timedelta(hours=h_ate), func,
                             f"Asignado a {r.nombre}")
        if estado in (E.ATENDIDO, E.CERRADO):
            i.registrar_atencion("Se realizó la limpieza/intervención y se verificó el sitio.",
                                 reporte + timedelta(hours=h_fin), i.responsable_nombre)
        if estado == E.CERRADO:
            i.cambiar_estado(E.CERRADO, reporte + timedelta(hours=(h_fin or 0) + 24), func,
                             "Cierre verificado")
        i.fecha_actualizacion = i.historial[-1].fecha
        incidentes.guardar(i)
