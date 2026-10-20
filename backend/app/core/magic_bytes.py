"""Validación del tipo real de archivo por *magic bytes* (Módulo 3, mejora #4).

La extensión de un archivo es solo un texto que controla quien lo sube; fiarse
de ella (o del ``Content-Type`` del navegador) es un clásico de vulnerabilidades
— la forma más simple de evadir una lista negra es renombrar ``malware.exe`` a
``contrato.pdf``. Aquí el tipo real se determina **leyendo los primeros bytes
del contenido**:

- **Formatos binarios con firma conocida:** PDF (``%PDF-``), PNG
  (``\\x89PNG\\r\\n\\x1a\\n``), JPEG (``\\xFF\\xD8\\xFF``) y ZIP (``PK\\x03\\x04``,
  incluyendo los archivos vacíos ``PK\\x05\\x06``).
- **Texto plano (``.txt``/``.csv``):** no llevan firma binaria, así que se
  exige que la muestra sea texto decodificable (UTF-8, con o sin BOM) y sin
  bytes nulos ni caracteres de control inesperados.

Lista blanca de extensiones configurable con la variable de entorno
``LEGALVAULT_EXTENSIONES_PERMITIDAS`` (separada por comas). Sin dependencias
externas: solo la stdlib, como exige el plan del proyecto.

Educación por los bordes: los mensajes de rechazo explican **por qué** se
rechazó y qué son los magic bytes; nunca incluyen el contenido del archivo
(regla innegociable: nada de datos sensibles en errores, alertas o auditoría).
"""

from __future__ import annotations

from pathlib import Path

from app.core.exceptions import ValidationError

# Tamaño de la muestra analizada: los magic bytes viven al principio; 8 KB son
# suficientes para el encabezado y para una heurística de texto robusta.
MUESTRA_BYTES = 8192

