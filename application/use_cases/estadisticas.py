"""RF-09: métricas del panel de control."""
from __future__ import annotations

from collections import Counter
from datetime import datetime
from typing import Callable

from application.dto import Estadisticas, ZonaCritica
from domain.policies.actor import Actor
from domain.policies.permisos import Permiso, exigir
from domain.ports.repositorios import IRepositorioIncidentes
from domain.value_objects.estado import EstadoIncidente as E

_MESES = ["Ene", "Feb", "Mar", "Abr", "May", "Jun", "Jul", "Ago", "Sep", "Oct", "Nov", "Dic"]
_ABIERTOS = (E.REPORTADO, E.EN_REVISION, E.EN_ATENCION)


def _media(valores: list[float]) -> float | None:
    return round(sum(valores) / len(valores), 1) if valores else None


class ObtenerEstadisticas:
    def __init__(self, incidentes: IRepositorioIncidentes,
                 reloj: Callable[[], datetime] = datetime.now) -> None:
        self._incidentes, self._reloj = incidentes, reloj

    def ejecutar(self, actor: Actor, meses: int = 6) -> Estadisticas:
        exigir(actor, Permiso.VER_ESTADISTICAS)
        todos = self._incidentes.listar()
        ahora = self._reloj()
        est = Estadisticas(total=len(todos))
        est.por_estado = {e.value: 0 for e in E} | dict(Counter(i.estado.value for i in todos))
        est.por_categoria = dict(Counter(i.categoria_nombre for i in todos).most_common())
        est.por_zona = dict(Counter(i.ubicacion.zona or "Sin zona" for i in todos).most_common())
        est.pendientes = est.por_estado[E.REPORTADO.value]
        est.en_proceso = est.por_estado[E.EN_REVISION.value] + est.por_estado[E.EN_ATENCION.value]
        est.resueltos = est.por_estado[E.ATENDIDO.value] + est.por_estado[E.CERRADO.value]
        est.tasa_resolucion = round(100 * est.resueltos / est.total, 1) if est.total else 0.0
        est.vencidos = sum(1 for i in todos if i.esta_vencido(ahora))

        # Tiempo medio de respuesta = reporte → primera atención en campo (EN_ATENCION)
        est.tiempo_medio_respuesta_h = _media(
            [h for i in todos if (h := i.horas_hasta(E.EN_ATENCION)) is not None])
        # Tiempo medio de resolución = reporte → ATENDIDO
        est.tiempo_medio_resolucion_h = _media(
            [h for i in todos if (h := i.horas_hasta(E.ATENDIDO)) is not None])

        # Zonas críticas: mayor número de casos abiertos (desempate por total histórico)
        abiertos = Counter(i.ubicacion.zona or "Sin zona" for i in todos if i.estado in _ABIERTOS)
        total_abiertos = sum(abiertos.values()) or 1
        ranking = sorted(est.por_zona, key=lambda z: (abiertos.get(z, 0), est.por_zona[z]),
                         reverse=True)
        est.zonas_criticas = [
            ZonaCritica(z, est.por_zona[z], abiertos.get(z, 0),
                        round(100 * abiertos.get(z, 0) / total_abiertos, 1))
            for z in ranking[:3] if abiertos.get(z, 0) > 0]

        # Tendencia mensual: reportados vs. atendidos (últimos N meses)
        y, m = ahora.year, ahora.month
        claves: list[tuple[int, int]] = []
        for k in range(meses - 1, -1, -1):
            mm = m - k
            yy = y
            while mm <= 0:
                mm += 12
                yy -= 1
            claves.append((yy, mm))
        rep = Counter((i.fecha_reporte.year, i.fecha_reporte.month) for i in todos)
        ate = Counter()
        for i in todos:
            f = i.fecha_de(E.ATENDIDO)
            if f:
                ate[(f.year, f.month)] += 1
        est.por_mes = [(_MESES[mm - 1], rep.get((yy, mm), 0), ate.get((yy, mm), 0))
                       for yy, mm in claves]
        return est
