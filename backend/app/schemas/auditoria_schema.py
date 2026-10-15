"""Esquemas de auditoría (Módulo 6)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import AccionAuditoria, ResultadoAuditoria


class RegistroAuditoriaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    accion: AccionAuditoria
    resultado: ResultadoAuditoria
    entidad: str
    entidad_id: str
    usuario: str
    usuario_id: str
    rol: str
    detalle: str
    ip: str
    creado_en: datetime
    hash_anterior: str
    hash_actual: str


class AuditoriaVerificacion(BaseModel):
    integro: bool
    total: int
    indice_roto: int | None = None
    verificado_en: str


class AuditoriaResumen(BaseModel):
    total: int
    por_resultado: dict[str, int]
    por_accion: dict[str, int]
