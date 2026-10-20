"""Composición de dependencias (wiring).

Construye repositorios y servicios una sola vez (singletons) y los comparte
entre controladores. Centraliza aquí el cableado para que ninguna capa
conozca cómo se instancian las demás.
"""

from __future__ import annotations

from functools import lru_cache

from app.core.config import settings
from app.repositories.alerta_repository import AlertaRepository
from app.repositories.auditoria_repository import AuditoriaRepository
from app.repositories.boveda_repository import BovedaRepository
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.user_repository import UserRepository
from app.services.alerta_service import AlertaService
from app.services.auditoria_service import AuditoriaService
from app.services.auth_service import AuthService
from app.services.boveda_service import BovedaService
from app.services.correlacion_service import CorrelacionAlertasService
from app.services.documento_service import DocumentoService
from app.services.expediente_service import ExpedienteService
from app.services.user_service import UserService


# --- Repositorios --------------------------------------------------------
@lru_cache
def user_repository() -> UserRepository:
    return UserRepository(settings.data_dir / "usuarios.json")


@lru_cache
def expediente_repository() -> ExpedienteRepository:
    return ExpedienteRepository(settings.data_dir / "expedientes.json")


@lru_cache
def documento_repository() -> DocumentoRepository:
    return DocumentoRepository(settings.data_dir / "documentos.json")


@lru_cache
def alerta_repository() -> AlertaRepository:
    return AlertaRepository(settings.data_dir / "alertas.json")


@lru_cache
def boveda_repository() -> BovedaRepository:
    return BovedaRepository(settings.data_dir / "bovedas.json")


@lru_cache
def auditoria_repository() -> AuditoriaRepository:
    return AuditoriaRepository(settings.data_dir / "auditoria.json")


# --- Servicios -----------------------------------------------------------
@lru_cache
def correlacion_service() -> CorrelacionAlertasService:
    """Reglas de correlación de alertas (Módulo 7, mejora #13).

    Depende solo del repositorio de alertas (lee el histórico y escribe sus
    propias alertas), por lo que no hay ciclos con ``alerta_service``.
    """

    return CorrelacionAlertasService(alerta_repository())


@lru_cache
def alerta_service() -> AlertaService:
    return AlertaService(alerta_repository(), correlacion=correlacion_service())


@lru_cache
def auditoria_service() -> AuditoriaService:
    return AuditoriaService(auditoria_repository())


@lru_cache
def user_service() -> UserService:
    return UserService(user_repository(), alerta_service(), auditoria_service())


@lru_cache
def auth_service() -> AuthService:
    return AuthService(user_repository(), alerta_service(), auditoria_service())


@lru_cache
def expediente_service() -> ExpedienteService:
    return ExpedienteService(
        expediente_repository(), user_repository(), alerta_service(), auditoria_service()
    )


@lru_cache
def documento_service() -> DocumentoService:
    return DocumentoService(
        documento_repository(), expediente_repository(), alerta_service(), auditoria_service()
    )


@lru_cache
def boveda_service() -> BovedaService:
    return BovedaService(
        boveda_repository(), expediente_repository(), alerta_service(), auditoria_service()
    )
