"""Modelo base y utilidades de (de)serialización."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def utcnow() -> datetime:
    """Fecha/hora actual en UTC (consciente de zona horaria)."""

    return datetime.now(timezone.utc)


def new_id() -> str:
    return uuid.uuid4().hex


def encode_value(value: Any) -> Any:
    """Convierte tipos de dominio a tipos serializables en JSON."""

    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [encode_value(item) for item in value]
    if isinstance(value, dict):
        return {key: encode_value(item) for key, item in value.items()}
    return value


def decode_datetime(value: Any) -> datetime | None:
    """Reconstruye un ``datetime`` desde su representación ISO."""

    if value in (None, ""):
        return None
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


@dataclass
class BaseEntity:
    """Campos comunes a todas las entidades."""

    id: str = field(default_factory=new_id)
    creado_en: datetime = field(default_factory=utcnow)
    actualizado_en: datetime = field(default_factory=utcnow)

    def to_dict(self) -> dict[str, Any]:
        return encode_value(asdict(self))

    def tocar(self) -> None:
        """Actualiza la marca temporal de modificación."""

        self.actualizado_en = utcnow()
