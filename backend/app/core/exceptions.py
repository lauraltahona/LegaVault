"""Excepciones de dominio.

Permiten que los servicios expresen reglas de negocio sin acoplarse a
FastAPI. La capa de controladores las traduce a respuestas HTTP mediante
un manejador global registrado en ``app.main``.
"""

from __future__ import annotations


class DomainError(Exception):
    """Error de negocio base."""

    status_code: int = 400

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ValidationError(DomainError):
    status_code = 422


class NotFoundError(DomainError):
    status_code = 404


class ConflictError(DomainError):
    status_code = 409


class AuthenticationError(DomainError):
    status_code = 401


class PermissionDeniedError(DomainError):
    status_code = 403


class AccountLockedError(DomainError):
    """Cuenta bloqueada temporalmente por intentos fallidos (Módulo 7)."""

    status_code = 423
