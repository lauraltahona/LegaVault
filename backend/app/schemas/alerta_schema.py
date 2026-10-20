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
    # Vacío para las alertas nativas; identifica la regla de correlación que
    # generó la alerta (mejora #13).
    regla: str = ""


class ReglaCorrelacionResponse(BaseModel):
    """Descripción de una regla de correlación activa (educativa y consultable)."""

    id: str
    descripcion: str
    severidad: SeveridadAlerta
    umbral: int | None = None
    ventana_segundos: int | None = None
    tipos_vigilados: list[TipoAlerta]


class AlertaResumen(BaseModel):
    total: int
    no_leidas: int
    por_severidad: dict[str, int]
    por_tipo: dict[str, int]


class MarcarLeidaRequest(BaseModel):
    leida: bool = True
