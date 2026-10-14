"""Modelo de usuario (Módulo 1)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from app.core.constants import Rol
from app.models.base import BaseEntity, decode_datetime


@dataclass
class User(BaseEntity):
    username: str = ""
    nombre_completo: str = ""
    email: str = ""
    password_hash: str = ""
    rol: Rol = Rol.ABOGADO
    activo: bool = True

    # --- Estado de seguridad (Módulo 7) ---
    intentos_fallidos: int = 0
    bloqueado_hasta: datetime | None = None
    ultimo_acceso: datetime | None = None

    @property
    def esta_bloqueado(self) -> bool:
        from app.models.base import utcnow

        return self.bloqueado_hasta is not None and self.bloqueado_hasta > utcnow()

    @classmethod
    def from_dict(cls, data: dict) -> "User":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            username=data.get("username", ""),
            nombre_completo=data.get("nombre_completo", ""),
            email=data.get("email", ""),
            password_hash=data.get("password_hash", ""),
            rol=Rol(data.get("rol", Rol.ABOGADO.value)),
            activo=bool(data.get("activo", True)),
            intentos_fallidos=int(data.get("intentos_fallidos", 0)),
            bloqueado_hasta=decode_datetime(data.get("bloqueado_hasta")),
            ultimo_acceso=decode_datetime(data.get("ultimo_acceso")),
        )
