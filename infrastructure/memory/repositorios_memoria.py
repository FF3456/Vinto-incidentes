"""Adaptadores en memoria de los puertos de persistencia.

Permiten probar los casos de uso sin base de datos (consecuencia directa de DIP).
"""
from __future__ import annotations

import copy
from datetime import datetime, time, timedelta

from domain.entities.categoria import Categoria
from domain.entities.incidente import IncidenteAmbiental
from domain.entities.responsable import Responsable
from domain.entities.usuario import Usuario
from domain.ports.repositorios import (
    FiltroIncidentes, IRepositorioAuditoria, IRepositorioCategorias, IRepositorioIncidentes,
    IRepositorioResponsables, IRepositorioUsuarios, RegistroAuditoria)


class _Base:
    def __init__(self) -> None:
        self._datos: dict[int, object] = {}
        self._sig = 1

    def _guardar(self, obj):
        if obj.id is None:
            obj.id = self._sig
            self._sig += 1
        self._datos[obj.id] = copy.deepcopy(obj)
        return copy.deepcopy(obj)

    def _obtener(self, id_):
        v = self._datos.get(id_)
        return copy.deepcopy(v) if v else None


class RepositorioIncidentesMemoria(_Base, IRepositorioIncidentes):
    def guardar(self, incidente: IncidenteAmbiental) -> IncidenteAmbiental:
        return self._guardar(incidente)

    def buscar_por_id(self, incidente_id: int):
        return self._obtener(incidente_id)

    def buscar_por_codigo(self, codigo: str):
        return next((copy.deepcopy(i) for i in self._datos.values() if i.codigo == codigo), None)

    def listar(self, f: FiltroIncidentes | None = None) -> list[IncidenteAmbiental]:
        f = f or FiltroIncidentes()

        def ok(i: IncidenteAmbiental) -> bool:
            if f.categoria_id and i.categoria_id != f.categoria_id:
                return False
            if f.estado and i.estado != f.estado:
                return False
            if f.zona and i.ubicacion.zona != f.zona:
                return False
            if f.desde and i.fecha_reporte < datetime.combine(f.desde, time.min):
                return False
            if f.hasta and i.fecha_reporte >= datetime.combine(f.hasta, time.min) + timedelta(days=1):
                return False
            if f.responsable_id and i.responsable_id != f.responsable_id:
                return False
            if f.reportante_id and i.reportante_id != f.reportante_id:
                return False
            if f.texto:
                t = f.texto.strip().lower()
                if t not in f"{i.codigo} {i.titulo} {i.ubicacion.referencia} {i.descripcion}".lower():
                    return False
            return True

        res = [copy.deepcopy(i) for i in self._datos.values() if ok(i)]
        return sorted(res, key=lambda i: (i.fecha_reporte, i.id), reverse=True)

    def contar_del_anio(self, anio: int) -> int:
        return sum(1 for i in self._datos.values() if i.fecha_reporte.year == anio)


class RepositorioUsuariosMemoria(_Base, IRepositorioUsuarios):
    def guardar(self, usuario: Usuario) -> Usuario:
        return self._guardar(usuario)

    def buscar_por_id(self, usuario_id: int):
        return self._obtener(usuario_id)

    def buscar_por_correo(self, correo: str):
        return next((copy.deepcopy(u) for u in self._datos.values() if u.correo == correo), None)

    def listar(self) -> list[Usuario]:
        return [copy.deepcopy(u) for u in self._datos.values()]


class RepositorioCategoriasMemoria(_Base, IRepositorioCategorias):
    def guardar(self, categoria: Categoria) -> Categoria:
        return self._guardar(categoria)

    def buscar_por_id(self, categoria_id: int):
        return self._obtener(categoria_id)

    def buscar_por_nombre(self, nombre: str):
        return next((copy.deepcopy(c) for c in self._datos.values()
                     if c.nombre.lower() == nombre.lower()), None)

    def listar(self, solo_activas: bool = False) -> list[Categoria]:
        return [copy.deepcopy(c) for c in self._datos.values() if c.activa or not solo_activas]


class RepositorioResponsablesMemoria(_Base, IRepositorioResponsables):
    def guardar(self, responsable: Responsable) -> Responsable:
        return self._guardar(responsable)

    def buscar_por_id(self, responsable_id: int):
        return self._obtener(responsable_id)

    def buscar_por_usuario(self, usuario_id: int):
        return next((copy.deepcopy(r) for r in self._datos.values() if r.usuario_id == usuario_id), None)

    def listar(self, solo_activos: bool = False) -> list[Responsable]:
        return [copy.deepcopy(r) for r in self._datos.values() if r.activo or not solo_activos]


class RepositorioAuditoriaMemoria(IRepositorioAuditoria):
    def __init__(self) -> None:
        self.registros: list[RegistroAuditoria] = []

    def registrar(self, registro: RegistroAuditoria) -> None:
        self.registros.append(registro)

    def listar(self, limite: int = 500) -> list[RegistroAuditoria]:
        return list(reversed(self.registros))[:limite]
