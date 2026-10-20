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

Padding por cubetas (mejora #15)
--------------------------------
El texto cifrado no tiene una longitud fija: un contenido corto produce un blob
corto y uno largo, uno largo. Eso filtra información por el **tamaño** (¿cuánto
hay dentro? ¿son iguales las dos vistas?). Para evitarlo, el plano se rellena
hasta una *cubeta*: un múltiplo de 25 MB (escalera por defecto 1/5/25 MB) que se
elige al crear la bóveda y se guarda en ``bucket_mb``. Ambas vistas usan la
misma cubeta, así que **ambas ocupan exactamente los mismos bytes** en disco.

Formato del plano antes de cifrar::

    b"LVB" | version(1B) | len_json(uint32 BE) | json_utf8 | relleno aleatorio

El relleno es ``os.urandom`` (no ceros) para no ofrecer un patrón reconocible. El
cifrado GCM añade después 16 bytes de etiqueta, de modo que el blob mide
``bucket + 16`` bytes. Al descifrar se comprueba primero la etiqueta GCM y luego
el encabezado; si no lleva el *magic* ``LVB`` se interpreta como el formato
heredado (JSON plano, sin padding) y se devuelve igualmente, de forma que las
bóvedas antiguas **siguen abriéndose** (migración al vuelo al guardarlas).

Se usan únicamente primitivas de librerías reconocidas (``hashlib``, ``os`` y
``cryptography``); no se implementa criptografía propia.
"""

from __future__ import annotations

import base64
import hashlib
import json
import os
import struct

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
_TAG_BYTES = 16  # etiqueta de autenticación de AES-GCM

# --- Formato con padding (mejora #15) ---
_MAGIC = b"LVB"  # 3 bytes que identifican el formato rellenado
_VERSION = 1  # versión del formato
_HEADER = struct.Struct(">3sBI")  # magic(3) + versión(1) + longitud(4, big-endian)
_BYTES_POR_MB = 1024 * 1024
# Escalera de cubetas admitidas (en MB) y su granularidad.
ESCALERA_BUCKET_MB = (1, 5, 25)
GRANULARIDAD_BUCKET_MB = 25
BUCKET_POR_DEFECTO_MB = 1


def calcular_bucket(bucket_mb: object, longitud: int) -> int:
    """Traduce ``bucket_mb`` a bytes, redondeando hacia arriba si hace falta.

    - ``bucket_mb`` None, 0 o negativo → sin padding (0 bytes).
    - Dentro de la escalera (1/5/25 MB) → esa cubeta.
    - Por encima de la escalera o a medio camino → múltiplo de 25 MB que
      contenga ``longitud`` (nunca menos de 1 MB).
    """

    try:
        pedido = int(bucket_mb)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return 0
    if pedido <= 0:
        return 0
    if pedido in ESCALERA_BUCKET_MB:
        return pedido * _BYTES_POR_MB
    # Redondeo a la cubeta de la escalera/múltiplo de 25 MB más cercano por arriba.
    escalones = max(1, -(-pedido // GRANULARIDAD_BUCKET_MB))
    return escalones * GRANULARIDAD_BUCKET_MB * _BYTES_POR_MB


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


def _empaquetar(datos: dict, bucket: int) -> bytes:
    """Serializa el contenido al formato con padding de tamaño ``bucket``.

    Con ``bucket == 0`` se omite el encabezado y se devuelve el JSON plano: es el
    formato *heredado*, útil para pruebas o compatibilidad estricta.
    """

    plano = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if bucket <= 0:
        return plano
    if len(plano) > bucket:
        raise ValueError("El contenido supera la cubeta configurada.")
    cabecera = _HEADER.pack(_MAGIC, _VERSION, len(plano))
    relleno = bucket - len(cabecera) - len(plano)
    # Relleno aleatorio (no ceros): no revela dónde acaba el contenido real.
    return cabecera + plano + os.urandom(relleno)


def _desempaquetar(blob: bytes) -> dict | None:
    """Revierte el formato con padding; tolera el JSON plano heredado."""

    if blob[:3] == _MAGIC:
        cabecera = _HEADER.size
        if len(blob) < cabecera:
            return None
        _magic, version, longitud = _HEADER.unpack(blob[:cabecera])
        if version != _VERSION:
            return None
        if longitud < 0 or cabecera + longitud > len(blob):
            return None
        cuerpo = blob[cabecera : cabecera + longitud]
    else:
        cuerpo = blob
    try:
        resultado = json.loads(cuerpo.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    return resultado if isinstance(resultado, dict) else None


def cifrar(datos: dict, password: str, *, bucket_mb: int | None = BUCKET_POR_DEFECTO_MB) -> dict:
    """Cifra un objeto (dict) y devuelve la vista ``{"salt","nonce","datos"}``.

    Se genera un salt y un nonce nuevos en cada llamada. Reutilizar el nonce
    con la misma clave sería inseguro en GCM, por eso nunca se reutiliza.

    ``bucket_mb`` fija la cubeta de padding: por defecto 1 MB (mejora #15); con
    ``None`` o ``0`` se cifra sin padding (formato heredado).
    """

    salt = os.urandom(_SALT_BYTES)
    nonce = os.urandom(_NONCE_BYTES)
    clave = derivar_clave(password, salt)
    plano = _empaquetar(datos, calcular_bucket(bucket_mb, 0))
    cifrado = AESGCM(clave).encrypt(nonce, plano, None)
    return {
        "salt": _b64_encode(salt),
        "nonce": _b64_encode(nonce),
        "datos": _b64_encode(cifrado),
    }


def descifrar(blob: dict, password: str) -> dict | None:
    """Descifra una vista. Devuelve ``None`` si la contraseña es incorrecta o el
    contenido fue alterado (la autenticación de GCM no valida).

    Acepta tanto el formato con padding (mejora #15) como el JSON plano de las
    bóvedas antiguas, que siguen abriéndose sin cambios.
    """

    try:
        salt = _b64_decode(blob["salt"])
        nonce = _b64_decode(blob["nonce"])
        cifrado = _b64_decode(blob["datos"])
        clave = derivar_clave(password, salt)
        plano = AESGCM(clave).decrypt(nonce, cifrado, None)
        resultado = _desempaquetar(plano)
    except (InvalidTag, KeyError, ValueError, TypeError):
        return None
    return resultado


def es_vista_valida(blob: object) -> bool:
    """Comprueba que un objeto tiene la forma de una vista cifrada."""

    return (
        isinstance(blob, dict)
        and all(isinstance(blob.get(campo), str) for campo in ("salt", "nonce", "datos"))
    )
