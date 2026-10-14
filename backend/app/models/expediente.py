"""Modelo de expediente jurídico (Módulo 2)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants import EstadoExpediente, TipoProceso
from app.models.base import BaseEntity, decode_datetime


@dataclass
class Expediente(BaseEntity):
    identificador: str = ""
    asunto: str = ""
    cliente: str = ""
    tipo_proceso: TipoProceso = TipoProceso.OTRO
    estado: EstadoExpediente = EstadoExpediente.ABIERTO
    abogado_responsable_id: str = ""
    descripcion: str = ""
    # Usuarios (además del responsable) con acceso autorizado al expediente.
    usuarios_autorizados: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict) -> "Expediente":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            identificador=data.get("identificador", ""),
            asunto=data.get("asunto", ""),
            cliente=data.get("cliente", ""),
            tipo_proceso=TipoProceso(data.get("tipo_proceso", TipoProceso.OTRO.value)),
            estado=EstadoExpediente(data.get("estado", EstadoExpediente.ABIERTO.value)),
            abogado_responsable_id=data.get("abogado_responsable_id", ""),
            descripcion=data.get("descripcion", ""),
            usuarios_autorizados=list(data.get("usuarios_autorizados") or []),
        )
