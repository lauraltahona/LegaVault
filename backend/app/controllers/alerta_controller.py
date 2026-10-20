"""Controlador de alertas de seguridad (Módulo 7). Solo administradores."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.controllers.dependencies import require_admin
from app.core.constants import SeveridadAlerta, TipoAlerta
from app.core.container import alerta_service, correlacion_service
from app.schemas.alerta_schema import (
    AlertaResponse,
    AlertaResumen,
    MarcarLeidaRequest,
    ReglaCorrelacionResponse,
)
from app.schemas.paginacion import RespuestaPaginada

router = APIRouter(
    prefix="/alertas",
    tags=["Alertas de seguridad"],
    dependencies=[Depends(require_admin)],
)


@router.get(
    "",
    response_model=RespuestaPaginada[AlertaResponse],
    summary="Consultar alertas (paginado)",
)
def listar(
    tipo: TipoAlerta | None = None,
    severidad: SeveridadAlerta | None = None,
    usuario: str | None = Query(None, description="Filtra por nombre de usuario (parcial)"),
    desde: datetime | None = None,
    hasta: datetime | None = None,
    solo_no_leidas: bool = False,
    limite: int | None = Query(None, ge=1, le=500, description="Alias legacy (usar por_pagina)"),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int | None = Query(default=None, ge=1, le=100),
) -> RespuestaPaginada[AlertaResponse]:
    pp = por_pagina if por_pagina is not None else (limite if limite is not None else 20)
    alertas, total = alerta_service().listar(
        tipo=tipo,
        severidad=severidad,
        usuario=usuario,
        desde=desde,
        hasta=hasta,
        solo_no_leidas=solo_no_leidas,
        pagina=pagina,
        por_pagina=pp,
        paginar=True,
    )
    return RespuestaPaginada.crear(
        [AlertaResponse.model_validate(alerta) for alerta in alertas], total, pagina, pp
    )


@router.get("/resumen", response_model=AlertaResumen, summary="Resumen de alertas")
def resumen() -> AlertaResumen:
    return AlertaResumen(**alerta_service().resumen())


@router.get(
    "/reglas",
    response_model=list[ReglaCorrelacionResponse],
    summary="Reglas de correlación activas",
)
def reglas() -> list[ReglaCorrelacionResponse]:
    """Describe las reglas de correlación que vigilan patrones sospechosos.

    Expone qué detecta el sistema (umbrales y ventanas incluidos) para que
    el administrador entienda de qué se generan las alertas
    ``patron_sospechoso`` (detección básica de anomalías, estilo SIEM).
    """

    return [
        ReglaCorrelacionResponse(
            id=regla.id,
            descripcion=regla.descripcion,
            severidad=regla.severidad,
            umbral=regla.umbral,
            ventana_segundos=regla.ventana_segundos,
            tipos_vigilados=list(regla.tipos_vigilados),
        )
        for regla in correlacion_service().reglas()
    ]


@router.patch("/{alerta_id}/leida", response_model=AlertaResponse, summary="Marcar alerta como leída")
def marcar_leida(alerta_id: str, payload: MarcarLeidaRequest) -> AlertaResponse:
    alerta = alerta_service().marcar_leida(alerta_id, payload.leida)
    return AlertaResponse.model_validate(alerta)


@router.post("/marcar-todas-leidas", summary="Marcar todas las alertas como leídas")
def marcar_todas_leidas() -> dict[str, int]:
    return {"actualizadas": alerta_service().marcar_todas_leidas()}
