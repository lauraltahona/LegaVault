"""Repositorio de expedientes (Módulo 2)."""

from __future__ import annotations

from pathlib import Path

from app.models.expediente import Expediente
from app.repositories.json_repository import JsonRepository


class ExpedienteRepository(JsonRepository[Expediente]):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path, Expediente)

    def get_by_identificador(self, identificador: str) -> Expediente | None:
        objetivo = (identificador or "").strip().lower()
        return self.first(lambda exp: exp.identificador.lower() == objetivo)

    def identificador_exists(self, identificador: str, exclude_id: str | None = None) -> bool:
        objetivo = (identificador or "").strip().lower()
        return any(
            exp.identificador.lower() == objetivo and exp.id != exclude_id
            for exp in self.list_all()
        )
