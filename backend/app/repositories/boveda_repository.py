"""Repositorio de bóvedas cifradas (Módulo 4)."""

from __future__ import annotations

from pathlib import Path

from app.models.boveda import Boveda
from app.repositories.json_repository import JsonRepository


class BovedaRepository(JsonRepository[Boveda]):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path, Boveda)

    def find_by_expediente(self, expediente_id: str) -> list[Boveda]:
        return self.find(lambda boveda: boveda.expediente_id == expediente_id)
