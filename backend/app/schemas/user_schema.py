"""Esquemas de usuario (Módulo 1)."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.core.constants import Rol


class UserCreate(BaseModel):
    username: str
    nombre_completo: str
    email: str
    password: str
    rol: Rol = Rol.ABOGADO


class UserUpdate(BaseModel):
    nombre_completo: str | None = None
    email: str | None = None
    rol: Rol | None = None


class UserEstadoRequest(BaseModel):
    activo: bool


class PasswordResetRequest(BaseModel):
    nueva_password: str


class UsuarioResumen(BaseModel):
    """Vista reducida de usuario para selectores (mínimo privilegio)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    nombre_completo: str
    rol: Rol


class UserResponse(BaseModel):
    """Respuesta pública: nunca incluye ``password_hash``."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    nombre_completo: str
    email: str
    rol: Rol
    activo: bool
    intentos_fallidos: int
    bloqueado_hasta: datetime | None = None
    esta_bloqueado: bool = False
    ultimo_acceso: datetime | None = None
    creado_en: datetime
    actualizado_en: datetime
