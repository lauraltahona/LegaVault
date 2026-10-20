"""Controlador de documentos (Módulo 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from app.controllers.dependencies import get_current_user
from app.core.constants import NivelSensibilidad, TipoDocumento
from app.core.container import documento_service
from app.models.user import User
from app.schemas.documento_schema import DocumentoResponse, VerificacionIntegridadResponse
from app.schemas.paginacion import RespuestaPaginada

router = APIRouter(prefix="/documentos", tags=["Documentos"])


@router.get(
    "",
    response_model=RespuestaPaginada[DocumentoResponse],
    summary="Listar / buscar documentos (paginado)",
)
def listar(
    expediente_id: str | None = None,
    tipo: TipoDocumento | None = None,
    nivel_sensibilidad: NivelSensibilidad | None = None,
    q: str | None = None,
    limite: int | None = Query(None, ge=1, le=1000, description="Alias legacy (usar por_pagina)"),
    pagina: int = Query(default=1, ge=1),
    por_pagina: int | None = Query(default=None, ge=1, le=100),
    usuario: User = Depends(get_current_user),
) -> RespuestaPaginada[DocumentoResponse]:
    pp = por_pagina if por_pagina is not None else (limite if limite is not None else 20)
    documentos = documento_service().listar(
        usuario,
        expediente_id=expediente_id,
        tipo=tipo,
        nivel_sensibilidad=nivel_sensibilidad,
        q=q,
    )
    # El listado se filtra en el servicio y se pagina aquí (los datos caben en
    # memoria); el total se devuelve para que la UI navegue sin descargar todo.
    total = len(documentos)
    inicio = (pagina - 1) * pp
    return RespuestaPaginada.crear(
        [
            DocumentoResponse.model_validate(documento)
            for documento in documentos[inicio : inicio + pp]
        ],
        total,
        pagina,
        pp,
    )


@router.post(
    "",
    response_model=DocumentoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Cargar documento",
)
async def cargar(
    expediente_id: str = Form(...),
    tipo: str = Form(TipoDocumento.OTRO.value),
    nivel_sensibilidad: str = Form(NivelSensibilidad.INTERNO.value),
    descripcion: str = Form(""),
    archivo: UploadFile = File(...),
    usuario: User = Depends(get_current_user),
) -> DocumentoResponse:
    contenido = await archivo.read()
    documento = documento_service().subir(
        usuario,
        expediente_id=expediente_id,
        contenido=contenido,
        nombre_original=archivo.filename or "documento",
        tipo=tipo,
        nivel_sensibilidad=nivel_sensibilidad,
        descripcion=descripcion,
    )
    return DocumentoResponse.model_validate(documento)


@router.get("/{documento_id}", response_model=DocumentoResponse, summary="Obtener documento")
def obtener(documento_id: str, usuario: User = Depends(get_current_user)) -> DocumentoResponse:
    return DocumentoResponse.model_validate(documento_service().obtener(documento_id, usuario))


@router.get(
    "/{documento_id}/verificar-integridad",
    response_model=VerificacionIntegridadResponse,
    summary="Re-verificar la integridad (SHA-256) de un documento",
)
def verificar_integridad(
    documento_id: str, usuario: User = Depends(get_current_user)
) -> VerificacionIntegridadResponse:
    """Recalcula el SHA-256 del archivo en disco y lo compara con el metadato.

    Si no coincide, el servidor registra una alerta crítica y un evento de
    auditoría con resultado ``error`` (la respuesta sigue siendo 200 con
    ``integro: false`` para que la interfaz pueda mostrar ambos estados).
    """

    return VerificacionIntegridadResponse(
        **documento_service().verificar_integridad(documento_id, usuario)
    )


@router.get("/{documento_id}/descargar", summary="Descargar documento")
def descargar(documento_id: str, usuario: User = Depends(get_current_user)) -> FileResponse:
    documento, ruta = documento_service().ruta_descarga(documento_id, usuario)
    return FileResponse(
        path=ruta,
        filename=documento.nombre_original,
        media_type="application/octet-stream",
    )


@router.delete(
    "/{documento_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar documento",
)
def eliminar(documento_id: str, usuario: User = Depends(get_current_user)) -> None:
    documento_service().eliminar(documento_id, usuario)
