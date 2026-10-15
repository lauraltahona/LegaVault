"""Controlador de auditoría (Módulo 6). Solo administradores."""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.controllers.dependencies import require_admin
from app.core.constants import AccionAuditoria, ResultadoAuditoria
from app.core.container import auditoria_service
from app.schemas.auditoria_schema import (
    AuditoriaResumen,
    AuditoriaVerificacion,
    RegistroAuditoriaResponse,
)

router = APIRouter(
    prefix="/auditoria",
    tags=["Auditoría"],
    dependencies=[Depends(require_admin)],
)


@router.get("", response_model=list[RegistroAuditoriaResponse], summary="Consultar la auditoría")
def listar(
    accion: AccionAuditoria | None = None,
    resultado: ResultadoAuditoria | None = None,
    usuario: str | None = Query(None, description="Filtra por nombre de usuario (parcial)"),
    entidad: str | None = Query(None, description="Filtra por entidad exacta"),
    desde: datetime | None = None,
    hasta: datetime | None = None,
    limite: int | None = Query(None, ge=1, le=1000),
) -> list[RegistroAuditoriaResponse]:
    registros = auditoria_service().listar(
        accion=accion,
        resultado=resultado,
        usuario=usuario,
        entidad=entidad,
        desde=desde,
        hasta=hasta,
        limite=limite,
    )
    return [RegistroAuditoriaResponse.model_validate(registro) for registro in registros]


@router.get(
    "/verificar",
    response_model=AuditoriaVerificacion,
    summary="Verificar la integridad de la cadena de auditoría",
)
def verificar() -> AuditoriaVerificacion:
    return AuditoriaVerificacion(**auditoria_service().verificar_integridad())


@router.get("/resumen", response_model=AuditoriaResumen, summary="Resumen de la auditoría")
def resumen() -> AuditoriaResumen:
    return AuditoriaResumen(**auditoria_service().resumen())
