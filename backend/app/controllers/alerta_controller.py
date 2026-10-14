"""Controlador de alertas de seguridad (Módulo 7). Solo administradores."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.controllers.dependencies import require_admin
from app.core.constants import SeveridadAlerta, TipoAlerta
from app.core.container import alerta_service
from app.schemas.alerta_schema import AlertaResponse, AlertaResumen, MarcarLeidaRequest

router = APIRouter(
    prefix="/alertas",
    tags=["Alertas de seguridad"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[AlertaResponse], summary="Consultar alertas")
def listar(
    tipo: TipoAlerta | None = None,
    severidad: SeveridadAlerta | None = None,
    usuario: str | None = Query(None, description="Filtra por nombre de usuario (parcial)"),
    desde: datetime | None = None,
    hasta: datetime | None = None,
    solo_no_leidas: bool = False,
    limite: int | None = Query(None, ge=1, le=500),
) -> list[AlertaResponse]:
    alertas = alerta_service().listar(
        tipo=tipo,
        severidad=severidad,
        usuario=usuario,
        desde=desde,
        hasta=hasta,
        solo_no_leidas=solo_no_leidas,
        limite=limite,
    )
    return [AlertaResponse.model_validate(alerta) for alerta in alertas]


@router.get("/resumen", response_model=AlertaResumen, summary="Resumen de alertas")
def resumen() -> AlertaResumen:
    return AlertaResumen(**alerta_service().resumen())


@router.patch("/{alerta_id}/leida", response_model=AlertaResponse, summary="Marcar alerta como leída")
def marcar_leida(alerta_id: str, payload: MarcarLeidaRequest) -> AlertaResponse:
    alerta = alerta_service().marcar_leida(alerta_id, payload.leida)
    return AlertaResponse.model_validate(alerta)


@router.post("/marcar-todas-leidas", summary="Marcar todas las alertas como leídas")
def marcar_todas_leidas() -> dict[str, int]:
    return {"actualizadas": alerta_service().marcar_todas_leidas()}
