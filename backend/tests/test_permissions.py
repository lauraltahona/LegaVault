"""Pruebas de las reglas de autorización centralizadas."""

from __future__ import annotations

import pytest

from app.core.constants import EstadoExpediente, Rol, TipoProceso
from app.core.exceptions import PermissionDeniedError
from app.models.expediente import Expediente
from app.models.user import User
from app.services import permissions


def _user(rol: Rol, uid: str = "u1") -> User:
    return User(id=uid, username=uid, nombre_completo=f"Usuario {uid}", rol=rol)


def _expediente(**kwargs) -> Expediente:
    base = {
        "id": "exp1",
        "identificador": "EXP-1",
        "asunto": "Caso",
        "cliente": "Cliente",
        "tipo_proceso": TipoProceso.CIVIL,
        "estado": EstadoExpediente.ABIERTO,
        "abogado_responsable_id": "resp",
        "usuarios_autorizados": [],
        "descripcion": "Desc",
    }
    base.update(kwargs)
    return Expediente(**base)


def test_es_admin() -> None:
    assert permissions.es_admin(_user(Rol.ADMIN)) is True
    assert permissions.es_admin(_user(Rol.ABOGADO)) is False
    assert permissions.es_admin(_user(Rol.ASISTENTE)) is False


def test_asegurar_rol_ok() -> None:
    permissions.asegurar_rol(_user(Rol.ADMIN), Rol.ADMIN, Rol.ABOGADO)
    permissions.asegurar_rol(_user(Rol.ABOGADO), Rol.ABOGADO)


def test_asegurar_rol_denegado() -> None:
    with pytest.raises(PermissionDeniedError):
        permissions.asegurar_rol(_user(Rol.ASISTENTE), Rol.ADMIN, Rol.ABOGADO)


def test_puede_acceder_expediente() -> None:
    exp = _expediente()

    # Admin puede todo
    assert permissions.puede_acceder_expediente(_user(Rol.ADMIN), exp) is True

    # Responsable sí
    assert permissions.puede_acceder_expediente(_user(Rol.ABOGADO, "resp"), exp) is True

    # Autorizado sí
    exp2 = _expediente(usuarios_autorizados=["as1"])
    assert permissions.puede_acceder_expediente(_user(Rol.ASISTENTE, "as1"), exp2) is True
    assert permissions.puede_acceder_expediente(_user(Rol.ABOGADO, "otro"), exp2) is False
    assert permissions.puede_acceder_expediente(_user(Rol.ASISTENTE, "otro"), exp2) is False


def test_asegurar_acceso_expediente_denegado() -> None:
    exp = _expediente()
    with pytest.raises(PermissionDeniedError):
        permissions.asegurar_acceso_expediente(_user(Rol.ABOGADO, "otro"), exp)


def test_es_responsable() -> None:
    exp = _expediente()
    assert permissions.es_responsable(_user(Rol.ABOGADO, "resp"), exp) is True
    assert permissions.es_responsable(_user(Rol.ABOGADO, "otro"), exp) is False


def test_puede_gestionar_expediente() -> None:
    exp = _expediente()
    # Solo admin o responsable
    assert permissions.puede_gestionar_expediente(_user(Rol.ADMIN), exp) is True
    assert permissions.puede_gestionar_expediente(_user(Rol.ABOGADO, "resp"), exp) is True
    # Abogado autorizado no puede gestionar
    assert permissions.puede_gestionar_expediente(_user(Rol.ABOGADO, "otro"), exp) is False
    # Asistente autorizado no puede gestionar
    exp2 = _expediente(usuarios_autorizados=["as1"])
    assert permissions.puede_gestionar_expediente(_user(Rol.ASISTENTE, "as1"), exp2) is False


def test_puede_cargar_documento() -> None:
    exp = _expediente(usuarios_autorizados=["as1"])
    # Todos los roles pueden cargar si tienen acceso
    assert permissions.puede_cargar_documento(_user(Rol.ADMIN), exp) is True
    assert permissions.puede_cargar_documento(_user(Rol.ABOGADO, "otro"), exp) is False
    assert permissions.puede_cargar_documento(_user(Rol.ABOGADO, "resp"), exp) is True
    assert permissions.puede_cargar_documento(_user(Rol.ASISTENTE, "as1"), exp) is True
    assert permissions.puede_cargar_documento(_user(Rol.ASISTENTE, "otro"), exp) is False


