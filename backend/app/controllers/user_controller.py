"""Controlador de gestión de usuarios (Módulo 1).

Las operaciones de administración exigen el rol ``admin``. El endpoint de
selección solo expone datos mínimos (id, usuario, nombre, rol) para que un
abogado pueda asignar responsables sin acceder a la información completa.
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query, status

from app.controllers.dependencies import require_admin, require_admin_or_abogado
from app.core.constants import Rol
from app.core.container import user_service
from app.models.user import User
from app.schemas.user_schema import (
    PasswordResetRequest,
    UsuarioResumen,
    UserCreate,
    UserEstadoRequest,
    UserResponse,
    UserUpdate,
)

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])


@router.get("", response_model=list[UserResponse], summary="Listar usuarios (admin)")
def listar(
    q: str | None = Query(None, description="Búsqueda por usuario, nombre o correo"),
    rol: Rol | None = None,
    activo: bool | None = None,
    _: User = Depends(require_admin),
) -> list[UserResponse]:
    usuarios = user_service().listar(q=q, rol=rol, activo=activo)
    return [UserResponse.model_validate(usuario) for usuario in usuarios]


@router.get(
    "/seleccion",
    response_model=list[UsuarioResumen],
    summary="Usuarios para selectores (admin y abogados)",
)
def seleccion(_: User = Depends(require_admin_or_abogado)) -> list[UsuarioResumen]:
    usuarios = user_service().listar(activo=True)
    return [UsuarioResumen.model_validate(usuario) for usuario in usuarios]


@router.post(
    "",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear usuario (admin)",
)
def crear(payload: UserCreate, admin: User = Depends(require_admin)) -> UserResponse:
    usuario = user_service().crear(payload.model_dump(), admin)
    return UserResponse.model_validate(usuario)


@router.get("/{user_id}", response_model=UserResponse, summary="Obtener usuario (admin)")
def obtener(user_id: str, _: User = Depends(require_admin)) -> UserResponse:
    return UserResponse.model_validate(user_service().obtener(user_id))


@router.put("/{user_id}", response_model=UserResponse, summary="Editar usuario (admin)")
def actualizar(
    user_id: str, payload: UserUpdate, admin: User = Depends(require_admin)
) -> UserResponse:
    usuario = user_service().actualizar(user_id, payload.model_dump(exclude_unset=True), admin)
    return UserResponse.model_validate(usuario)


@router.patch(
    "/{user_id}/estado",
    response_model=UserResponse,
    summary="Activar o desactivar usuario (admin)",
)
def cambiar_estado(
    user_id: str, payload: UserEstadoRequest, admin: User = Depends(require_admin)
) -> UserResponse:
    usuario = user_service().cambiar_estado(user_id, payload.activo, admin)
    return UserResponse.model_validate(usuario)


@router.post(
    "/{user_id}/password",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Restablecer contraseña (admin)",
)
def restablecer_password(
    user_id: str, payload: PasswordResetRequest, admin: User = Depends(require_admin)
) -> None:
    user_service().restablecer_password(user_id, payload.nueva_password, admin)


@router.post(
    "/{user_id}/desbloquear",
    response_model=UserResponse,
    summary="Desbloquear cuenta (admin)",
)
def desbloquear(user_id: str, admin: User = Depends(require_admin)) -> UserResponse:
    usuario = user_service().desbloquear(user_id, admin)
    return UserResponse.model_validate(usuario)
