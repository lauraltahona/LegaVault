"""Esquemas de alertas de seguridad (Módulo 7)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import SeveridadAlerta, TipoAlerta


class AlertaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tipo: TipoAlerta
    severidad: SeveridadAlerta
    mensaje: str
    usuario: str
    usuario_id: str
    ip: str
    leida: bool
    creado_en: datetime


class AlertaResumen(BaseModel):
    total: int
    no_leidas: int
    por_severidad: dict[str, int]
    por_tipo: dict[str, int]


class MarcarLeidaRequest(BaseModel):
    leida: bool = True
