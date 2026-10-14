"""Repositorio de documentos (Módulo 3)."""

from __future__ import annotations

from pathlib import Path

from app.models.documento import Documento
from app.repositories.json_repository import JsonRepository


class DocumentoRepository(JsonRepository[Documento]):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path, Documento)

    def find_by_expediente(self, expediente_id: str) -> list[Documento]:
        return self.find(lambda doc: doc.expediente_id == expediente_id)

    def count_by_expediente(self, expediente_id: str) -> int:
        return len(self.find_by_expediente(expediente_id))
