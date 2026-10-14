"""Punto de entrada de la API LegalVault (FastAPI)."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.controllers import (
    alerta_router,
    auth_router,
    documento_router,
    expediente_router,
    user_router,
)
from app.core.bootstrap import asegurar_datos_iniciales
from app.core.config import settings
from app.core.exceptions import DomainError


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Prepara directorios y el administrador inicial antes de aceptar tráfico.
    asegurar_datos_iniciales()
    yield


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description=(
        "Sistema seguro de gestión de expedientes jurídicos. "
        "Módulos implementados: autenticación y usuarios, expedientes, "
        "documentos y alertas de seguridad."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(DomainError)
async def _manejar_error_dominio(_: Request, exc: DomainError) -> JSONResponse:
    """Traduce errores de negocio a respuestas HTTP."""

    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})


@app.exception_handler(RequestValidationError)
async def _manejar_error_validacion(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"detail": "Los datos enviados no son válidos.", "errores": exc.errors()},
    )


@app.get("/", tags=["Sistema"], summary="Estado de la API")
def estado() -> dict[str, str]:
    return {"app": settings.app_name, "version": settings.version, "estado": "ok"}


@app.get("/api/health", tags=["Sistema"], summary="Comprobación de salud")
def health() -> dict[str, str]:
    return {"estado": "ok"}


for _router in (auth_router, user_router, expediente_router, documento_router, alerta_router):
    app.include_router(_router, prefix=settings.api_prefix)
