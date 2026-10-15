"""Esquemas de la bóveda cifrada de doble fondo (Módulo 4).

Importante: **ningún esquema de salida expone las vistas cifradas** ni
cualquier material criptográfico. La metainformación visible es solo la
necesaria para listar y describir la bóveda en la interfaz.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BovedaCreate(BaseModel):
    """Datos para crear una bóveda con sus dos contraseñas independientes."""

    nombre: str = Field(..., max_length=120)
    descripcion: str = ""
    expediente_id: str = ""
    password_visible: str = Field(..., min_length=1)
    password_confidencial: str = Field(..., min_length=1)
    contenido_visible: str = ""
    contenido_confidencial: str = ""


class BovedaResponse(BaseModel):
    """Metadatos de una bóveda (nunca el contenido ni las vistas cifradas)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    descripcion: str
    expediente_id: str
    creado_por_id: str
    activo: bool
    creado_en: datetime
    actualizado_en: datetime

    # Campo enriquecido que se completa en el controlador.
    expediente_identificador: str | None = None


class DesbloqueoRequest(BaseModel):
    password: str = Field(..., min_length=1)


class EntradaResponse(BaseModel):
    id: str
    titulo: str
    contenido: str
    creado_en: str


class ContenidoResponse(BaseModel):
    """Contenido descifrado de una vista (solo tras desbloquear)."""

    entradas: list[EntradaResponse] = Field(default_factory=list)


class EntradaCreate(BaseModel):
    titulo: str = Field(..., max_length=200)
    contenido: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CredencialesRequest(BaseModel):
    password_actual: str = Field(..., min_length=1)
    password_nueva: str = Field(..., min_length=1)
