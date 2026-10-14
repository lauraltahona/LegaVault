"""Contratos de entrada/salida de la API (Pydantic).

Representan la "vista" serializable del modelo: definen qué se acepta del
cliente y qué se devuelve, evitando filtrar campos internos como el hash de
la contraseña.
"""

from app.schemas.alerta_schema import AlertaResumen, AlertaResponse, MarcarLeidaRequest
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.schemas.documento_schema import DocumentoResponse
from app.schemas.expediente_schema import (
    ExpedienteCreate,
    ExpedienteResponse,
    ExpedienteUpdate,
)
from app.schemas.user_schema import (
    PasswordResetRequest,
    UserCreate,
    UserEstadoRequest,
    UserResponse,
    UserUpdate,
    UsuarioResumen,
)

__all__ = [
    "AlertaResumen",
    "AlertaResponse",
    "DocumentoResponse",
    "ExpedienteCreate",
    "ExpedienteResponse",
    "ExpedienteUpdate",
    "LoginRequest",
    "MarcarLeidaRequest",
    "PasswordResetRequest",
    "TokenResponse",
    "UserCreate",
    "UserEstadoRequest",
    "UserResponse",
    "UserUpdate",
    "UsuarioResumen",
]
