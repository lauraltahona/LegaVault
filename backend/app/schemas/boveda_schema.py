"""Esquemas de la bóveda cifrada de doble fondo (Módulo 4).

Importante: **ningún esquema de salida expone las vistas cifradas** ni
cualquier material criptográfico. La metainformación visible es solo la
necesaria para listar y describir la bóveda en la interfaz.

Desde la **Fase 6 (mejora M4.1)** la bóveda admite además **archivos
adjuntos** por fondo. Los esquemas de adjuntos exponen **solo metadatos**
(nombre, mime, tamaño, hash y posición): ni la clave de cifrado de los chunks
ni el contenido del archivo salen nunca del servidor.
"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class BovedaCreate(BaseModel):
    """Datos para crear una bóveda con sus dos contraseñas independientes."""

    nombre: str = Field(..., max_length=120)
    descripcion: str = ""
    expediente_id: str = ""
    password_visible: str = Field(..., min_length=1)
    password_confidencial: str = Field(..., min_length=1)
    contenido_visible: str = ""
    contenido_confidencial: str = ""
    # Cubeta de padding en MB (mejora #15). Si se omite se usa el valor
    # configurado; 0 desactiva el padding. No se expone en la respuesta.
    bucket_mb: int | None = Field(default=None, ge=0)
    # Capacidad de adjuntos **por fondo** en MB (Fase 6). Si se omite se usa el
    # valor configurado (5 MB). Admite la escalera 1 / 5 / 25 MB.
    adjuntos_mb: int | None = Field(default=None, ge=1)


class BovedaResponse(BaseModel):
    """Metadatos de una bóveda (nunca el contenido ni las vistas cifradas)."""

    model_config = ConfigDict(from_attributes=True)

    id: str
    nombre: str
    descripcion: str
    expediente_id: str
    creado_por_id: str
    activo: bool
    creado_en: datetime
    actualizado_en: datetime
    # Formato de la bóveda: 1 = heredado (solo texto), 2 = con adjuntos.
    # La interfaz lo usa para ofrecer la opción de modernizar.
    formato: int = 1

    # Campo enriquecido que se completa en el controlador.
    expediente_identificador: str | None = None


class DesbloqueoRequest(BaseModel):
    password: str = Field(..., min_length=1)


class EntradaResponse(BaseModel):
    id: str
    titulo: str
    contenido: str
    creado_en: str


class AdjuntoMetadata(BaseModel):
    """Metadatos de un adjunto (sin clave ni contenido)."""

    id: str
    nombre: str
    mime: str
    tamano_bytes: int
    sha256: str
    chunk_inicio: int
    chunks: int
    titulo: str = ""


class AdjuntoResponse(AdjuntoMetadata):
    """Adjunto recién subido (incluye la fecha de creación)."""

    creado_en: str


class VerificacionAdjuntoResponse(BaseModel):
    """Resultado de re-verificar la integridad de un adjunto."""

    id: str
    integro: bool
    checksum_esperado: str
    checksum_calculado: str | None = None
    tamano_esperado: int
    tamano_calculado: int | None = None
    verificado_en: str
    mensaje: str


class ContenidoResponse(BaseModel):
    """Contenido descifrado de una vista (solo tras desbloquear)."""

    entradas: list[EntradaResponse] = Field(default_factory=list)
    # Metadatos de los adjuntos de la vista abierta (vacío en las bóvedas v1).
    adjuntos: list[AdjuntoMetadata] = Field(default_factory=list)
    # Formato del contenido: 1 = heredado (solo texto), 2 = con adjuntos.
    version: int = 1


class EntradaCreate(BaseModel):
    titulo: str = Field(..., max_length=200)
    contenido: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class CredencialesRequest(BaseModel):
    password_actual: str = Field(..., min_length=1)
    password_nueva: str = Field(..., min_length=1)


class AdjuntoAccion(BaseModel):
    """Cuerpo de las acciones sobre un adjunto (descarga, verificación, borrado).

    La contraseña viaja en el **cuerpo** de la petición, nunca en la URL: en una
    query string acabaría en los registros del servidor y en la cabecera
    ``Referer`` (decisión D7 del spec de la Fase 6).
    """

    password: str = Field(..., min_length=1)


class ModernizarRequest(BaseModel):
    """Modernización de una bóveda v1 a v2 (pide las dos contraseñas)."""

    password_visible: str = Field(..., min_length=1)
    password_confidencial: str = Field(..., min_length=1)
