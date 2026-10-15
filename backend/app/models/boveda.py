"""Modelo de bóveda cifrada de doble fondo (Módulo 4).

Una bóveda guarda **dos vistas cifradas** independientes. Cada vista es un
diccionario ``{"salt", "nonce", "datos"}`` (valores en base64) que solo puede
descifrarse con su contraseña. El modelo **no** contiene contraseñas ni claves,
y no lleva ninguna etiqueta que revele qué vista es "visible" y cuál
"confidencial": las dos son indistinguibles.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.models.base import BaseEntity, decode_datetime


@dataclass
class Boveda(BaseEntity):
    nombre: str = ""
    descripcion: str = ""
    # Expediente al que se asocia la bóveda (opcional).
    expediente_id: str = ""
    creado_por_id: str = ""
    # Exactamente dos vistas cifradas, sin orden significativo.
    vistas: list[dict] = field(default_factory=list)
    activo: bool = True

    @classmethod
    def from_dict(cls, data: dict) -> "Boveda":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            nombre=data.get("nombre", ""),
            descripcion=data.get("descripcion", ""),
            expediente_id=data.get("expediente_id", ""),
            creado_por_id=data.get("creado_por_id", ""),
            vistas=list(data.get("vistas") or []),
            activo=bool(data.get("activo", True)),
        )
