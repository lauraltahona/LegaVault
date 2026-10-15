"""Esquemas de expediente (Módulo 2)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import EstadoExpediente, TipoProceso


class ExpedienteCreate(BaseModel):
    identificador: str = Field(..., max_length=60)
    asunto: str = Field(..., max_length=200)
    cliente: str = Field(..., max_length=200)
    tipo_proceso: TipoProceso = TipoProceso.OTRO
    estado: EstadoExpediente = EstadoExpediente.ABIERTO
    abogado_responsable_id: str | None = None
    descripcion: str = ""
    usuarios_autorizados: list[str] = Field(default_factory=list)


class ExpedienteUpdate(BaseModel):
    identificador: str | None = None
    asunto: str | None = None
    cliente: str | None = None
    tipo_proceso: TipoProceso | None = None
    estado: EstadoExpediente | None = None
    abogado_responsable_id: str | None = None
    descripcion: str | None = None
    usuarios_autorizados: list[str] | None = None


class PermisosUpdate(BaseModel):
    """Matriz granular ``{usuario_id: {accion: bool}}`` (Módulo 5)."""

    permisos: dict[str, dict[str, bool]] = Field(default_factory=dict)


class ExpedienteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    identificador: str
    asunto: str
    cliente: str
    tipo_proceso: TipoProceso
    estado: EstadoExpediente
    abogado_responsable_id: str
    descripcion: str
    usuarios_autorizados: list[str]
    permisos: dict[str, dict[str, bool]] = Field(default_factory=dict)
    creado_en: datetime
    actualizado_en: datetime

    # Campos enriquecidos que se completan en el controlador.
    abogado_responsable_nombre: str | None = None
    total_documentos: int | None = None
