"""Inicialización de datos mínimos para que la aplicación arranque."""

from __future__ import annotations

import os

from app.core.config import settings
from app.core.constants import Rol
from app.core.container import user_repository
from app.core.security import hash_password
from app.models.user import User

ADMIN_USER = os.getenv("LEGALVAULT_ADMIN_USER", "admin")
ADMIN_EMAIL = os.getenv("LEGALVAULT_ADMIN_EMAIL", "admin@legalvault.local")
ADMIN_PASSWORD = os.getenv("LEGALVAULT_ADMIN_PASSWORD", "Admin123!")


def asegurar_datos_iniciales() -> None:
    """Crea el administrador inicial si aún no existe ningún usuario.

    Las credenciales por defecto son solo para el entorno académico: deben
    cambiarse y definirse por variables de entorno en cualquier otro caso.
    """

    settings.ensure_directories()
    repositorio = user_repository()
    if repositorio.count() > 0:
        return

    admin = User(
        username=ADMIN_USER,
        nombre_completo="Administrador LegalVault",
        email=ADMIN_EMAIL,
        password_hash=hash_password(ADMIN_PASSWORD),
        rol=Rol.ADMIN,
    )
    repositorio.add(admin)
    print(
        "[LegalVault] Usuario administrador inicial creado.\n"
        f"            usuario: {ADMIN_USER}\n"
        f"            contraseña: {ADMIN_PASSWORD}\n"
        "            (cámbiela antes de usar la aplicación)."
    )
