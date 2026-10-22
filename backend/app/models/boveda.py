"""Modelo de bóveda cifrada de doble fondo (Módulo 4).

Una bóveda guarda **dos vistas cifradas** independientes. Cada vista es un
diccionario ``{"salt", "nonce", "datos"}`` (valores en base64) que solo puede
descifrarse con su contraseña. El modelo **no** contiene contraseñas ni claves,
y no lleva ninguna etiqueta que revele qué vista es "visible" y cuál
"confidencial": las dos son indistinguibles.

Desde la **Fase 6 (mejora M4.1)** la bóveda puede además admitir **archivos
adjuntos** por fondo. Los metadatos de los adjuntos viven **dentro** del JSON
cifrado de la vista y sus bytes en un blob aparte de tamaño fijo
(``data/bovedas/{id}/adjuntos.bin``). El campo ``formato`` distingue la bóveda
heredada (1, solo texto) de la nueva (2, con adjuntos); las bóvedas existentes
se leen como v1 sin tocar el JSON.
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
    # Cubeta de padding (mejora #15), en MB. 0 = formato heredado sin padding.
    # Es la *misma* para las dos vistas, de modo que ambas ocupan igual en disco.
    bucket_mb: int = 0
    # Formato de la bóveda: 1 = heredado (solo texto), 2 = con adjuntos (Fase 6).
    # Las bóvedas existentes no tienen este campo: se leen como v1 sin tocar
    # el JSON (migración explícita, nunca automática).
    formato: int = 1
    # Capacidad de adjuntos por fondo, en MB. 0 = sin adjuntos (bóveda v1).
    adjuntos_mb: int = 0
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
            bucket_mb=int(data.get("bucket_mb") or 0),
            formato=int(data.get("formato") or 1),
            adjuntos_mb=int(data.get("adjuntos_mb") or 0),
            activo=bool(data.get("activo", True)),
        )
