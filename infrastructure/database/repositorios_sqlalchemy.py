"""Adaptadores de persistencia: implementan los puertos del dominio con SQLAlchemy."""
from __future__ import annotations

from datetime import datetime, time, timedelta

from sqlalchemy import extract, func, or_, select
from sqlalchemy.orm import Session, sessionmaker

from domain.entities.categoria import Categoria
from domain.entities.incidente import IncidenteAmbiental, RegistroHistorial
from domain.entities.responsable import Responsable
from domain.entities.usuario import Usuario
from domain.ports.repositorios import (
    FiltroIncidentes, IRepositorioAuditoria, IRepositorioCategorias, IRepositorioIncidentes,
    IRepositorioResponsables, IRepositorioUsuarios, RegistroAuditoria)
from domain.value_objects.estado import EstadoIncidente
from domain.value_objects.evidencia import Evidencia
from domain.value_objects.prioridad import Prioridad
from domain.value_objects.rol import Rol
from domain.value_objects.ubicacion import Ubicacion
from infrastructure.database.models import (
    AuditoriaModel, CategoriaModel, EvidenciaModel, HistorialEstadoModel, IncidenteModel,
    ResponsableModel, UsuarioModel)

Fabrica = sessionmaker[Session]


# ----------------------------------------------------------------- mapeadores
def _usuario(m: UsuarioModel) -> Usuario:
    return Usuario(m.nombre, m.correo, m.password_hash, Rol(m.rol), m.activo, m.id)


def _categoria(m: CategoriaModel) -> Categoria:
    return Categoria(m.nombre, m.descripcion, m.perfil, m.activa, m.id)


def _responsable(m: ResponsableModel) -> Responsable:
    return Responsable(m.nombre, m.unidad, m.contacto, m.activo, m.usuario_id, m.id)


def _incidente(m: IncidenteModel) -> IncidenteAmbiental:
    return IncidenteAmbiental(
        id=m.id, codigo=m.codigo, titulo=m.titulo, descripcion=m.descripcion,
        categoria_id=m.categoria_id, categoria_nombre=m.categoria.nombre,
        fecha_incidente=m.fecha_incidente, fecha_reporte=m.fecha_reporte,
        ubicacion=Ubicacion(m.latitud, m.longitud, m.referencia, m.zona),
        prioridad=Prioridad(m.prioridad), plazo_horas=m.plazo_horas,
        estado=EstadoIncidente(m.estado), reportante_id=m.usuario_id,
        contacto_nombre=m.contacto_nombre, contacto_medio=m.contacto_medio,
        responsable_id=m.responsable_id,
        responsable_nombre=m.responsable.nombre if m.responsable else "",
        resumen_atencion=m.resumen_atencion, fecha_actualizacion=m.fecha_actualizacion,
        evidencias=[Evidencia(e.ruta_archivo, e.fecha_carga, e.tipo) for e in m.evidencias],
        historial=[RegistroHistorial(
            EstadoIncidente(h.estado_anterior) if h.estado_anterior else None,
            EstadoIncidente(h.estado_nuevo), h.fecha, h.usuario_nombre, h.observacion, h.usuario_id)
            for h in m.historial])


