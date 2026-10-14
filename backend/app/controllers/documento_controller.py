"""Controlador de documentos (Módulo 3)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, File, Form, UploadFile, status
from fastapi.responses import FileResponse

from app.controllers.dependencies import get_current_user
from app.core.constants import NivelSensibilidad, TipoDocumento
from app.core.container import documento_service
from app.models.user import User
from app.schemas.documento_schema import DocumentoResponse

router = APIRouter(prefix="/documentos", tags=["Documentos"])


@router.get("", response_model=list[DocumentoResponse], summary="Listar / buscar documentos")
def listar(
    expediente_id: str | None = None,
    tipo: TipoDocumento | None = None,
    nivel_sensibilidad: NivelSensibilidad | None = None,
    q: str | None = None,
    usuario: User = Depends(get_current_user),
) -> list[DocumentoResponse]:
    documentos = documento_service().listar(
        usuario,
        expediente_id=expediente_id,
        tipo=tipo,
        nivel_sensibilidad=nivel_sensibilidad,
        q=q,
    )
    return [DocumentoResponse.model_validate(documento) for documento in documentos]


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
