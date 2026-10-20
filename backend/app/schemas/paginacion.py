"""Esquema genérico de respuesta paginada (Módulo 2/6/7 — mejora #10 del plan).

Contrato de la API para los listados que pueden crecer mucho (auditoría,
alertas, documentos, expedientes): la respuesta deja de ser un array plano y
pasa a ser un objeto con la página actual y los metadatos de paginación::

    {"items": [...], "total": 137, "pagina": 2, "por_pagina": 20, "paginas": 7}

Ventajas: el cliente conoce el total sin descargar la colección completa y la
respuesta es estable aunque se agreguen campos (p. ej. ordenación) en el futuro.
"""

from __future__ import annotations

import math
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class RespuestaPaginada(BaseModel, Generic[T]):
    """Listado paginado: ``items`` de la página actual + metadatos."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    pagina: int = 1
    por_pagina: int = 20
    paginas: int = 0

    @classmethod
    def crear(
        cls, items: list[T], total: int, pagina: int, por_pagina: int
    ) -> "RespuestaPaginada[T]":
        """Construye la respuesta calculando el número total de páginas."""

        paginas = math.ceil(total / por_pagina) if por_pagina > 0 else 0
        return cls(
            items=items,
            total=total,
            pagina=pagina,
            por_pagina=por_pagina,
            paginas=paginas,
        )
