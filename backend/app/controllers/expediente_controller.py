"""Controlador de expedientes (Módulo 2)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.controllers.dependencies import get_current_user
from app.core.constants import EstadoExpediente, TipoProceso
from app.core.container import documento_repository, expediente_service, user_repository
from app.models.expediente import Expediente
from app.models.user import User
from app.schemas.expediente_schema import (
    ExpedienteCreate,
    ExpedienteResponse,
    ExpedienteUpdate,
    PermisosUpdate,
)

router = APIRouter(prefix="/expedientes", tags=["Expedientes"])


def _to_response(exp: Expediente) -> ExpedienteResponse:
    """Enriquece la respuesta con datos legibles para la interfaz."""

    respuesta = ExpedienteResponse.model_validate(exp)
    responsable = user_repository().get(exp.abogado_responsable_id)
    respuesta.abogado_responsable_nombre = responsable.nombre_completo if responsable else None
    respuesta.total_documentos = documento_repository().count_by_expediente(exp.id)
    return respuesta


@router.get("", response_model=list[ExpedienteResponse], summary="Listar / buscar expedientes")
def listar(
    q: str | None = None,
    estado: EstadoExpediente | None = None,
    tipo_proceso: TipoProceso | None = None,
    abogado_id: str | None = None,
    usuario: User = Depends(get_current_user),
) -> list[ExpedienteResponse]:
    expedientes = expediente_service().listar(
        usuario, q=q, estado=estado, tipo_proceso=tipo_proceso, abogado_id=abogado_id
    )
    return [_to_response(exp) for exp in expedientes]


@router.post(
    "",
    response_model=ExpedienteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear expediente",
)
def crear(payload: ExpedienteCreate, usuario: User = Depends(get_current_user)) -> ExpedienteResponse:
    exp = expediente_service().crear(payload.model_dump(), usuario)
    return _to_response(exp)


@router.get("/{expediente_id}", response_model=ExpedienteResponse, summary="Obtener expediente")
def obtener(expediente_id: str, usuario: User = Depends(get_current_user)) -> ExpedienteResponse:
    return _to_response(expediente_service().obtener(expediente_id, usuario))


@router.put("/{expediente_id}", response_model=ExpedienteResponse, summary="Editar expediente")
def actualizar(
    expediente_id: str, payload: ExpedienteUpdate, usuario: User = Depends(get_current_user)
) -> ExpedienteResponse:
    exp = expediente_service().actualizar(
        expediente_id, payload.model_dump(exclude_unset=True), usuario
    )
    return _to_response(exp)


@router.patch(
    "/{expediente_id}/archivar",
    response_model=ExpedienteResponse,
    summary="Archivar expediente",
)
def archivar(expediente_id: str, usuario: User = Depends(get_current_user)) -> ExpedienteResponse:
    return _to_response(expediente_service().archivar(expediente_id, usuario))


@router.put(
    "/{expediente_id}/permisos",
    response_model=ExpedienteResponse,
    summary="Actualizar la matriz de permisos del expediente (solo admin/responsable)",
)
def actualizar_permisos(
    expediente_id: str, payload: PermisosUpdate, usuario: User = Depends(get_current_user)
) -> ExpedienteResponse:
    exp = expediente_service().actualizar_permisos(expediente_id, payload.permisos, usuario)
    return _to_response(exp)
