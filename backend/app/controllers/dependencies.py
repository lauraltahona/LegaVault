"""Dependencias reutilizables de FastAPI (autenticación y autorización).

La verificación de identidad y rol se hace siempre en el servidor.
"""

from __future__ import annotations

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.constants import Rol
from app.core.container import auth_service
from app.core.exceptions import AuthenticationError, PermissionDeniedError
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


def obtener_ip(request: Request) -> str:
    """IP de origen para el registro de eventos (no se usa para autorizar)."""

    return request.client.host if request.client else ""


def get_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> str:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Se requiere autenticación.")
    return credentials.credentials


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> User:
    if credentials is None or not credentials.credentials:
        raise AuthenticationError("Se requiere autenticación.")
    return auth_service().usuario_actual(credentials.credentials)


def require_roles(*roles: Rol):
    """Genera una dependencia que exige uno de los roles indicados."""

    def _dependency(user: User = Depends(get_current_user)) -> User:
        if user.rol not in roles:
            raise PermissionDeniedError("Su rol no permite realizar esta acción.")
        return user

    return _dependency


require_admin = require_roles(Rol.ADMIN)
require_admin_or_abogado = require_roles(Rol.ADMIN, Rol.ABOGADO)
