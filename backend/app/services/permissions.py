"""Reglas de autorización centralizadas (Módulos 2, 3 y 5).

La comprobación de permisos ocurre siempre en el servidor; la interfaz solo
oculta acciones como ayuda visual, nunca como control de seguridad.

Modelo de permisos (Módulo 5): cada expediente puede guardar una matriz
``{usuario_id: {accion: bool}}`` que **refina** los permisos por defecto,
derivados del rol y del acceso base (responsable o usuario autorizado).
El administrador y el abogado responsable conservan siempre el control total.
"""

from __future__ import annotations

from app.core.constants import (
    ACCIONES_PERMISO,
    ROLES_CARGA_DOCUMENTOS,
    NivelSensibilidad,
    Rol,
)
from app.core.exceptions import PermissionDeniedError
from app.models.documento import Documento
from app.models.expediente import Expediente
from app.models.user import User


def es_admin(user: User) -> bool:
    return user.rol == Rol.ADMIN


def asegurar_rol(user: User, *roles: Rol) -> None:
    if user.rol not in roles:
        raise PermissionDeniedError("Su rol no permite realizar esta acción.")


def es_responsable(user: User, expediente: Expediente) -> bool:
    """Indica si el usuario es el abogado responsable del expediente."""

    return expediente.abogado_responsable_id == user.id


def permisos_efectivos(user: User, expediente: Expediente) -> dict[str, bool]:
    """Calcula la matriz efectiva de acciones del usuario sobre el expediente.

    - El administrador y el responsable tienen todas las acciones.
    - Un usuario autorizado recibe por defecto ``leer``/``cargar``/``descargar``.
    - La matriz almacenada en el expediente puede conceder o revocar acciones
      (los valores explícitos tienen prioridad sobre los de por defecto).
    """

    if es_admin(user) or es_responsable(user, expediente):
        return {accion: True for accion in ACCIONES_PERMISO}

    acceso = user.id in expediente.usuarios_autorizados
    efectivos = {
        "leer": acceso,
        "cargar": acceso,
        "descargar": acceso,
        "editar": False,
        "eliminar": False,
    }
    for accion, valor in (expediente.permisos.get(user.id) or {}).items():
        if accion in efectivos:
            efectivos[accion] = bool(valor)
    return efectivos


def puede_accion(user: User, expediente: Expediente, accion: str) -> bool:
    return permisos_efectivos(user, expediente).get(accion, False)


def puede_acceder_expediente(user: User, expediente: Expediente) -> bool:
    """Un admin accede a todo; el resto solo si la matriz concede ``leer``."""

    return puede_accion(user, expediente, "leer")


def asegurar_acceso_expediente(user: User, expediente: Expediente) -> None:
    if not puede_acceder_expediente(user, expediente):
        raise PermissionDeniedError("No tiene permisos para acceder a este expediente.")


def asegurar_accion(user: User, expediente: Expediente, accion: str) -> None:
    if not puede_accion(user, expediente, accion):
        raise PermissionDeniedError("No tiene permisos para realizar esta acción.")


def puede_gestionar_expediente(user: User, expediente: Expediente) -> bool:
    """Editar o archivar el expediente (admin, responsable o permiso ``editar``)."""

    return puede_accion(user, expediente, "editar")


def puede_administrar_permisos(user: User, expediente: Expediente) -> bool:
    """Administrar la matriz de permisos: solo admin o abogado responsable.

    No basta con tener la acción ``editar`` concedida, para evitar que un
    usuario pueda elevar sus propios privilegios.
    """

    return es_admin(user) or es_responsable(user, expediente)


def puede_cargar_documento(user: User, expediente: Expediente) -> bool:
    """Rol con permiso de carga (Módulo 3) y acción ``cargar`` concedida."""

    return user.rol in ROLES_CARGA_DOCUMENTOS and puede_accion(user, expediente, "cargar")


def _nivel_permitido(user: User, documento: Documento) -> bool:
    """Mínimo privilegio: el asistente no accede a documentos confidenciales."""

    if user.rol == Rol.ASISTENTE and documento.nivel_sensibilidad == NivelSensibilidad.CONFIDENCIAL:
        return False
    return True


def puede_leer_documento(user: User, documento: Documento, expediente: Expediente) -> bool:
    return es_admin(user) or (
        puede_accion(user, expediente, "leer") and _nivel_permitido(user, documento)
    )


def puede_descargar_documento(user: User, documento: Documento, expediente: Expediente) -> bool:
    return es_admin(user) or (
        puede_accion(user, expediente, "descargar") and _nivel_permitido(user, documento)
    )


def puede_eliminar_documento(user: User, documento: Documento, expediente: Expediente) -> bool:
    """Puede eliminar el autor del documento, un admin o quien tenga ``eliminar``."""

    return (
        es_admin(user)
        or documento.subido_por_id == user.id
        or puede_accion(user, expediente, "eliminar")
    )


def asegurar_leer_documento(user: User, documento: Documento, expediente: Expediente) -> None:
    if not puede_leer_documento(user, documento, expediente):
        raise PermissionDeniedError("No tiene permisos para acceder a este documento.")


def asegurar_descargar_documento(user: User, documento: Documento, expediente: Expediente) -> None:
    if not puede_descargar_documento(user, documento, expediente):
        raise PermissionDeniedError("No tiene permisos para descargar este documento.")


def asegurar_eliminar_documento(user: User, documento: Documento, expediente: Expediente) -> None:
    if not puede_eliminar_documento(user, documento, expediente):
        raise PermissionDeniedError(
            "Solo el autor del documento, un administrador o quien tenga permiso de "
            "eliminación pueden borrarlo."
        )
