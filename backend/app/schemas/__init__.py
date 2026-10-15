"""Contratos de entrada/salida de la API (Pydantic).

Representan la "vista" serializable del modelo: definen qué se acepta del
cliente y qué se devuelve, evitando filtrar campos internos como el hash de
la contraseña.
"""

from app.schemas.alerta_schema import AlertaResumen, AlertaResponse, MarcarLeidaRequest
from app.schemas.auditoria_schema import (
    AuditoriaResumen,
    AuditoriaVerificacion,
    RegistroAuditoriaResponse,
)
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.schemas.boveda_schema import (
    BovedaCreate,
    BovedaResponse,
    ContenidoResponse,
    CredencialesRequest,
    DesbloqueoRequest,
    EntradaCreate,
    EntradaResponse,
)
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
    "AuditoriaResumen",
    "AuditoriaVerificacion",
    "BovedaCreate",
    "BovedaResponse",
    "ContenidoResponse",
    "CredencialesRequest",
    "DesbloqueoRequest",
    "DocumentoResponse",
    "EntradaCreate",
    "EntradaResponse",
    "ExpedienteCreate",
    "ExpedienteResponse",
    "ExpedienteUpdate",
    "LoginRequest",
    "MarcarLeidaRequest",
    "PasswordResetRequest",
    "RegistroAuditoriaResponse",
    "TokenResponse",
    "UserCreate",
    "UserEstadoRequest",
    "UserResponse",
    "UserUpdate",
    "UsuarioResumen",
]
