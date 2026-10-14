"""Reglas de autorización centralizadas (Módulos 2, 3 y 5).

La comprobación de permisos ocurre siempre en el servidor; la interfaz solo
oculta acciones como ayuda visual, nunca como control de seguridad.
"""

from __future__ import annotations

from app.core.constants import NivelSensibilidad, Rol
from app.core.exceptions import PermissionDeniedError
from app.models.documento import Documento
from app.models.expediente import Expediente
from app.models.user import User


def es_admin(user: User) -> bool:
    return user.rol == Rol.ADMIN


def asegurar_rol(user: User, *roles: Rol) -> None:
    if user.rol not in roles:
        raise PermissionDeniedError("Su rol no permite realizar esta acción.")


def puede_acceder_expediente(user: User, expediente: Expediente) -> bool:
    """Un admin accede a todo; el resto solo a expedientes donde participa."""

    if es_admin(user):
        return True
    return (
        expediente.abogado_responsable_id == user.id
        or user.id in expediente.usuarios_autorizados
    )


def asegurar_acceso_expediente(user: User, expediente: Expediente) -> None:
    if not puede_acceder_expediente(user, expediente):
        raise PermissionDeniedError("No tiene permisos para acceder a este expediente.")


def puede_ver_documento(user: User, documento: Documento, expediente: Expediente) -> bool:
    """Mínimo privilegio: el asistente no accede a documentos confidenciales."""

    if es_admin(user):
        return True
    if not puede_acceder_expediente(user, expediente):
        return False
    if user.rol == Rol.ASISTENTE and documento.nivel_sensibilidad == NivelSensibilidad.CONFIDENCIAL:
        return False
    return True


def asegurar_ver_documento(user: User, documento: Documento, expediente: Expediente) -> None:
    if not puede_ver_documento(user, documento, expediente):
        raise PermissionDeniedError("No tiene permisos para acceder a este documento.")
