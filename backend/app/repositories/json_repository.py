"""Repositorio genérico respaldado por un archivo JSON.

Garantías:
- **Escrituras atómicas**: se escribe en un archivo temporal y se reemplaza
  con ``os.replace`` para evitar dejar el JSON corrupto ante un fallo.
- **Concurrencia**: un ``RLock`` por instancia serializa el acceso.
- **Aislamiento**: expone entidades de dominio, no diccionarios crudos.
"""

from __future__ import annotations

import json
import os
import threading
from pathlib import Path
from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class JsonRepository(Generic[T]):
    def __init__(self, file_path: str | Path, model_cls: type[T]) -> None:
        self._path = Path(file_path)
        self._model = model_cls
        self._lock = threading.RLock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
        if not self._path.exists():
            self._write_rows([])

    @property
    def path(self) -> Path:
        return self._path

    # --- acceso interno -------------------------------------------------
    def _read_rows(self) -> list[dict]:
        try:
            with self._path.open("r", encoding="utf-8") as handle:
                data = json.load(handle)
        except (json.JSONDecodeError, FileNotFoundError):
            return []
        return data if isinstance(data, list) else []

    def _write_rows(self, rows: list[dict]) -> None:
        temp_path = self._path.with_name(self._path.name + ".tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(rows, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_path, self._path)

    # --- API pública ----------------------------------------------------
    def list_all(self) -> list[T]:
        with self._lock:
            return [self._model.from_dict(row) for row in self._read_rows()]

    def get(self, entity_id: str) -> T | None:
        with self._lock:
            for row in self._read_rows():
                if row.get("id") == entity_id:
                    return self._model.from_dict(row)
        return None

    def find(self, predicate: Callable[[T], bool]) -> list[T]:
        return [entity for entity in self.list_all() if predicate(entity)]

    def first(self, predicate: Callable[[T], bool]) -> T | None:
        for entity in self.list_all():
            if predicate(entity):
                return entity
        return None

    def add(self, entity: T) -> T:
        with self._lock:
            rows = self._read_rows()
            rows.append(entity.to_dict())
            self._write_rows(rows)
        return entity

    def add_many(self, entities: list[T]) -> list[T]:
        with self._lock:
            rows = self._read_rows()
            rows.extend(entity.to_dict() for entity in entities)
            self._write_rows(rows)
        return entities

    def update(self, entity: T) -> T:
        with self._lock:
            rows = self._read_rows()
            for index, row in enumerate(rows):
                if row.get("id") == entity.id:
                    rows[index] = entity.to_dict()
                    break
            else:
                rows.append(entity.to_dict())
            self._write_rows(rows)
        return entity

    def delete(self, entity_id: str) -> bool:
        with self._lock:
            rows = self._read_rows()
            remaining = [row for row in rows if row.get("id") != entity_id]
            if len(remaining) == len(rows):
                return False
            self._write_rows(remaining)
            return True

    def count(self) -> int:
        with self._lock:
            return len(self._read_rows())
