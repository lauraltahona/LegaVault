"""Pruebas del padding por cubetas de la bóveda (Módulo 4, mejora #15).

Se comprueba el formato con padding, su tamaño exacto, la tolerancia al formato
heredado (sin padding) y el cálculo de la cubeta.
"""

from __future__ import annotations

import base64
import copy
import json

import pytest

from app.core.boveda_crypto import (
    _MAGIC,
    calcular_bucket,
    cifrar,
    descifrar,
)

DATO = {"entradas": [{"id": "1", "titulo": "Nota", "contenido": "secreto"}]}
PASSWORD = "FraseDePaso123"

MB = 1024 * 1024


def _bytes_cifrados(blob: dict) -> bytes:
    return base64.b64decode(blob["datos"])


# --- calcular_bucket ---------------------------------------------------
def test_calcular_bucket_escalera() -> None:
    assert calcular_bucket(1, 0) == 1 * MB
    assert calcular_bucket(5, 0) == 5 * MB
    assert calcular_bucket(25, 0) == 25 * MB


def test_calcular_bucket_redondea_por_arriba() -> None:
    # Por encima de la escalera se sube a múltiplos de 25 MB.
    assert calcular_bucket(26, 0) == 50 * MB
    assert calcular_bucket(50, 0) == 50 * MB
    # Valores intermedios que no están en la escalera también se redondean.
    assert calcular_bucket(2, 0) == 25 * MB
    assert calcular_bucket(7, 0) == 25 * MB


def test_calcular_bucket_apagado() -> None:
    assert calcular_bucket(None, 0) == 0
    assert calcular_bucket(0, 0) == 0
    assert calcular_bucket(-3, 0) == 0
    assert calcular_bucket("no-numero", 0) == 0


# --- Tamaño y formato --------------------------------------------------
def test_el_blob_mide_bucket_mas_la_etiqueta_gcm() -> None:
    blob = cifrar(DATO, PASSWORD, bucket_mb=1)
    # 1 MB de plano + 16 bytes de etiqueta de AES-GCM.
    assert len(_bytes_cifrados(blob)) == 1 * MB + 16


@pytest.mark.parametrize("bucket_mb", [1, 5, 25])
def test_tamano_por_cubeta(bucket_mb: int) -> None:
    blob = cifrar(DATO, PASSWORD, bucket_mb=bucket_mb)
    assert len(_bytes_cifrados(blob)) == bucket_mb * MB + 16


def test_el_plano_lleva_el_encabezado_magic() -> None:
    # Se fuerza bucket 0 no: para inspeccionar el encabezado desciframos el plano.
    import hashlib

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    blob = cifrar(DATO, PASSWORD, bucket_mb=1)
    salt = base64.b64decode(blob["salt"])
    nonce = base64.b64decode(blob["nonce"])
    clave = hashlib.scrypt(salt=salt, password=PASSWORD.encode(), n=2 ** 14, r=8, p=1, dklen=32, maxmem=64 * MB)
    plano = AESGCM(clave).decrypt(nonce, _bytes_cifrados(blob), None)
    assert plano[:3] == _MAGIC
    assert len(plano) == 1 * MB


def test_contenidos_distintos_mismo_tamano() -> None:
    corto = cifrar({"entradas": []}, PASSWORD, bucket_mb=1)
    largo = cifrar(DATO, PASSWORD, bucket_mb=1)
    assert len(_bytes_cifrados(corto)) == len(_bytes_cifrados(largo))


def test_sin_padding_es_mas_pequeno() -> None:
    con = cifrar(DATO, PASSWORD, bucket_mb=1)
    sin = cifrar(DATO, PASSWORD, bucket_mb=0)
    assert len(_bytes_cifrados(sin)) < len(_bytes_cifrados(con))


# --- Round-trip --------------------------------------------------------
def test_round_trip_con_padding() -> None:
    blob = cifrar(DATO, PASSWORD, bucket_mb=1)
    assert descifrar(blob, PASSWORD) == DATO


def test_password_incorrecta_con_padding_devuelve_none() -> None:
    blob = cifrar(DATO, PASSWORD, bucket_mb=1)
    assert descifrar(blob, "OtraFrase999") is None


def test_datos_alterados_con_padding_devuelve_none() -> None:
    blob = cifrar(DATO, PASSWORD, bucket_mb=1)
    alterado = copy.deepcopy(blob)
    datos = alterado["datos"]
    alterado["datos"] = ("A" if datos[0] != "A" else "B") + datos[1:]
    assert descifrar(alterado, PASSWORD) is None


# --- Compatibilidad con el formato heredado ----------------------------
def _vista_heredada(datos: dict, password: str) -> dict:
    """Construye una vista en el formato antiguo (JSON plano, sin padding)."""

    import hashlib
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    salt = os.urandom(16)
    nonce = os.urandom(12)
    clave = hashlib.scrypt(salt=salt, password=password.encode(), n=2 ** 14, r=8, p=1, dklen=32, maxmem=64 * MB)
    plano = json.dumps(datos, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    cifrado = AESGCM(clave).encrypt(nonce, plano, None)
    return {
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "datos": base64.b64encode(cifrado).decode(),
    }


def test_las_bovedas_antiguas_siguen_abriendo() -> None:
    blob = _vista_heredada(DATO, PASSWORD)
    # El formato heredado no lleva encabezado: se devuelve tal cual.
    assert descifrar(blob, PASSWORD) == DATO


def test_encabezado_corrupto_no_revienta() -> None:
    import hashlib
    import os

    from cryptography.hazmat.primitives.ciphers.aead import AESGCM

    # Plano con magic pero con una longitud imposible: se trata como error suave.
    salt = os.urandom(16)
    nonce = os.urandom(12)
    clave = hashlib.scrypt(salt=salt, password=PASSWORD.encode(), n=2 ** 14, r=8, p=1, dklen=32, maxmem=64 * MB)
    plano = _MAGIC + b"\x01" + (9_999_999).to_bytes(4, "big") + b"corto"
    cifrado = AESGCM(clave).encrypt(nonce, plano, None)
    blob = {
        "salt": base64.b64encode(salt).decode(),
        "nonce": base64.b64encode(nonce).decode(),
        "datos": base64.b64encode(cifrado).decode(),
    }
    assert descifrar(blob, PASSWORD) is None