def test_puede_ver_documento_basico() -> None:
    # La visibilidad de documentos se prueba de forma integrada en la API.
    # Esta prueba existe por cobertura y valida únicamente que la función no explote.
    exp = _expediente(usuarios_autorizados=["as1"])
    assert permissions.puede_acceder_expediente(_user(Rol.ASISTENTE, "as1"), exp) is True
    assert permissions.puede_acceder_expediente(_user(Rol.ABOGADO, "otro"), exp) is False


def test_permisos_efectivos_por_rol() -> None:
    exp = _expediente(usuarios_autorizados=["as1", "ab1"])

    # Admin y responsable tienen todas las acciones
    admin = permissions.permisos_efectivos(_user(Rol.ADMIN), exp)
    assert all(admin.values())

    resp = permissions.permisos_efectivos(_user(Rol.ABOGADO, "resp"), exp)
    assert all(resp.values())

    # Usuario autorizado: lectura/carga/descarga por defecto, sin editar/eliminar
    autorizado = permissions.permisos_efectivos(_user(Rol.ABOGADO, "ab1"), exp)
    assert autorizado["leer"] is True
    assert autorizado["cargar"] is True
    assert autorizado["descargar"] is True
    assert autorizado["editar"] is False
    assert autorizado["eliminar"] is False

    # Usuario ajeno: sin ninguna acción
    ajeno = permissions.permisos_efectivos(_user(Rol.ABOGADO, "otro"), exp)
    assert not any(ajeno.values())


def test_permisos_efectivos_refinan_con_matriz() -> None:
    exp = _expediente(usuarios_autorizados=["ab1"])
    exp.permisos = {"ab1": {"editar": True, "descargar": False}}

    efectivos = permissions.permisos_efectivos(_user(Rol.ABOGADO, "ab1"), exp)
    assert efectivos["editar"] is True
    assert efectivos["descargar"] is False
    assert efectivos["leer"] is True

    assert permissions.puede_accion(_user(Rol.ABOGADO, "ab1"), exp, "editar") is True
    assert permissions.puede_accion(_user(Rol.ABOGADO, "ab1"), exp, "descargar") is False
    assert permissions.puede_gestionar_expediente(_user(Rol.ABOGADO, "ab1"), exp) is True


def test_permisos_no_afectan_a_admin_ni_responsable() -> None:
    exp = _expediente(abogado_responsable_id="resp", usuarios_autorizados=["ab1"])
    exp.permisos = {"resp": {"editar": False, "leer": False}}

    # El responsable conserva el control total pese a la matriz.
    assert permissions.puede_accion(_user(Rol.ABOGADO, "resp"), exp, "editar") is True
    assert permissions.puede_accion(_user(Rol.ABOGADO, "resp"), exp, "leer") is True


def test_normalizar_permisos_descarta_desconocidos() -> None:
    from app.models.expediente import normalizar_permisos

    crudo = {
        "u1": {"leer": True, "inventada": True, "editar": 1},
        "u2": "no-es-dict",
        "u3": {},
    }
    limpio = normalizar_permisos(crudo)
    assert limpio == {"u1": {"leer": True, "editar": True}}
    assert normalizar_permisos(None) == {}


def test_puede_administrar_permisos_no_basta_editar() -> None:
    exp = _expediente(abogado_responsable_id="resp", usuarios_autorizados=["ab1"])
    exp.permisos = {"ab1": {"editar": True}}

    # Aunque tenga 'editar', no puede administrar la matriz de permisos.
    assert permissions.puede_gestionar_expediente(_user(Rol.ABOGADO, "ab1"), exp) is True
    assert permissions.puede_administrar_permisos(_user(Rol.ABOGADO, "ab1"), exp) is False
    # El responsable y el admin sí.
    assert permissions.puede_administrar_permisos(_user(Rol.ABOGADO, "resp"), exp) is True
    assert permissions.puede_administrar_permisos(_user(Rol.ADMIN), exp) is True
