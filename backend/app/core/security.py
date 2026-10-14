"""Primitivas de seguridad.

- Hash de contraseñas de usuario con **scrypt** (``hashlib`` de la stdlib),
  con salt aleatorio por usuario. Nunca se guarda la contraseña en claro.
- Emisión/validación de **tokens JWT** (PyJWT) para las sesiones.
- Lista de revocación en memoria para el cierre de sesión del lado servidor.

Nota académica: la lista de revocación es en memoria y se pierde al
reiniciar el proceso. Para producción debe usarse un almacén persistente
(Redis, base de datos) o tokens de corta duración con refresh tokens.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import threading
import uuid
from datetime import datetime, timedelta, timezone

import jwt

from app.core.config import settings

# Parámetros de scrypt (coste recomendado para un prototipo).
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_SALT_BYTES = 16
_MAXMEM = 64 * 1024 * 1024

_ALGORITHM = "scrypt"


def _b64encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def hash_password(password: str) -> str:
    """Devuelve un hash autocontenido con formato ``scrypt$N$r$p$salt$hash``."""

    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    salt = os.urandom(_SALT_BYTES)
    derived = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
        maxmem=_MAXMEM,
    )
    return f"{_ALGORITHM}${_SCRYPT_N}${_SCRYPT_R}${_SCRYPT_P}${_b64encode(salt)}${_b64encode(derived)}"


def verify_password(password: str, stored_hash: str) -> bool:
    """Compara una contraseña con su hash en tiempo constante."""

    if not password or not stored_hash:
        return False
    try:
        algorithm, n, r, p, salt_b64, hash_b64 = stored_hash.split("$")
        if algorithm != _ALGORITHM:
            return False
        salt = _b64decode(salt_b64)
        expected = _b64decode(hash_b64)
        derived = hashlib.scrypt(
            password.encode("utf-8"),
            salt=salt,
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=len(expected),
            maxmem=_MAXMEM,
        )
    except (ValueError, TypeError):
        return False
    return hmac.compare_digest(derived, expected)


# --------------------------------------------------------------------------
# Tokens de sesión (JWT)
# --------------------------------------------------------------------------

_revoked_tokens: dict[str, float] = {}
_revoked_lock = threading.Lock()


def create_access_token(subject: str, role: str, expires_minutes: int | None = None) -> tuple[str, datetime]:
    """Genera un token JWT y devuelve ``(token, fecha_expiracion)``."""

    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=expires_minutes or settings.minutos_expiracion_token)
    payload = {
        "sub": subject,
        "role": role,
        "iat": now,
        "nbf": now,
        "exp": expires_at,
        "jti": uuid.uuid4().hex,
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)
    return token, expires_at


def decode_access_token(token: str) -> dict:
    """Valida un token y devuelve su payload. Lanza ``jwt.InvalidTokenError``."""

    payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    jti = payload.get("jti")
    if jti and is_token_revoked(jti):
        raise jwt.InvalidTokenError("El token fue revocado")
    return payload


def revoke_token(jti: str, expires_at: float | None = None) -> None:
    """Registra un token como revocado hasta su expiración."""

    with _revoked_lock:
        _revoked_tokens[jti] = expires_at or (datetime.now(timezone.utc).timestamp() + 3600)


def is_token_revoked(jti: str) -> bool:
    now_ts = datetime.now(timezone.utc).timestamp()
    with _revoked_lock:
        expired = [key for key, exp in _revoked_tokens.items() if exp <= now_ts]
        for key in expired:
            _revoked_tokens.pop(key, None)
        return jti in _revoked_tokens
