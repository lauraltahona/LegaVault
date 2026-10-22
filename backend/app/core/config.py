"""Configuración central de la aplicación.

Los parámetros sensibles o ajustables se leen de variables de entorno con
valores por defecto válidos para un entorno académico/de desarrollo. Nunca
deben usarse los valores por defecto en producción.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

# backend/  (este archivo vive en backend/app/core/config.py)
BACKEND_DIR = Path(__file__).resolve().parents[2]
DEFAULT_DATA_DIR = BACKEND_DIR / "data"


def _env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def _env_extensiones(name: str) -> tuple[str, ...] | None:
    """Lee una lista blanca de extensiones separadas por comas (Módulo 3).

    Acepta ``.pdf,png`` o ``.pdf, .png``; se normaliza a minúsculas con punto.
    Devuelve ``None`` si la variable no está definida para usar el valor por
    defecto de ``magic_bytes`` (fuente única de verdad).
    """

    valor = os.getenv(name, "")
    if not valor.strip():
        return None
    extensiones: list[str] = []
    for parte in valor.split(","):
        ext = parte.strip().lower()
        if not ext:
            continue
        extensiones.append(ext if ext.startswith(".") else f".{ext}")
    return tuple(extensiones) or None


def _extensiones_archivo_por_defecto() -> tuple[str, ...]:
    # Import perezoso para evitar un ciclo config <-> magic_bytes.
    from app.core.magic_bytes import EXTENSIONES_POR_DEFECTO

    return EXTENSIONES_POR_DEFECTO


@dataclass(frozen=True)
class Settings:
    """Parámetros de configuración de LegalVault."""

    app_name: str = "LegalVault API"
    version: str = "1.0.0"
    api_prefix: str = "/api"

    # Persistencia local (JSON) mientras no se use una base de datos real.
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("LEGALVAULT_DATA_DIR", str(DEFAULT_DATA_DIR)))
    )

    # --- Seguridad de cuentas (Módulos 1 y 7) ---
    max_intentos_fallidos: int = field(default_factory=lambda: _env_int("LEGALVAULT_MAX_INTENTOS", 5))
    minutos_bloqueo: int = field(default_factory=lambda: _env_int("LEGALVAULT_MINUTOS_BLOQUEO", 15))

    # --- Tokens de sesión (Módulo 1) ---
    secret_key: str = field(
        default_factory=lambda: os.getenv("LEGALVAULT_SECRET_KEY", "dev-secret-cambiar-en-produccion")
    )
    algorithm: str = "HS256"
    minutos_expiracion_token: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_MINUTOS_TOKEN", 60)
    )

    # --- CORS para el frontend (React/Vite) ---
    cors_origins: tuple[str, ...] = (
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    )

    # --- Documentos (Módulo 3) ---
    max_tamano_archivo_mb: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_MAX_ARCHIVO_MB", 25)
    )

    # Lista blanca de extensiones admitidas al subir (validación por magic bytes).
    # Por defecto: txt, csv, png, jpg/jpeg, pdf y zip (el seed sube .txt).
    extensiones_archivo_permitidas: tuple[str, ...] = field(
        default_factory=lambda: _env_extensiones("LEGALVAULT_EXTENSIONES_PERMITIDAS")
        or _extensiones_archivo_por_defecto()
    )

    @property
    def max_tamano_archivo_bytes(self) -> int:
        return self.max_tamano_archivo_mb * 1024 * 1024

    # --- Bóveda cifrada (Módulo 4, mejora #15) ---
    # Tamaño de la cubeta de padding. Todas las vistas de una bóveda usan la
    # misma cubeta para no filtrar información por el tamaño del contenido.
    boveda_bucket_mb: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_BOVEDA_BUCKET_MB", 1)
    )

    # --- Bóveda cifrada: adjuntos (Módulo 4, mejora M4.1 / Fase 6) ---
    # Capacidad de adjuntos **por fondo** (cada vista de la bóveda tiene la
    # suya). Define el tamaño del blob `data/bovedas/{id}/adjuntos.bin`, que
    # es SIEMPRE el doble del segmento de un fondo (2 x segmento_bytes), con
    # independencia del contenido: así el tamaño en disco no delata nada.
    boveda_adjuntos_mb: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_BOVEDA_ADJUNTOS_MB", 5)
    )

    # Tamaño máximo del chunk en que se cifra cada archivo dentro del blob.
    # El tamaño efectivo nunca supera la capacidad menos la etiqueta GCM, de
    # modo que la capacidad mínima (1 MB) siempre admita al menos un slot.
    boveda_chunk_kb: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_BOVEDA_CHUNK_KB", 1024)
    )

    # --- Reglas de correlación de alertas (Módulo 7, mejora #13) ---
    # Umbrales del servicio que detecta patrones sospechosos analizando
    # varias alertas en conjunto (detección básica de anomalías, estilo SIEM).
    corr_denegados_umbral: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_CORR_DENEGADOS_UMBRAL", 3)
    )
    corr_denegados_minutos: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_CORR_DENEGADOS_MINUTOS", 5)
    )
    corr_descargas_umbral: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_CORR_DESCARGAS_UMBRAL", 10)
    )
    corr_descargas_segundos: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_CORR_DESCARGAS_SEGUNDOS", 60)
    )
    corr_ip_cooldown_minutos: int = field(
        default_factory=lambda: _env_int("LEGALVAULT_CORR_IP_COOLDOWN_MINUTOS", 60)
    )

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def bovedas_dir(self) -> Path:
        """Directorio de los blobs de adjuntos de las bóvedas (Fase 6)."""

        return self.data_dir / "bovedas"

    def ensure_directories(self) -> None:
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.uploads_dir.mkdir(parents=True, exist_ok=True)
        self.bovedas_dir.mkdir(parents=True, exist_ok=True)


settings = Settings()
