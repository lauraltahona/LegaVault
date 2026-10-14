"""Repositorios: acceso a datos sobre archivos JSON locales."""

from app.repositories.alerta_repository import AlertaRepository
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.user_repository import UserRepository

__all__ = [
    "AlertaRepository",
    "DocumentoRepository",
    "ExpedienteRepository",
    "UserRepository",
]
