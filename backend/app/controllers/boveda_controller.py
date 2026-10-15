"""Controlador de la bóveda cifrada de doble fondo (Módulo 4)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.controllers.dependencies import get_current_user
from app.core.container import boveda_service, expediente_repository
from app.models.boveda import Boveda
from app.models.user import User
from app.schemas.boveda_schema import (
    BovedaCreate,
    BovedaResponse,
    ContenidoResponse,
    CredencialesRequest,
    DesbloqueoRequest,
    EntradaCreate,
    EntradaResponse,
)

router = APIRouter(prefix="/bovedas", tags=["Bóveda cifrada"])


def _to_response(boveda: Boveda) -> BovedaResponse:
    respuesta = BovedaResponse.model_validate(boveda)
    if boveda.expediente_id:
        expediente = expediente_repository().get(boveda.expediente_id)
        respuesta.expediente_identificador = expediente.identificador if expediente else None
    return respuesta


@router.get("", response_model=list[BovedaResponse], summary="Listar bóvedas accesibles")
def listar(usuario: User = Depends(get_current_user)) -> list[BovedaResponse]:
    return [_to_response(boveda) for boveda in boveda_service().listar(usuario)]


@router.post(
    "",
    response_model=BovedaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Crear bóveda de doble fondo",
)
def crear(payload: BovedaCreate, usuario: User = Depends(get_current_user)) -> BovedaResponse:
    boveda = boveda_service().crear(payload.model_dump(), usuario)
    return _to_response(boveda)


@router.get("/{boveda_id}", response_model=BovedaResponse, summary="Obtener metadatos de bóveda")
def obtener(boveda_id: str, usuario: User = Depends(get_current_user)) -> BovedaResponse:
    return _to_response(boveda_service().obtener(boveda_id, usuario))


@router.post(
    "/{boveda_id}/desbloquear",
    response_model=ContenidoResponse,
    summary="Desbloquear una vista con su contraseña",
)
def desbloquear(
    boveda_id: str,
    payload: DesbloqueoRequest,
    usuario: User = Depends(get_current_user),
) -> ContenidoResponse:
    contenido = boveda_service().desbloquear(boveda_id, payload.password, usuario)
    return ContenidoResponse.model_validate(contenido)


@router.post(
    "/{boveda_id}/entradas",
    response_model=EntradaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Añadir una entrada a la vista desbloqueada",
)
def agregar_entrada(
    boveda_id: str,
    payload: EntradaCreate,
    usuario: User = Depends(get_current_user),
) -> EntradaResponse:
    entrada = boveda_service().agregar_entrada(
        boveda_id, payload.password, payload.model_dump(), usuario
    )
    return EntradaResponse.model_validate(entrada)


@router.put(
    "/{boveda_id}/credenciales",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cambiar la contraseña de una vista",
)
def cambiar_credenciales(
    boveda_id: str,
    payload: CredencialesRequest,
    usuario: User = Depends(get_current_user),
) -> None:
    boveda_service().cambiar_credenciales(
        boveda_id, payload.password_actual, payload.password_nueva, usuario
    )


@router.delete(
    "/{boveda_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar bóveda",
)
def eliminar(boveda_id: str, usuario: User = Depends(get_current_user)) -> None:
    boveda_service().eliminar(boveda_id, usuario)