# --------------------------------------------------------------- repositorios
class RepositorioIncidentesSQL(IRepositorioIncidentes):
    def __init__(self, fabrica: Fabrica) -> None:
        self._fabrica = fabrica

    def guardar(self, i: IncidenteAmbiental) -> IncidenteAmbiental:
        with self._fabrica.begin() as s:
            m = s.get(IncidenteModel, i.id) if i.id else IncidenteModel()
            m.codigo, m.titulo, m.descripcion = i.codigo, i.titulo, i.descripcion
            m.categoria_id = i.categoria_id
            m.fecha_incidente, m.fecha_reporte = i.fecha_incidente, i.fecha_reporte
            m.fecha_actualizacion = i.fecha_actualizacion or i.fecha_reporte
            m.latitud, m.longitud = i.ubicacion.latitud, i.ubicacion.longitud
            m.referencia, m.zona = i.ubicacion.referencia, i.ubicacion.zona
            m.prioridad, m.plazo_horas, m.estado = i.prioridad.value, i.plazo_horas, i.estado.value
            m.usuario_id, m.responsable_id = i.reportante_id, i.responsable_id
            m.contacto_nombre, m.contacto_medio = i.contacto_nombre, i.contacto_medio
            m.resumen_atencion = i.resumen_atencion
            if not i.id:
                s.add(m)
            # Las colecciones son append-only: solo se agregan las filas nuevas.
            for ev in i.evidencias[len(m.evidencias):]:
                m.evidencias.append(EvidenciaModel(
                    ruta_archivo=ev.ruta_archivo, fecha_carga=ev.fecha_carga, tipo=ev.tipo))
            for h in i.historial[len(m.historial):]:
                m.historial.append(HistorialEstadoModel(
                    estado_anterior=h.estado_anterior.value if h.estado_anterior else None,
                    estado_nuevo=h.estado_nuevo.value, fecha=h.fecha, usuario_id=h.usuario_id,
                    usuario_nombre=h.usuario_nombre, observacion=h.observacion))
            s.flush()
            s.refresh(m)
            return _incidente(m)

    def buscar_por_id(self, incidente_id: int) -> IncidenteAmbiental | None:
        with self._fabrica() as s:
            m = s.get(IncidenteModel, incidente_id)
            return _incidente(m) if m else None

    def buscar_por_codigo(self, codigo: str) -> IncidenteAmbiental | None:
        with self._fabrica() as s:
            m = s.scalars(select(IncidenteModel).where(IncidenteModel.codigo == codigo)).first()
            return _incidente(m) if m else None

    def listar(self, f: FiltroIncidentes | None = None) -> list[IncidenteAmbiental]:
        f = f or FiltroIncidentes()
        q = select(IncidenteModel)
        if f.categoria_id:
            q = q.where(IncidenteModel.categoria_id == f.categoria_id)
        if f.estado:
            q = q.where(IncidenteModel.estado == f.estado.value)
        if f.zona:
            q = q.where(IncidenteModel.zona == f.zona)
        if f.desde:
            q = q.where(IncidenteModel.fecha_reporte >= datetime.combine(f.desde, time.min))
        if f.hasta:
            q = q.where(IncidenteModel.fecha_reporte < datetime.combine(f.hasta, time.min) + timedelta(days=1))
        if f.responsable_id:
            q = q.where(IncidenteModel.responsable_id == f.responsable_id)
        if f.reportante_id:
            q = q.where(IncidenteModel.usuario_id == f.reportante_id)
        if f.texto:
            patron = f"%{f.texto.strip()}%"
            q = q.where(or_(IncidenteModel.codigo.ilike(patron), IncidenteModel.titulo.ilike(patron),
                            IncidenteModel.referencia.ilike(patron),
                            IncidenteModel.descripcion.ilike(patron)))
        q = q.order_by(IncidenteModel.fecha_reporte.desc(), IncidenteModel.id.desc())
        with self._fabrica() as s:
            return [_incidente(m) for m in s.scalars(q).unique()]

    def contar_del_anio(self, anio: int) -> int:
        with self._fabrica() as s:
            return s.scalar(select(func.count(IncidenteModel.id)).where(
                extract("year", IncidenteModel.fecha_reporte) == anio)) or 0


class RepositorioUsuariosSQL(IRepositorioUsuarios):
    def __init__(self, fabrica: Fabrica) -> None:
        self._fabrica = fabrica

    def guardar(self, u: Usuario) -> Usuario:
        with self._fabrica.begin() as s:
            m = s.get(UsuarioModel, u.id) if u.id else UsuarioModel()
            m.nombre, m.correo, m.password_hash = u.nombre, u.correo, u.password_hash
            m.rol, m.activo = u.rol.value, u.activo
            if not u.id:
                s.add(m)
            s.flush()
            return _usuario(m)

    def buscar_por_id(self, usuario_id: int) -> Usuario | None:
        with self._fabrica() as s:
            m = s.get(UsuarioModel, usuario_id)
            return _usuario(m) if m else None

    def buscar_por_correo(self, correo: str) -> Usuario | None:
        with self._fabrica() as s:
            m = s.scalars(select(UsuarioModel).where(UsuarioModel.correo == correo)).first()
            return _usuario(m) if m else None

    def listar(self) -> list[Usuario]:
        with self._fabrica() as s:
            return [_usuario(m) for m in s.scalars(select(UsuarioModel).order_by(UsuarioModel.id))]


