"""Formato del blob de adjuntos de la bóveda cifrada (Módulo 4, mejora M4.1).

Este módulo es el **corazón de la Fase 6**: define, byte a byte, cómo se
guardan los archivos adjuntos de cada fondo sin que el tamaño en disco revele
cuál contiene qué.

Diseño
------
Los **bytes** de los adjuntos NO van en el JSON de la vista (ahí solo caben
metadatos: nombre, mime, tamaño y hash del texto plano). Van en un archivo
binario aparte::

    data/bovedas/{boveda_id}/adjuntos.bin

    ┌────────────────────────────┬────────────────────────────┐
    │  segmento 0  (vistas[0])   │  segmento 1  (vistas[1])   │
    └────────────────────────────┴────────────────────────────┘

El archivo mide **siempre** ``2 × segmento_bytes``, con independencia del
contenido: un fondo vacío y un fondo con 4 MiB ocupan exactamente lo mismo.
Cada segmento, a su vez, se divide en *slots* de tamaño fijo
(``slot_bytes = chunk_bytes + 16``, los 16 bytes son la etiqueta de GCM)::

    [slot 0][slot 1] … [slot k-1][relleno aleatorio]

Cifrado
-------
Cada *chunk* de cada archivo se cifra con **AES-256-GCM** usando una clave
propia de la vista (32 bytes aleatorios guardados dentro del JSON cifrado):

- ``nonce = IV_base(8 B) ‖ contador(4 B BE)``: el contador es **monótono y
  nunca se reutiliza** (ni al borrar un archivo ni al deshacer una operación
  fallida). Reutilizar un nonce con la misma clave rompe el GCM por completo.
- ``aad = b"LVATT1" ‖ boveda_id ‖ b"|" ‖ índice_vista ‖ contador(4 B BE)``:
  ata cada chunk a su bóveda, su vista y su posición, de modo que no se puede
  mover un chunk de un fondo a otro ni reordenar chunks sin que GCM lo detecte.
- El **último** chunk de cada archivo se rellena con bytes aleatorios hasta
  ``chunk_bytes``: el tamaño real del archivo no se filtra (la longitud
  verdadera va en el metadato cifrado).

Se usan únicamente primitivas de librerías reconocidas (``cryptography`` y la
stdlib); no se implementa criptografía propia.
"""

from __future__ import annotations

import os
import struct
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# --- Parámetros del formato ---------------------------------------------
TAG_BYTES = 16  # etiqueta de autenticación de AES-GCM
IV_BASE_BYTES = 8  # base del nonce (4 bytes de contador en big-endian)
CLAVE_BYTES = 32  # clave AES-256 de los chunks de una vista
AAD_PREFIJO = b"LVATT1"  # "LegalVault adjuntos tipo 1"
NOMBRE_BLOB = "adjuntos.bin"
NUM_VISTAS = 2  # una bóveda tiene exactamente dos fondos

BYTES_POR_MB = 1024 * 1024

# Escalera de capacidades admitidas por fondo (MB). Los valores fuera de la
# escalera se rechazan: una capacidad discreta evita filtrar el volumen real.
ESCALERA_ADJUNTOS_MB = (1, 5, 25)
ADJUNTOS_MB_POR_DEFECTO = 5

# Formato de los contadores (índices de chunk y de vista).
_COUNTER = struct.Struct(">I")


class ErrorAdjuntos(ValueError):
    """Error del formato del blob (contenido alterado o corrupto)."""


# --- Cálculo de tamaños ---------------------------------------------------
def bytes_chunk(capacidad_bytes: int, chunk_bytes_config: int) -> int:
    """Tamaño efectivo del chunk para una capacidad dada.

    Nunca supera ``chunk_bytes_config`` ni la capacidad menos la etiqueta
    GCM: así la capacidad mínima (1 MB) siempre admite **al menos un slot**
    en lugar de quedarse sin espacio útil.
    """

    capacidad = max(0, int(capacidad_bytes))
    configurado = max(1, int(chunk_bytes_config))
    return max(1, min(configurado, capacidad - TAG_BYTES))


