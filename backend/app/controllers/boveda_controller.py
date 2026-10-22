"""Controlador de la bóveda cifrada de doble fondo (Módulo 4).

Desde la **Fase 6 (mejora M4.1)** la bóveda admite **archivos adjuntos** por
fondo. Los cinco endpoints nuevos (``adjuntar``, ``descargar``,
``verificar-integridad``, ``eliminar`` y ``modernizar``) respetan tres reglas
que no se negocian:

1. **La contraseña viaja siempre en el cuerpo** de la petición (nunca en la
   query string): en una URL acabaría en los registros del servidor y en la
   cabecera ``Referer``.
2. **El servidor decide qué fondo se está usando**: la contraseña es la
   credencial y el backend resuelve sola la vista que se abre. Nunca se envía
   un identificador de fondo en la URL.
3. **Solo se exponen metadatos**: ni la clave de cifrado de los chunks ni el
   contenido del archivo salen del servidor en las respuestas JSON.
"""

from __future__ import annotations

from urllib.parse import quote

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile, status

from app.controllers.dependencies import get_current_user
from app.core.container import boveda_service, expediente_repository
from app.models.boveda import Boveda
from app.models.user import User
from app.schemas.boveda_schema import (
    AdjuntoAccion,
    AdjuntoMetadata,
    AdjuntoResponse,
    BovedaCreate,
    BovedaResponse,
    ContenidoResponse,
    CredencialesRequest,
    DesbloqueoRequest,
    EntradaCreate,
    EntradaResponse,
    ModernizarRequest,
    VerificacionAdjuntoResponse,
)

router = APIRouter(prefix="/bovedas", tags=["Bóveda cifrada"])


def _to_response(boveda: Boveda) -> BovedaResponse:
    respuesta = BovedaResponse.model_validate(boveda)
    if boveda.expediente_id:
        expediente = expediente_repository().get(boveda.expediente_id)
        respuesta.expediente_identificador = expediente.identificador if expediente else None
    return respuesta


def _to_contenido_response(contenido: dict) -> ContenidoResponse:
    """Convierte el JSON descifrado de una vista en la respuesta pública.

    El bloque ``adjuntos`` del JSON cifrado es un **objeto** (con la clave, el
    nonce base, el contador y la lista de archivos), así que no se puede
    validar el contenido directamente contra el esquema: se construye la
    respuesta a mano, exponiendo **solo** los metadatos de los archivos.
    """

    entradas = []
    for entrada in contenido.get("entradas") or []:
        if not isinstance(entrada, dict):
            continue
        entradas.append(
            EntradaResponse(
                id=str(entrada.get("id", "")),
                titulo=str(entrada.get("titulo", "")),
                contenido=str(entrada.get("contenido", "")),
                creado_en=str(entrada.get("creado_en", "")),
            )
        )

    bloque = contenido.get("adjuntos")
    adjuntos: list[AdjuntoMetadata] = []
    version = 1
    if isinstance(bloque, dict):
        version = 2
        for archivo in bloque.get("archivos") or []:
            if not isinstance(archivo, dict):
                continue
            adjuntos.append(
                AdjuntoMetadata(
                    id=str(archivo.get("id", "")),
                    nombre=str(archivo.get("nombre", "")),
                    mime=str(archivo.get("mime") or "application/octet-stream"),
                    tamano_bytes=int(archivo.get("tamano_bytes") or 0),
                    sha256=str(archivo.get("sha256", "")),
                    chunk_inicio=int(archivo.get("chunk_inicio") or 0),
                    chunks=int(archivo.get("chunks") or 0),
                    titulo=str(archivo.get("titulo", "")),
                )
            )
    else:
        # Bóveda heredada (v1): solo texto, sin adjuntos.
        version = int(contenido.get("version") or 1)

    return ContenidoResponse(entradas=entradas, adjuntos=adjuntos, version=version)


def _content_disposition(nombre: str) -> str:
    """Cabecera ``Content-Disposition`` con el nombre del archivo.

    Se manda la versión ASCII (para clientes antiguos) y la versión **RFC 5987**
    (``filename*=UTF-8''``) que conserva los acentos y los nombres no ASCII.
    """

    plano = str(nombre or "archivo")
    ascii_seguro = plano.encode("ascii", "replace").decode("ascii").replace('"', "_")
    return f"attachment; filename=\"{ascii_seguro}\"; filename*=UTF-8''{quote(plano, safe='')}"


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
    return _to_contenido_response(contenido)


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


