"""Controladores: frontera HTTP de la aplicación (patrón MVC)."""

from app.controllers.alerta_controller import router as alerta_router
from app.controllers.auth_controller import router as auth_router
from app.controllers.documento_controller import router as documento_router
from app.controllers.expediente_controller import router as expediente_router
from app.controllers.user_controller import router as user_router

__all__ = [
    "alerta_router",
    "auth_router",
    "documento_router",
    "expediente_router",
    "user_router",
]