# Firmas magicas: formato detectado -> prefijos que lo identifican.
_FIRMAS: dict[str, tuple[bytes, ...]] = {
    "pdf": (b"%PDF-",),
    "png": (b"\x89PNG\r\n\x1a\n",),
    "jpg": (b"\xff\xd8\xff",),
    "zip": (b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08"),
}

# Extensiones admitidas -> formato esperado del contenido. ``texto`` marca los
# formatos sin firma binaria (.txt y .csv comparten heurística de texto plano).
EXTENSIONES_POR_FORMATO: dict[str, str] = {
    ".txt": "texto",
    ".csv": "texto",
    ".png": "png",
    ".jpg": "jpg",
    ".jpeg": "jpg",
    ".pdf": "pdf",
    ".zip": "zip",
}

# Lista blanca por defecto (la config puede ampliarla/reducirla por entorno).
EXTENSIONES_POR_DEFECTO: tuple[str, ...] = tuple(EXTENSIONES_POR_FORMATO)

# Nombre legible de cada formato, para mensajes educativos.
FORMATOS_LEGIBLES: dict[str, str] = {
    "pdf": "PDF",
    "png": "PNG",
    "jpg": "JPEG",
    "zip": "ZIP",
    "texto": "texto plano",
}

# Firmas de binarios peligrosos/-desconocidos: solo para explicar el rechazo.
_BINARIOS_SOSPECHOSOS: tuple[tuple[bytes, str], ...] = (
    (b"MZ", "un ejecutable de Windows"),
    (b"\x7fELF", "un ejecutable de Linux (ELF)"),
    (b"\xca\xfe\xba\xbe", "un binario Java/Mach-O"),
)


def detectar_formato(contenido: bytes) -> str | None:
    """Devuelve el formato real (``pdf``/``png``/``jpg``/``zip``/``texto``) o ``None``."""

    muestra = contenido[:MUESTRA_BYTES]
    for formato, firmas in _FIRMAS.items():
        if any(muestra.startswith(firma) for firma in firmas):
            return formato
    if es_texto_plano(muestra):
        return "texto"
    return None


def es_texto_plano(muestra: bytes) -> bool:
    """Heurística para ``.txt``/``.csv``: UTF-8 válido, sin NUL ni controles raros."""

    if not muestra:
        return False
    if muestra.startswith(b"\xef\xbb\xbf"):  # BOM UTF-8 (Excel lo pone en los CSV)
        muestra = muestra[3:]
    if b"\x00" in muestra:
        return False
    texto = _decodificar_utf8(muestra)
    if texto is None:
        return False
    return not any(ord(caracter) < 32 and caracter not in "\t\n\r" for caracter in texto)


def _decodificar_utf8(muestra: bytes) -> str | None:
    """Decodifica la muestra tolerando **solo** un carácter multibyte truncado.

    Un CSV UTF-8 puede terminar justo en la mitad de una ``ñ`` (2–4 bytes) por
    el límite de ``MUESTRA_BYTES``: eso se acepta. Los bytes inválidos en medio
    del contenido (p. ej. Latin-1 mal codificado) **no** se toleran: recortar
    bytes del final para "arreglarlo" ocultaría contenido binario real, así que
    la cola final solo se acepta si es un prefijo plausible de una secuencia
    UTF-8 de 2–4 bytes (cabecera seguida de bytes de continuación).
    """

    try:
        return muestra.decode("utf-8")
    except UnicodeDecodeError as exc:
        cola = muestra[exc.start :]
        if not cola or len(cola) > 4:
            return None
        cabecera = cola[0]
        if 0xC2 <= cabecera <= 0xDF:
            longitud_esperada = 2
        elif 0xE0 <= cabecera <= 0xEF:
            longitud_esperada = 3
        elif 0xF0 <= cabecera <= 0xF4:
            longitud_esperada = 4
        else:
            return None  # cabecera inválida o byte de continuación huérfano
        if len(cola) >= longitud_esperada:
            return None  # no está truncado: los bytes son inválidos de verdad
        if any(not (0x80 <= byte <= 0xBF) for byte in cola[1:]):
            return None  # la "cola" no son bytes de continuación
        # El prefijo ya es UTF-8 válido: el decodificador falla en el primer
        # byte incorrecto, así que [:exc.start] siempre decodifica limpio.
        return muestra[: exc.start].decode("utf-8")


def describir_binario(muestra: bytes) -> str | None:
    """Si la muestra parece un binario conocido, devuelve una descripción."""

    for prefijo, descripcion in _BINARIOS_SOSPECHOSOS:
        if muestra.startswith(prefijo):
            return descripcion
    return None


def validar_tipo_archivo(
    nombre_original: str,
    contenido: bytes,
    *,
    extensiones_permitidas: tuple[str, ...] | list[str] | None = None,
) -> str:
    """Valida que la extensión esté en la lista blanca y **coincida** con el contenido.

    Devuelve el formato detectado (``pdf``, ``png``, ``jpg``, ``zip`` o
    ``texto``). Lanza :class:`ValidationError` (HTTP 422 en la API) si:

    1. El archivo no tiene extensión o esta no está en la lista blanca, o
    2. los magic bytes no corresponden al formato que promete la extensión.

    Una extensión admitida por configuración pero sin regla de contenido
    (p. ej. ``.docx`` añadida por entorno) solo exige que el archivo no sea
    un binario desconocido.
    """

    extensiones = {
        ext.lower() if ext.startswith(".") else f".{ext}".lower()
        for ext in (extensiones_permitidas or EXTENSIONES_POR_DEFECTO)
    }
    base = Path(str(nombre_original or "")).name
    extension = Path(base).suffix.lower()

    if not extension:
        raise ValidationError(
            "El archivo no tiene extensión: no se puede validar su tipo por magic bytes. "
            f"Extensiones admitidas: {_listado(extensiones)}."
        )
    if extension not in extensiones:
        raise ValidationError(
            f"Tipo de archivo no permitido ('{extension}'). "
            f"Extensiones admitidas: {_listado(extensiones)}."
        )

    muestra = contenido[:MUESTRA_BYTES]
    formato = detectar_formato(contenido)
    esperado = EXTENSIONES_POR_FORMATO.get(extension)

    if esperado is None:
        # Extensión habilitada por configuración sin regla asociada.
        if formato is None:
            raise ValidationError(
                f"El contenido de '{base}' no parece un archivo válido para '{extension}': "
                "los magic bytes no corresponden a ningún formato admitido."
            )
        return formato

    if formato == esperado:
        return formato

    if formato is None:
        sospechoso = describir_binario(muestra)
        if sospechoso:
            raise ValidationError(
                f"El contenido de '{base}' no coincide con su extensión '{extension}': "
                f"los magic bytes corresponden a {sospechoso}, no a "
                f"{FORMATOS_LEGIBLES[esperado]}. Validación por magic bytes: el tipo "
                "real lo determina el contenido, no el nombre del archivo."
            )
        raise ValidationError(
            f"El contenido de '{base}' no coincide con su extensión '{extension}': "
            "no es texto plano ni contiene la firma del formato que promete. "
            "Validación por magic bytes: el tipo real lo determina el contenido, "
            "no el nombre del archivo."
        )

    raise ValidationError(
        f"El contenido de '{base}' no coincide con su extensión '{extension}': "
        f"los magic bytes corresponden a {FORMATOS_LEGIBLES[formato]}, no a "
        f"{FORMATOS_LEGIBLES[esperado]}. Validación por magic bytes: el tipo real "
        "lo determina el contenido, no el nombre del archivo."
    )


def _listado(extensiones: set[str]) -> str:
    return ", ".join(sorted(extensiones))