# --- adjuntos (Fase 6, mejora M4.1) ----------------------------------------
@router.post(
    "/{boveda_id}/adjuntos",
    response_model=AdjuntoResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Adjuntar un archivo al fondo que abre la contraseña",
)
async def adjuntar(
    boveda_id: str,
    password: str = Form(...),
    archivo: UploadFile = File(...),
    titulo: str = Form(""),
    usuario: User = Depends(get_current_user),
) -> AdjuntoResponse:
    """Sube un archivo al fondo que abre ``password``.

    El backend resuelve sola la vista: la contraseña **es** la credencial del
    fondo, así que el cliente nunca envía el identificador de la vista.
    """

    contenido = await archivo.read()
    adjunto = boveda_service().adjuntar(
        boveda_id,
        password,
        nombre=archivo.filename or "archivo",
        contenido=contenido,
        titulo=titulo,
        actor=usuario,
    )
    return AdjuntoResponse(
        id=str(adjunto["id"]),
        nombre=str(adjunto["nombre"]),
        mime=str(adjunto["mime"]),
        tamano_bytes=int(adjunto["tamano_bytes"]),
        sha256=str(adjunto["sha256"]),
        chunk_inicio=int(adjunto["chunk_inicio"]),
        chunks=int(adjunto["chunks"]),
        titulo=str(adjunto.get("titulo", "")),
        creado_en=str(adjunto["creado_en"]),
    )


@router.post(
    "/{boveda_id}/adjuntos/{adjunto_id}/descargar",
    summary="Descargar un adjunto (verificando su integridad)",
    response_class=Response,
    responses={200: {"content": {"application/octet-stream": {}}}},
)
def descargar_adjunto(
    boveda_id: str,
    adjunto_id: str,
    payload: AdjuntoAccion,
    usuario: User = Depends(get_current_user),
) -> Response:
    """Devuelve los bytes del adjunto **en claro**, ya verificados.

    Antes de servirlos se re-computa el SHA-256 y se compara con el metadato
    cifrado: si no cuadra, la descarga se bloquea con un 409 y se genera una
    alerta crítica.
    """

    resultado = boveda_service().descargar_adjunto(
        boveda_id, adjunto_id, payload.password, usuario
    )
    return Response(
        content=resultado["contenido"],
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": _content_disposition(resultado["nombre"]),
            "X-Content-SHA256": resultado["sha256"],
        },
    )


@router.post(
    "/{boveda_id}/adjuntos/{adjunto_id}/verificar-integridad",
    response_model=VerificacionAdjuntoResponse,
    summary="Re-verificar la integridad (SHA-256) de un adjunto",
)
def verificar_adjunto(
    boveda_id: str,
    adjunto_id: str,
    payload: AdjuntoAccion,
    usuario: User = Depends(get_current_user),
) -> VerificacionAdjuntoResponse:
    return VerificacionAdjuntoResponse(
        **boveda_service().verificar_adjunto(
            boveda_id, adjunto_id, payload.password, usuario
        )
    )


@router.delete(
    "/{boveda_id}/adjuntos/{adjunto_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Eliminar un adjunto (los bytes cifrados permanecen en el blob)",
)
def eliminar_adjunto(
    boveda_id: str,
    adjunto_id: str,
    payload: AdjuntoAccion,
    usuario: User = Depends(get_current_user),
) -> None:
    boveda_service().eliminar_adjunto(boveda_id, adjunto_id, payload.password, usuario)


@router.post(
    "/{boveda_id}/modernizar",
    response_model=BovedaResponse,
    summary="Modernizar una bóveda v1 (solo texto) al formato con adjuntos",
)
def modernizar(
    boveda_id: str,
    payload: ModernizarRequest,
    usuario: User = Depends(get_current_user),
) -> BovedaResponse:
    """Migra una bóveda heredada al formato v2.

    Se piden **las dos contraseñas**: sin ellas no se puede garantizar que las
    dos vistas queden cifradas con la misma cubeta ni con el mismo tamaño de
    segmento, que es lo que sostiene la negación plausible.
    """

    boveda = boveda_service().modernizar(
        boveda_id, payload.password_visible, payload.password_confidencial, usuario
    )
    return _to_response(boveda)
