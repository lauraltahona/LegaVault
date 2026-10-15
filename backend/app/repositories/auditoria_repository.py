"""Repositorio de auditoría con cadena de integridad (Módulo 6).

Amplía :class:`JsonRepository` con dos garantías propias del registro de
auditoría:

- ``append`` calcula el encadenado de hashes de forma **atómica** (lectura del
  último hash + escritura bajo el mismo bloqueo).
- ``verificar_cadena`` recalcula la cadena completa y localiza el primer
  registro roto (por edición, inserción o reordenación manual del JSON).
"""

from __future__ import annotations

from pathlib import Path

from app.models.registro_auditoria import HASH_GENESIS, RegistroAuditoria
from app.repositories.json_repository import JsonRepository


class AuditoriaRepository(JsonRepository[RegistroAuditoria]):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path, RegistroAuditoria)

    def append(self, registro: RegistroAuditoria) -> RegistroAuditoria:
        """Añade un registro encadenándolo con el último de la cadena."""

        with self._lock:
            rows = self._read_rows()
            anterior = rows[-1].get("hash_actual", HASH_GENESIS) if rows else HASH_GENESIS
            registro.hash_anterior = anterior
            registro.hash_actual = registro.calcular_hash()
            rows.append(registro.to_dict())
            self._write_rows(rows)
        return registro

    def ultimo(self) -> RegistroAuditoria | None:
        rows = self._read_rows()
        return RegistroAuditoria.from_dict(rows[-1]) if rows else None

    def verificar_cadena(self) -> tuple[bool, int | None]:
        """Verifica la cadena completa.

        Devuelve ``(True, None)`` si es íntegra o ``(False, indice)`` con la
        posición (0-based) del primer registro inválido.
        """

        rows = self._read_rows()
        anterior = HASH_GENESIS
        for indice, row in enumerate(rows):
            if row.get("hash_anterior") != anterior:
                return False, indice
            registro = RegistroAuditoria.from_dict(row)
            if row.get("hash_actual") != registro.calcular_hash():
                return False, indice
            anterior = row.get("hash_actual")
        return True, None
