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


class VerificacionIntegridadResponse(BaseModel):
    """Resultado de re-verificar el SHA-256 del archivo en disco (Módulo 3)."""

    documento_id: str
    integro: bool
    checksum_esperado: str
    checksum_calculado: str
    tamano_esperado: int
    tamano_calculado: int
    verificado_en: datetime
    mensaje: str
