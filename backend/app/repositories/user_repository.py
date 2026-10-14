"""Repositorio de usuarios (Módulo 1)."""

from __future__ import annotations

from pathlib import Path

from app.core.constants import Rol
from app.models.user import User
from app.repositories.json_repository import JsonRepository


class UserRepository(JsonRepository[User]):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path, User)

    def get_by_username(self, username: str) -> User | None:
        objetivo = (username or "").strip().lower()
        return self.first(lambda user: user.username.lower() == objetivo)

    def username_exists(self, username: str, exclude_id: str | None = None) -> bool:
        objetivo = (username or "").strip().lower()
        return any(
            user.username.lower() == objetivo and user.id != exclude_id
            for user in self.list_all()
        )

    def email_exists(self, email: str, exclude_id: str | None = None) -> bool:
        objetivo = (email or "").strip().lower()
        return any(
            user.email.lower() == objetivo and user.id != exclude_id
            for user in self.list_all()
        )

    def count_admins_activos(self) -> int:
        return len(
            [user for user in self.list_all() if user.rol == Rol.ADMIN and user.activo]
        )
