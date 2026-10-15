"""Pruebas base de validadores de entrada."""

from __future__ import annotations

import pytest

from app.core.exceptions import ValidationError
from app.core.validators import (
    validar_email,
    validar_password,
    validar_password_boveda,
    validar_texto_obligatorio,
    validar_username,
)


def test_validar_username() -> None:
    assert validar_username("abogado01") == "abogado01"
    assert validar_username("demo.user") == "demo.user"
    assert validar_username("Usuario_1") == "Usuario_1"

    with pytest.raises(ValidationError):
        validar_username("")

    with pytest.raises(ValidationError):
        validar_username("ab")

    with pytest.raises(ValidationError):
        validar_username("*no*")

    with pytest.raises(ValidationError):
        validar_username(" ")


def test_validar_email() -> None:
    assert validar_email("legal@vault.org") == "legal@vault.org"

    with pytest.raises(ValidationError):
        validar_email("")

    with pytest.raises(ValidationError):
        validar_email("invalido")

    with pytest.raises(ValidationError):
        validar_email("a@b")


def test_validar_password() -> None:
    assert validar_password("Abogado123!") == "Abogado123!"

    with pytest.raises(ValidationError):
        validar_password("")

    with pytest.raises(ValidationError):
        validar_password("abc123")  # < 8

    with pytest.raises(ValidationError):
        validar_password("abcdefgh")  # solo letras

    with pytest.raises(ValidationError):
        validar_password("12345678")  # solo dígitos


def test_validar_password_boveda() -> None:
    # La política admite frases largas; no obliga dígitos ni símbolos.
    assert validar_password_boveda("BovedaSegura123!") == "BovedaSegura123!"
    assert validar_password_boveda("frase-de-paso-muy-larga-y-segura") == "frase-de-paso-muy-larga-y-segura"

    with pytest.raises(ValidationError):
        validar_password_boveda("")

    with pytest.raises(ValidationError):
        validar_password_boveda("abcde")  # muy corta

    with pytest.raises(ValidationError):
        validar_password_boveda("a1!bcde")  # muy corta (< 8)


def test_validar_texto_obligatorio() -> None:
    assert validar_texto_obligatorio("x", "campo") == "x"

    with pytest.raises(ValidationError):
        validar_texto_obligatorio("", "campo")

    with pytest.raises(ValidationError):
        validar_texto_obligatorio("   ", "campo")