def slot_bytes(capacidad_bytes: int, chunk_bytes_config: int) -> int:
    """Bytes que ocupa un slot (chunk cifrado + etiqueta GCM)."""

    return bytes_chunk(capacidad_bytes, chunk_bytes_config) + TAG_BYTES


def slots_por_capacidad(capacidad_bytes: int, chunk_bytes_config: int) -> int:
    """Número de slots que caben en el segmento de un fondo."""

    paso = slot_bytes(capacidad_bytes, chunk_bytes_config)
    return max(1, max(0, int(capacidad_bytes)) // paso)


def bytes_segmento(capacidad_bytes: int, chunk_bytes_config: int) -> int:
    """Tamaño en bytes del segmento de un fondo (y de cada slot multiplicado)."""

    return slots_por_capacidad(capacidad_bytes, chunk_bytes_config) * slot_bytes(
        capacidad_bytes, chunk_bytes_config
    )


def bytes_utiles(capacidad_bytes: int, chunk_bytes_config: int) -> int:
    """Bytes de texto plano que caben realmente en un fondo."""

    return slots_por_capacidad(capacidad_bytes, chunk_bytes_config) * bytes_chunk(
        capacidad_bytes, chunk_bytes_config
    )


def ruta_blob(bovedas_dir: Path | str, boveda_id: str) -> Path:
    """Ruta del blob de adjuntos de una bóveda."""

    return Path(bovedas_dir) / str(boveda_id) / NOMBRE_BLOB


# --- Nonce y datos asociados ---------------------------------------------
def nonce(iv_base: bytes, indice_chunk: int) -> bytes:
    """``IV_base(8 B) ‖ contador(4 B BE)``: 12 bytes, nunca repetidos."""

    if len(iv_base) != IV_BASE_BYTES:
        raise ErrorAdjuntos("La base del nonce debe tener 8 bytes.")
    if indice_chunk < 0 or indice_chunk > 0xFFFFFFFF:
        raise ErrorAdjuntos("El índice de chunk está fuera de rango.")
    return iv_base + _COUNTER.pack(indice_chunk)


def aad(boveda_id: str, indice_vista: int, indice_chunk: int) -> bytes:
    """Datos asociados: atan el chunk a su bóveda, su vista y su posición."""

    if indice_vista < 0 or indice_vista > 0xFF:
        raise ErrorAdjuntos("El índice de vista está fuera de rango.")
    return (
        AAD_PREFIJO
        + str(boveda_id).encode("utf-8")
        + b"|"
        + bytes([indice_vista])
        + _COUNTER.pack(indice_chunk)
    )


# --- Cifrado de chunks ----------------------------------------------------
def cifrar_chunk(
    clave: bytes,
    iv_base: bytes,
    boveda_id: str,
    indice_vista: int,
    indice_chunk: int,
    datos: bytes,
    chunk_bytes: int,
) -> bytes:
    """Cifra un chunk y devuelve ``chunk_bytes + 16`` bytes.

    El plano se rellena con bytes aleatorios hasta ``chunk_bytes`` para que el
    tamaño real del archivo no se deduzca del tamaño del ciphertext.
    """

    if len(clave) != CLAVE_BYTES:
        raise ErrorAdjuntos("La clave de adjuntos debe tener 32 bytes.")
    if len(datos) > chunk_bytes:
        raise ErrorAdjuntos("El chunk excede el tamaño máximo configurado.")
    plano = bytes(datos) + os.urandom(chunk_bytes - len(datos))
    cifrado = AESGCM(clave).encrypt(
        nonce(iv_base, indice_chunk), plano, aad(boveda_id, indice_vista, indice_chunk)
    )
    return cifrado


def descifrar_chunk(
    clave: bytes,
    iv_base: bytes,
    boveda_id: str,
    indice_vista: int,
    indice_chunk: int,
    cifrado: bytes,
    chunk_bytes: int,
) -> bytes:
    """Descifra un chunk. Lanza :class:`ErrorAdjuntos` si el GCM no valida.

    Que la autenticación falle significa que el ciphertext fue alterado: es la
    señal de corrupción que se traduce en un 409 y una alerta crítica.
    """

    if len(clave) != CLAVE_BYTES:
        raise ErrorAdjuntos("La clave de adjuntos debe tener 32 bytes.")
    try:
        plano = AESGCM(clave).decrypt(
            nonce(iv_base, indice_chunk),
            cifrado,
            aad(boveda_id, indice_vista, indice_chunk),
        )
    except InvalidTag as exc:
        raise ErrorAdjuntos(
            "El chunk cifrado no supera la autenticación: el contenido fue alterado."
        ) from exc
    if len(plano) != chunk_bytes:
        raise ErrorAdjuntos("El chunk descifrado tiene un tamaño inesperado.")
    return plano


# --- Lectura y escritura del blob ----------------------------------------
def crear_blob_vacio(ruta: Path, segmento_bytes: int) -> None:
    """Crea el blob con los dos segmentos vacíos (solo relleno aleatorio)."""

    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    with temporal.open("wb") as destino:
        for _ in range(NUM_VISTAS):
            destino.write(os.urandom(segmento_bytes))
        destino.flush()
        os.fsync(destino.fileno())
    os.replace(temporal, ruta)


def _leer_segmento_exacto(ruta: Path, indice: int, segmento_bytes: int) -> bytes:
    """Lee un segmento; si el archivo está incompleto, rellena con aleatorio."""

    with ruta.open("rb") as origen:
        origen.seek(indice * segmento_bytes)
        datos = origen.read(segmento_bytes)
    if len(datos) < segmento_bytes:
        datos = datos + os.urandom(segmento_bytes - len(datos))
    return datos


def leer_segmento(ruta: Path, indice: int, segmento_bytes: int) -> bytes:
    """Lee el segmento ``indice`` del blob (bytes exactos)."""

    if not ruta.exists():
        raise ErrorAdjuntos("El archivo de adjuntos no está disponible.")
    return _leer_segmento_exacto(ruta, indice, segmento_bytes)


def actualizar_segmento(
    ruta: Path,
    indice_vista: int,
    segmento_bytes: int,
    slot_bytes_total: int,
    cambios: dict[int, bytes],
) -> None:
    """Escribe los *chunks* indicados en su slot y deja el resto intacto.

    El segmento contrario se copia byte a byte (no se re-cifra ni se re-genera:
    es byte a byte idéntico al que había). La escritura es atómica: se escribe
    en un temporal y se sustituye con ``os.replace``.
    """

    ruta.parent.mkdir(parents=True, exist_ok=True)
    temporal = ruta.with_name(ruta.name + ".tmp")
    existe = ruta.exists()
    with temporal.open("wb") as destino:
        for indice in range(NUM_VISTAS):
            if indice == indice_vista:
                base = bytearray(
                    _leer_segmento_exacto(ruta, indice, segmento_bytes)
                    if existe
                    else os.urandom(segmento_bytes)
                )
                for slot, datos in cambios.items():
                    inicio = slot * slot_bytes_total
                    if inicio + len(datos) > len(base):
                        raise ErrorAdjuntos("El slot queda fuera del segmento.")
                    base[inicio : inicio + len(datos)] = datos
                destino.write(base)
            elif existe:
                with ruta.open("rb") as origen:
                    origen.seek(indice * segmento_bytes)
                    restante = segmento_bytes
                    while restante > 0:
                        bloque = origen.read(min(1024 * 1024, restante))
                        if not bloque:
                            break
                        destino.write(bloque)
                        restante -= len(bloque)
                    if restante > 0:
                        destino.write(os.urandom(restante))
            else:
                destino.write(os.urandom(segmento_bytes))
        destino.flush()
        os.fsync(destino.fileno())
    os.replace(temporal, ruta)


def eliminar_blob(bovedas_dir: Path | str, boveda_id: str) -> None:
    """Borra el directorio de adjuntos de una bóveda (al eliminarla)."""

    import shutil

    directorio = Path(bovedas_dir) / str(boveda_id)
    if directorio.exists():
        shutil.rmtree(directorio, ignore_errors=True)
