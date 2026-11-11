"""Estados del ciclo de vida de un incidente (RF-06)."""
from __future__ import annotations

from enum import Enum


class EstadoIncidente(str, Enum):
    REPORTADO = "REPORTADO"
    EN_REVISION = "EN_REVISION"
    EN_ATENCION = "EN_ATENCION"
    ATENDIDO = "ATENDIDO"
    CERRADO = "CERRADO"

    @property
    def etiqueta(self) -> str:
        return {
            "REPORTADO": "Reportado",
            "EN_REVISION": "En revisión",
            "EN_ATENCION": "En atención",
            "ATENDIDO": "Atendido",
            "CERRADO": "Cerrado",
        }[self.value]

    @property
    def siguiente(self) -> "EstadoIncidente | None":
        """Único estado al que puede transicionar (flujo lineal)."""
        return _FLUJO.get(self)

    def puede_pasar_a(self, destino: "EstadoIncidente") -> bool:
        return _FLUJO.get(self) == destino


_FLUJO: dict[EstadoIncidente, EstadoIncidente] = {
    EstadoIncidente.REPORTADO: EstadoIncidente.EN_REVISION,
    EstadoIncidente.EN_REVISION: EstadoIncidente.EN_ATENCION,
    EstadoIncidente.EN_ATENCION: EstadoIncidente.ATENDIDO,
    EstadoIncidente.ATENDIDO: EstadoIncidente.CERRADO,
}