class RepositorioCategoriasSQL(IRepositorioCategorias):
    def __init__(self, fabrica: Fabrica) -> None:
        self._fabrica = fabrica

    def guardar(self, c: Categoria) -> Categoria:
        with self._fabrica.begin() as s:
            m = s.get(CategoriaModel, c.id) if c.id else CategoriaModel()
            m.nombre, m.descripcion, m.perfil, m.activa = c.nombre, c.descripcion, c.perfil, c.activa
            if not c.id:
                s.add(m)
            s.flush()
            return _categoria(m)

    def buscar_por_id(self, categoria_id: int) -> Categoria | None:
        with self._fabrica() as s:
            m = s.get(CategoriaModel, categoria_id)
            return _categoria(m) if m else None

    def buscar_por_nombre(self, nombre: str) -> Categoria | None:
        with self._fabrica() as s:
            m = s.scalars(select(CategoriaModel).where(
                func.lower(CategoriaModel.nombre) == nombre.lower())).first()
            return _categoria(m) if m else None

    def listar(self, solo_activas: bool = False) -> list[Categoria]:
        q = select(CategoriaModel).order_by(CategoriaModel.id)
        if solo_activas:
            q = q.where(CategoriaModel.activa.is_(True))
        with self._fabrica() as s:
            return [_categoria(m) for m in s.scalars(q)]


class RepositorioResponsablesSQL(IRepositorioResponsables):
    def __init__(self, fabrica: Fabrica) -> None:
        self._fabrica = fabrica

    def guardar(self, r: Responsable) -> Responsable:
        with self._fabrica.begin() as s:
            m = s.get(ResponsableModel, r.id) if r.id else ResponsableModel()
            m.nombre, m.unidad, m.contacto = r.nombre, r.unidad, r.contacto
            m.activo, m.usuario_id = r.activo, r.usuario_id
            if not r.id:
                s.add(m)
            s.flush()
            return _responsable(m)

    def buscar_por_id(self, responsable_id: int) -> Responsable | None:
        with self._fabrica() as s:
            m = s.get(ResponsableModel, responsable_id)
            return _responsable(m) if m else None

    def buscar_por_usuario(self, usuario_id: int) -> Responsable | None:
        with self._fabrica() as s:
            m = s.scalars(select(ResponsableModel).where(ResponsableModel.usuario_id == usuario_id)).first()
            return _responsable(m) if m else None

    def listar(self, solo_activos: bool = False) -> list[Responsable]:
        q = select(ResponsableModel).order_by(ResponsableModel.id)
        if solo_activos:
            q = q.where(ResponsableModel.activo.is_(True))
        with self._fabrica() as s:
            return [_responsable(m) for m in s.scalars(q)]


class RepositorioAuditoriaSQL(IRepositorioAuditoria):
    def __init__(self, fabrica: Fabrica) -> None:
        self._fabrica = fabrica

    def registrar(self, r: RegistroAuditoria) -> None:
        with self._fabrica.begin() as s:
            s.add(AuditoriaModel(fecha=r.fecha, usuario_nombre=r.usuario_nombre,
                                 accion=r.accion, recurso=r.recurso, detalle=r.detalle))

    def listar(self, limite: int = 500) -> list[RegistroAuditoria]:
        q = select(AuditoriaModel).order_by(AuditoriaModel.fecha.desc(), AuditoriaModel.id.desc()).limit(limite)
        with self._fabrica() as s:
            return [RegistroAuditoria(m.fecha, m.usuario_nombre, m.accion, m.recurso, m.detalle, m.id)
                    for m in s.scalars(q)]
