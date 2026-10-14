"""Esquemas de documento (Módulo 3)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import NivelSensibilidad, TipoDocumento


class DocumentoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre_original: str
    expediente_id: str
    tipo: TipoDocumento
    nivel_sensibilidad: NivelSensibilidad
    descripcion: str
    tamano_bytes: int
    checksum_sha256: str
    subido_por_id: str
    creado_en: datetime
    actualizado_en: datetime
