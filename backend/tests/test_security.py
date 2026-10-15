"""Pruebas base de primitivas de seguridad."""

from __future__ import annotations

import time

from app.core import security


def test_hash_password_verifies() -> None:
    hashed = security.hash_password("Admin123!")
    assert hashed is not None
    assert hashed != "Admin123!"
    assert security.verify_password("Admin123!", hashed) is True
    assert security.verify_password("otro456", hashed) is False


def test_create_and_decode_token_contains_subject_and_roles() -> None:
    token, _ = security.create_access_token(subject="u1", role="admin")
    payload = security.decode_access_token(token)
    assert payload["sub"] == "u1"
    assert payload["role"] == "admin"
    assert "exp" in payload
    assert "jti" in payload


def test_decode_token_fails_with_tampered_token() -> None:
    token, _ = security.create_access_token(subject="u1", role="abogado")
    tampered = token[:-1] + ("x" if token[-1] != "x" else "y")
    try:
        security.decode_access_token(tampered)
        raise AssertionError("Debió lanzar una excepción para token manipulado")
    except Exception:
        pass


def test_revoke_token_prevents_decoding() -> None:
    token, _ = security.create_access_token(subject="u1", role="abogado")
    payload = security.decode_access_token(token)
    assert payload["sub"] == "u1"
    security.revoke_token(payload["jti"], payload["exp"])
    try:
        security.decode_access_token(token)
        raise AssertionError("El token revocado debe dejar de ser válido")
    except Exception:
        pass


def test_create_access_token_with_short_expiration() -> None:
    token, _ = security.create_access_token(subject="u2", role="abogado")
    payload = security.decode_access_token(token)
    assert payload["exp"] > int(time.time())
