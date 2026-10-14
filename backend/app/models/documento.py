"""Modelo de documento asociado a un expediente (Módulo 3)."""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import NivelSensibilidad, TipoDocumento
from app.models.base import BaseEntity, decode_datetime


@dataclass
class Documento(BaseEntity):
    nombre_original: str = ""
    nombre_almacenado: str = ""
    expediente_id: str = ""
    tipo: TipoDocumento = TipoDocumento.OTRO
    nivel_sensibilidad: NivelSensibilidad = NivelSensibilidad.INTERNO
    descripcion: str = ""
    tamano_bytes: int = 0
    checksum_sha256: str = ""
    subido_por_id: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Documento":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            nombre_original=data.get("nombre_original", ""),
            nombre_almacenado=data.get("nombre_almacenado", ""),
            expediente_id=data.get("expediente_id", ""),
            tipo=TipoDocumento(data.get("tipo", TipoDocumento.OTRO.value)),
            nivel_sensibilidad=NivelSensibilidad(
                data.get("nivel_sensibilidad", NivelSensibilidad.INTERNO.value)
            ),
            descripcion=data.get("descripcion", ""),
            tamano_bytes=int(data.get("tamano_bytes", 0)),
            checksum_sha256=data.get("checksum_sha256", ""),
            subido_por_id=data.get("subido_por_id", ""),
        )
