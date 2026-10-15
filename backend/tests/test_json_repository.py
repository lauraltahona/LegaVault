"""Pruebas del repositorio genérico JSON."""

from __future__ import annotations

import json
from pathlib import Path
from tempfile import NamedTemporaryFile

from app.repositories.json_repository import JsonRepository


class _Dummy:
    def __init__(self, id: str, nombre: str | None = None, v: int | None = None) -> None:
        self.id = id
        self.nombre = nombre
        self.v = v

    @classmethod
    def from_dict(cls, data: dict) -> "_Dummy":
        return cls(**data)

    def to_dict(self) -> dict:
        d = {"id": self.id}
        if self.nombre is not None:
            d["nombre"] = self.nombre
        if self.v is not None:
            d["v"] = self.v
        return d


def test_crud_basico() -> None:
    with NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as f:
        path = Path(f.name)

    try:
        repo = JsonRepository(path, _Dummy)
        assert repo.count() == 0

        d1 = repo.add(_Dummy(id="1", nombre="A"))
        assert isinstance(d1, _Dummy)
        assert repo.count() == 1

        obtenido = repo.get("1")
        assert obtenido is not None
        assert obtenido.nombre == "A"

        actualizado = repo.update(_Dummy(id="1", nombre="A2"))
        assert actualizado is not None
        assert actualizado.nombre == "A2"

        lista = repo.list_all()
        assert len(lista) == 1
        assert lista[0].nombre == "A2"

        encontrados = repo.find(lambda x: x.nombre == "A2")
        assert len(encontrados) == 1
        assert encontrados[0].id == "1"

        primero = repo.first(lambda x: x.nombre == "A2")
        assert primero is not None
        assert primero.id == "1"

        eliminado = repo.delete("1")
        assert eliminado is True
        assert repo.count() == 0
        assert repo.get("1") is None
        assert repo.delete("1") is False
    finally:
        if path.exists():
            path.unlink()


def test_update_no_existe_inserta() -> None:
    with NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as f:
        path = Path(f.name)

    try:
        repo = JsonRepository(path, _Dummy)
        res = repo.update(_Dummy(id="no", nombre="X"))
        assert res.nombre == "X"
        assert repo.count() == 1
    finally:
        if path.exists():
            path.unlink()


def test_escritura_atomica_no_corrompe() -> None:
    with NamedTemporaryFile(mode="w", delete=False, suffix=".json", encoding="utf-8") as f:
        path = Path(f.name)

    try:
        repo = JsonRepository(path, _Dummy)
        repo.add(_Dummy(id="1", v=1))
        data = json.loads(path.read_text(encoding="utf-8"))
        assert data[0]["id"] == "1"

        repo.update(_Dummy(id="1", v=2))
        data2 = json.loads(path.read_text(encoding="utf-8"))
        assert data2[0]["v"] == 2
    finally:
        if path.exists():
            path.unlink()
