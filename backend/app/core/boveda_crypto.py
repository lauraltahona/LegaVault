"""Criptografía de la bóveda cifrada de doble fondo (Módulo 4).

Diseño
------
- Cada **vista** de la bóveda (un conjunto de contenido independiente) se cifra
  con una clave derivada de *su* contraseña mediante **scrypt** (KDF) y un salt
  aleatorio propio.
- El cifrado usa **AES-256-GCM** (AEAD), que aporta confidencialidad *y*
  autenticidad: si el contenido o los metadatos se alteran, el descifrado falla.
- Cada vista es un diccionario autocontenido ``{"salt", "nonce", "datos"}`` con
  los valores en base64. **Nunca** se almacena la contraseña ni la clave.
- La *negación plausible* se apoya en que la estructura de la bóveda no permite
  distinguir qué contraseña corresponde a qué vista: ambas tienen el mismo
  formato y no llevan etiquetas.

Se usan únicamente primitivas de librerías reconocidas (``hashlib`` y
``cryptography``); no se implementa criptografía propia.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# Parámetros de la derivación de clave (coste adecuado para un prototipo).
_SCRYPT_N = 2 ** 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_DKLEN = 32
_MAXMEM = 64 * 1024 * 1024

_SALT_BYTES = 16
_NONCE_BYTES = 12  # tamaño recomendado para GCM


def _b64_encode(raw: bytes) -> str:
    return base64.b64encode(raw).decode("ascii")


def _b64_decode(value: str) -> bytes:
    return base64.b64decode(value.encode("ascii"))


def derivar_clave(password: str, salt: bytes) -> bytes:
    """Deriva una clave de 32 bytes desde una contraseña y su salt (scrypt)."""

    if not password:
        raise ValueError("La contraseña no puede estar vacía")
    return hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_N,
        r=_SCRYPT_R,
        p=_SCRYPT_P,
        dklen=_DKLEN,
        maxmem=_MAXMEM,
    )


def cifrar(datos: dict, password: str) -> dict:
    """Cifra un objeto (dict) y devuelve la vista ``{"salt","nonce","datos"}``.

    Se genera un salt y un nonce nuevos en cada llamada. Reutilizar el nonce
    con la misma clave sería inseguro en GCM, por eso nunca se reutiliza.
    """

    salt = os.urandom(_SALT_BYTES)
    nonce = os.urandom(_NONCE_BYTES)
    clave = derivar_clave(password, salt)
    plano = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    cifrado = AESGCM(clave).encrypt(nonce, plano, None)
    return {
        "salt": _b64_encode(salt),
        "nonce": _b64_encode(nonce),
        "datos": _b64_encode(cifrado),
    }


def descifrar(blob: dict, password: str) -> dict | None:
    """Descifra una vista. Devuelve ``None`` si la contraseña es incorrecta o el
    contenido fue alterado (la autenticación de GCM no valida)."""

    try:
        salt = _b64_decode(blob["salt"])
        nonce = _b64_decode(blob["nonce"])
        cifrado = _b64_decode(blob["datos"])
        clave = derivar_clave(password, salt)
        plano = AESGCM(clave).decrypt(nonce, cifrado, None)
        resultado = json.loads(plano.decode("utf-8"))
    except (InvalidTag, KeyError, ValueError, TypeError, json.JSONDecodeError):
        return None
    return resultado if isinstance(resultado, dict) else None


def es_vista_valida(blob: object) -> bool:
    """Comprueba que un objeto tiene la forma de una vista cifrada."""

    return (
        isinstance(blob, dict)
        and all(isinstance(blob.get(campo), str) for campo in ("salt", "nonce", "datos"))
    )
