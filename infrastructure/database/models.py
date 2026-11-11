"""Modelos ORM (SQLAlchemy 2.0). Solo existen en infraestructura: el dominio no los conoce."""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UsuarioModel(Base):
    __tablename__ = "usuario"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    correo: Mapped[str] = mapped_column(String(160), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    rol: Mapped[str] = mapped_column(String(20))
    activo: Mapped[bool] = mapped_column(Boolean, default=True)


class CategoriaModel(Base):
    __tablename__ = "categoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), unique=True)
    descripcion: Mapped[str] = mapped_column(Text, default="")
    perfil: Mapped[str] = mapped_column(String(20), default="GENERICO")
    activa: Mapped[bool] = mapped_column(Boolean, default=True)


class ResponsableModel(Base):
    __tablename__ = "responsable"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120))
    unidad: Mapped[str] = mapped_column(String(120), default="")
    contacto: Mapped[str] = mapped_column(String(160), default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True)


class IncidenteModel(Base):
    __tablename__ = "incidente"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    codigo: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    titulo: Mapped[str] = mapped_column(String(200))
    descripcion: Mapped[str] = mapped_column(Text)
    categoria_id: Mapped[int] = mapped_column(ForeignKey("categoria.id"), index=True)
    fecha_incidente: Mapped[datetime] = mapped_column(DateTime)
    fecha_reporte: Mapped[datetime] = mapped_column(DateTime, index=True)
    fecha_actualizacion: Mapped[datetime] = mapped_column(DateTime)
    latitud: Mapped[float] = mapped_column(Float)
    longitud: Mapped[float] = mapped_column(Float)
    referencia: Mapped[str] = mapped_column(String(255), default="")
    zona: Mapped[str] = mapped_column(String(80), default="", index=True)
    prioridad: Mapped[str] = mapped_column(String(10))
    plazo_horas: Mapped[int] = mapped_column(Integer, default=72)
    estado: Mapped[str] = mapped_column(String(20), index=True)
    usuario_id: Mapped[int | None] = mapped_column(ForeignKey("usuario.id"), nullable=True, index=True)
    contacto_nombre: Mapped[str] = mapped_column(String(120), default="")
    contacto_medio: Mapped[str] = mapped_column(String(160), default="")
    responsable_id: Mapped[int | None] = mapped_column(ForeignKey("responsable.id"), nullable=True, index=True)
    resumen_atencion: Mapped[str] = mapped_column(Text, default="")

    categoria: Mapped[CategoriaModel] = relationship(lazy="joined")
    responsable: Mapped[ResponsableModel | None] = relationship(lazy="joined")
    evidencias: Mapped[list["EvidenciaModel"]] = relationship(
        back_populates="incidente", cascade="all, delete-orphan", order_by="EvidenciaModel.id",
        lazy="selectin")
    historial: Mapped[list["HistorialEstadoModel"]] = relationship(
        back_populates="incidente", cascade="all, delete-orphan", order_by="HistorialEstadoModel.id",
        lazy="selectin")


class EvidenciaModel(Base):
    __tablename__ = "evidencia"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incidente_id: Mapped[int] = mapped_column(ForeignKey("incidente.id"))
    ruta_archivo: Mapped[str] = mapped_column(String(255))
    fecha_carga: Mapped[datetime] = mapped_column(DateTime)
    tipo: Mapped[str] = mapped_column(String(10), default="REPORTE")
    incidente: Mapped[IncidenteModel] = relationship(back_populates="evidencias")


class HistorialEstadoModel(Base):
    __tablename__ = "historial_estado"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    incidente_id: Mapped[int] = mapped_column(ForeignKey("incidente.id"))
    estado_anterior: Mapped[str | None] = mapped_column(String(20), nullable=True)
    estado_nuevo: Mapped[str] = mapped_column(String(20))
    fecha: Mapped[datetime] = mapped_column(DateTime)
    usuario_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    usuario_nombre: Mapped[str] = mapped_column(String(120), default="")
    observacion: Mapped[str] = mapped_column(Text, default="")
    incidente: Mapped[IncidenteModel] = relationship(back_populates="historial")


class AuditoriaModel(Base):
    __tablename__ = "auditoria"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    fecha: Mapped[datetime] = mapped_column(DateTime, index=True)
    usuario_nombre: Mapped[str] = mapped_column(String(120))
    accion: Mapped[str] = mapped_column(String(60))
    recurso: Mapped[str] = mapped_column(String(160), default="")
    detalle: Mapped[str] = mapped_column(Text, default="")
