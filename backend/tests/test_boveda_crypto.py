"""Pruebas unitarias de la criptografía de la bóveda (Módulo 4)."""

from __future__ import annotations

import copy

import pytest

from app.core.boveda_crypto import cifrar, descifrar, es_vista_valida

DATO = {"entradas": [{"id": "1", "titulo": "Nota", "contenido": "secreto"}]}


def test_round_trip() -> None:
    blob = cifrar(DATO, "FraseDePaso123")
    assert descifrar(blob, "FraseDePaso123") == DATO


def test_password_incorrecta_devuelve_none() -> None:
    blob = cifrar(DATO, "FraseDePaso123")
    assert descifrar(blob, "OtraFrase999") is None


def test_datos_alterados_devuelve_none() -> None:
    blob = cifrar(DATO, "FraseDePaso123")
    alterado = copy.deepcopy(blob)
    # Cambiar un carácter del texto cifrado invalida la etiqueta GCM.
    datos = alterado["datos"]
    alterado["datos"] = ("A" if datos[0] != "A" else "B") + datos[1:]
    assert descifrar(alterado, "FraseDePaso123") is None


def test_estructura_de_vista_valida() -> None:
    blob = cifrar(DATO, "FraseDePaso123")
    assert es_vista_valida(blob)
    assert set(blob) == {"salt", "nonce", "datos"}
    assert not es_vista_valida({"salt": "x"})
    assert not es_vista_valida("no soy una vista")


def test_salt_y_nonce_aleatorios() -> None:
    primero = cifrar(DATO, "FraseDePaso123")
    segundo = cifrar(DATO, "FraseDePaso123")
    assert primero["salt"] != segundo["salt"]
    assert primero["nonce"] != segundo["nonce"]
    assert primero["datos"] != segundo["datos"]


def test_password_vacia_no_es_valida() -> None:
    with pytest.raises(ValueError):
        cifrar(DATO, "")


def test_el_texto_cifrado_no_contiene_el_plano() -> None:
    blob = cifrar(DATO, "FraseDePaso123")
    assert "secreto" not in blob["datos"]
    assert "secreto" not in blob["salt"]
    assert "secreto" not in blob["nonce"]
