"""Enumeraciones y constantes de dominio.

Se usan ``str, Enum`` para que Pydantic (JSON) las serialice por su valor
legible en lugar del nombre del miembro.
"""

from __future__ import annotations

from enum import Enum


class Rol(str, Enum):
    """Roles disponibles del sistema (Módulo 1)."""

    ADMIN = "admin"
    ABOGADO = "abogado"
    ASISTENTE = "asistente"


class EstadoExpediente(str, Enum):
    """Estados del ciclo de vida de un expediente (Módulo 2)."""

    ABIERTO = "abierto"
    EN_TRAMITE = "en_tramite"
    SUSPENDIDO = "suspendido"
    CERRADO = "cerrado"
    ARCHIVADO = "archivado"


class TipoProceso(str, Enum):
    """Tipos de proceso jurídico (Módulo 2)."""

    CIVIL = "civil"
    PENAL = "penal"
    LABORAL = "laboral"
    MERCANTIL = "mercantil"
    FAMILIA = "familia"
    ADMINISTRATIVO = "administrativo"
    OTRO = "otro"


class TipoDocumento(str, Enum):
    """Clasificación documental por tipo (Módulo 3)."""

    CONTRATO = "contrato"
    DEMANDA = "demanda"
    DECLARACION = "declaracion"
    PRUEBA = "prueba"
    PODER = "poder"
    RESOLUCION = "resolucion"
    OTRO = "otro"


class NivelSensibilidad(str, Enum):
    """Nivel de sensibilidad de un documento.

    ``CONFIDENCIAL`` restringe el acceso del rol ``ASISTENTE`` (mínimo
    privilegio, Módulos 3 y 5).
    """

    PUBLICO = "publico"
    INTERNO = "interno"
    CONFIDENCIAL = "confidencial"


class TipoAlerta(str, Enum):
    """Tipos de evento de seguridad registrados como alertas (Módulo 7)."""

    LOGIN_EXITOSO = "login_exitoso"
    LOGIN_FALLIDO = "login_fallido"
    CUENTA_BLOQUEADA = "cuenta_bloqueada"
    CUENTA_DESBLOQUEADA = "cuenta_desbloqueada"
    ACCESO_DENEGADO = "acceso_denegado"
    USUARIO_CREADO = "usuario_creado"
    USUARIO_EDITADO = "usuario_editado"
    USUARIO_DESACTIVADO = "usuario_desactivado"
    EXPEDIENTE_CREADO = "expediente_creado"
    EXPEDIENTE_EDITADO = "expediente_editado"
    EXPEDIENTE_ARCHIVADO = "expediente_archivado"
    DOCUMENTO_CARGADO = "documento_cargado"
    DOCUMENTO_DESCARGADO = "documento_descargado"
    DOCUMENTO_ELIMINADO = "documento_eliminado"


class SeveridadAlerta(str, Enum):
    """Severidad de una alerta, usada para priorizar su revisión (Módulo 7)."""

    INFO = "info"
    ADVERTENCIA = "advertencia"
    CRITICA = "critica"


# Roles con permiso para crear/gestionar expedientes (Módulos 2 y 5).
ROLES_GESTION_EXPEDIENTES = (Rol.ADMIN, Rol.ABOGADO)
