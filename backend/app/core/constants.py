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
    DOCUMENTO_CORRUPO = "documento_corrupto"
    DOCUMENTO_RECHAZADO = "documento_rechazado"
    BOVEDA_CREADA = "boveda_creada"
    BOVEDA_ABIERTA = "boveda_abierta"
    BOVEDA_ACCESO_FALLIDO = "boveda_acceso_fallido"
    BOVEDA_EDITADA = "boveda_editada"
    BOVEDA_CREDENCIALES = "boveda_credenciales"
    BOVEDA_ELIMINADA = "boveda_eliminada"
    # Adjuntos de la bóveda (Módulo 4, mejora M4.1 / Fase 6).
    BOVEDA_ADJUNTO_CARGADO = "boveda_adjunto_cargado"
    BOVEDA_ADJUNTO_DESCARGADO = "boveda_adjunto_descargado"
    BOVEDA_ADJUNTO_ELIMINADO = "boveda_adjunto_eliminado"
    BOVEDA_ADJUNTO_CORRUPTO = "boveda_adjunto_corrupto"
    BOVEDA_ADJUNTO_RECHAZADO = "boveda_adjunto_rechazado"
    # Generada por el servicio de correlación (Módulo 7, mejora #13): resume
    # un patrón sospechoso detectado al analizar varias alertas en conjunto.
    PATRON_SOSPECHOSO = "patron_sospechoso"


class SeveridadAlerta(str, Enum):
    """Severidad de una alerta, usada para priorizar su revisión (Módulo 7)."""

    INFO = "info"
    ADVERTENCIA = "advertencia"
    CRITICA = "critica"


class ResultadoAuditoria(str, Enum):
    """Resultado de una acción registrada en la auditoría (Módulo 6)."""

    OK = "ok"
    DENEGADO = "denegado"
    ERROR = "error"


class AccionAuditoria(str, Enum):
    """Acciones auditables del sistema (Módulo 6).

    A diferencia de :class:`TipoAlerta` (que alimenta el panel de seguridad), la
    auditoría registra **todas** las acciones relevantes, incluidas las lecturas
    sensibles y los intentos denegados.
    """

    LOGIN = "login"
    LOGIN_FALLIDO = "login_fallido"
    LOGOUT = "logout"
    CUENTA_BLOQUEADA = "cuenta_bloqueada"
    ACCESO_DENEGADO = "acceso_denegado"
    USUARIO_CREADO = "usuario_creado"
    USUARIO_EDITADO = "usuario_editado"
    USUARIO_ESTADO = "usuario_estado"
    USUARIO_PASSWORD = "usuario_password"
    USUARIO_DESBLOQUEADO = "usuario_desbloqueado"
    EXPEDIENTE_CREADO = "expediente_creado"
    EXPEDIENTE_EDITADO = "expediente_editado"
    EXPEDIENTE_ARCHIVADO = "expediente_archivado"
    DOCUMENTO_CARGADO = "documento_cargado"
    DOCUMENTO_DESCARGADO = "documento_descargado"
    DOCUMENTO_ELIMINADO = "documento_eliminado"
    DOCUMENTO_VERIFICADO = "documento_verificado"
    DOCUMENTO_CORRUPO = "documento_corrupto"
    DOCUMENTO_RECHAZADO = "documento_rechazado"
    BOVEDA_CREADA = "boveda_creada"
    BOVEDA_ABIERTA = "boveda_abierta"
    BOVEDA_ACCESO_FALLIDO = "boveda_acceso_fallido"
    BOVEDA_EDITADA = "boveda_editada"
    BOVEDA_CREDENCIALES = "boveda_credenciales"
    BOVEDA_ELIMINADA = "boveda_eliminada"
    BOVEDA_ADJUNTO_CARGADO = "boveda_adjunto_cargado"
    BOVEDA_ADJUNTO_DESCARGADO = "boveda_adjunto_descargado"
    BOVEDA_ADJUNTO_ELIMINADO = "boveda_adjunto_eliminado"
    BOVEDA_ADJUNTO_CORRUPTO = "boveda_adjunto_corrupto"
    BOVEDA_ADJUNTO_RECHAZADO = "boveda_adjunto_rechazado"
    EXPEDIENTE_PERMISOS = "expediente_permisos"
    AUDITORIA_VERIFICADA = "auditoria_verificada"


# Roles con permiso para crear/gestionar expedientes (Módulos 2 y 5).
ROLES_GESTION_EXPEDIENTES = (Rol.ADMIN, Rol.ABOGADO)

# Roles con permiso para cargar documentos (Módulo 3). El asistente puede cargar
# documentos no confidenciales en expedientes a los que tiene acceso.
ROLES_CARGA_DOCUMENTOS = (Rol.ADMIN, Rol.ABOGADO, Rol.ASISTENTE)

# Acciones contempladas por la matriz de permisos granular por expediente (Módulo 5).
# El orden se usa en la interfaz de administración de permisos.
ACCIONES_PERMISO = ("leer", "cargar", "descargar", "editar", "eliminar")

# Roles con permiso para crear bóvedas cifradas (Módulo 4).
ROLES_GESTION_BOVEDA = (Rol.ADMIN, Rol.ABOGADO)
