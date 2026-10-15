"""Servicio de gestión documental (Módulos 3 y 5).

Los archivos se guardan en disco (``data/uploads``) con un nombre generado
por el sistema; el nombre original se conserva solo como metadato. Cada
documento guarda un checksum SHA-256 para verificar su integridad.
"""

from __future__ import annotations

import hashlib
from pathlib import Path

from app.core.config import settings
from app.core.constants import (
    AccionAuditoria,
    ROLES_CARGA_DOCUMENTOS,
    NivelSensibilidad,
    ResultadoAuditoria,
    Rol,
    SeveridadAlerta,
    TipoAlerta,
    TipoDocumento,
)
from app.core.exceptions import NotFoundError, PermissionDeniedError, ValidationError
from app.core.validators import validar_texto_obligatorio
from app.models.base import new_id
from app.models.documento import Documento
from app.models.expediente import Expediente
from app.models.user import User
from app.repositories.documento_repository import DocumentoRepository
from app.repositories.expediente_repository import ExpedienteRepository
from app.services.alerta_service import AlertaService
from app.services.auditoria_service import AuditoriaService
from app.services.permissions import (
    asegurar_accion,
    asegurar_acceso_expediente,
    asegurar_descargar_documento,
    asegurar_rol,
    puede_eliminar_documento,
    puede_leer_documento,
)

_TIPOS = {tipo.value for tipo in TipoDocumento}
_NIVELES = {nivel.value for nivel in NivelSensibilidad}


class DocumentoService:
    def __init__(
        self,
        repository: DocumentoRepository,
        expediente_repository: ExpedienteRepository,
        alertas: AlertaService,
        auditoria: AuditoriaService,
    ) -> None:
        self._repo = repository
        self._expedientes = expediente_repository
        self._alertas = alertas
        self._auditoria = auditoria

    # --- consultas ------------------------------------------------------
    def listar(
        self,
        actor: User,
        *,
        expediente_id: str | None = None,
        tipo: TipoDocumento | None = None,
        nivel_sensibilidad: NivelSensibilidad | None = None,
        q: str | None = None,
    ) -> list[Documento]:
        objetivo = (q or "").strip().lower()
        cache: dict[str, Expediente] = {}

        def expediente_de(documento: Documento) -> Expediente | None:
            if documento.expediente_id not in cache:
                cache[documento.expediente_id] = self._expedientes.get(documento.expediente_id)
            return cache[documento.expediente_id]

        def coincide(documento: Documento) -> bool:
            exp = expediente_de(documento)
            if exp is None or not puede_leer_documento(actor, documento, exp):
                return False
            if expediente_id and documento.expediente_id != expediente_id:
                return False
            if tipo is not None and documento.tipo != tipo:
                return False
            if nivel_sensibilidad is not None and documento.nivel_sensibilidad != nivel_sensibilidad:
                return False
            if objetivo and objetivo not in documento.nombre_original.lower():
                return False
            return True

        return sorted(self._repo.find(coincide), key=lambda doc: doc.creado_en, reverse=True)

    def obtener(self, documento_id: str, actor: User) -> Documento:
        documento, _ = self._obtener_con_expediente(documento_id, actor)
        return documento

    # --- comandos -------------------------------------------------------
    def subir(
        self,
        actor: User,
        *,
        expediente_id: str,
        contenido: bytes,
        nombre_original: str,
        tipo: str,
        nivel_sensibilidad: str,
        descripcion: str = "",
    ) -> Documento:
        asegurar_rol(actor, *ROLES_CARGA_DOCUMENTOS)

        exp = self._expedientes.get(expediente_id)
        if exp is None:
            raise NotFoundError("El expediente indicado no existe.")
        asegurar_accion(actor, exp, "cargar")

        nombre_seguro = self._sanitizar_nombre(nombre_original)
        if not contenido:
            raise ValidationError("El archivo está vacío.")
        if len(contenido) > settings.max_tamano_archivo_bytes:
            raise ValidationError(
                f"El archivo supera el tamaño máximo de {settings.max_tamano_archivo_mb} MB."
            )

        tipo_doc = self._normalizar(tipo, _TIPOS, TipoDocumento, "tipo de documento")
        nivel = self._normalizar(
            nivel_sensibilidad, _NIVELES, NivelSensibilidad, "nivel de sensibilidad"
        )
        # Mínimo privilegio: el asistente no puede crear documentos confidenciales.
        if actor.rol == Rol.ASISTENTE and nivel == NivelSensibilidad.CONFIDENCIAL:
            raise PermissionDeniedError(
                "El asistente jurídico no puede cargar documentos confidenciales."
            )

        documento = Documento(
            id=new_id(),
            nombre_original=nombre_seguro,
            nombre_almacenado="",
            expediente_id=exp.id,
            tipo=tipo_doc,
            nivel_sensibilidad=nivel,
            descripcion=(descripcion or "").strip()[:1000],
            tamano_bytes=len(contenido),
            checksum_sha256=hashlib.sha256(contenido).hexdigest(),
            subido_por_id=actor.id,
        )

        settings.uploads_dir.mkdir(parents=True, exist_ok=True)
        archivo = settings.uploads_dir / self._nombre_almacenado(documento.id, nombre_seguro)
        archivo.write_bytes(contenido)
        documento.nombre_almacenado = archivo.name

        self._repo.add(documento)
        self._alertas.registrar(
            TipoAlerta.DOCUMENTO_CARGADO,
            mensaje=(
                f"Documento '{documento.nombre_original}' cargado en el expediente "
                f"'{exp.identificador}'."
            ),
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.DOCUMENTO_CARGADO,
            actor=actor,
            entidad="documento",
            entidad_id=documento.id,
            detalle=(
                f"Documento '{documento.nombre_original}' cargado en el expediente "
                f"'{exp.identificador}'."
            ),
        )
        return documento

    def ruta_descarga(self, documento_id: str, actor: User) -> tuple[Documento, Path]:
        documento, exp = self._obtener_con_expediente(documento_id, actor)
        asegurar_descargar_documento(actor, documento, exp)

        archivo = settings.uploads_dir / documento.nombre_almacenado
        if not archivo.exists():
            raise NotFoundError("El archivo físico del documento no está disponible.")

        self._alertas.registrar(
            TipoAlerta.DOCUMENTO_DESCARGADO,
            mensaje=(
                f"Documento '{documento.nombre_original}' descargado del expediente "
                f"'{exp.identificador}'."
            ),
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.DOCUMENTO_DESCARGADO,
            actor=actor,
            entidad="documento",
            entidad_id=documento.id,
            detalle=(
                f"Documento '{documento.nombre_original}' descargado del expediente "
                f"'{exp.identificador}'."
            ),
        )
        return documento, archivo

    def eliminar(self, documento_id: str, actor: User) -> None:
        documento, exp = self._obtener_con_expediente(documento_id, actor)
        if not puede_eliminar_documento(actor, documento, exp):
            self._alertas.registrar(
                TipoAlerta.ACCESO_DENEGADO,
                severidad=SeveridadAlerta.ADVERTENCIA,
                mensaje=f"Intento de eliminar el documento '{documento.nombre_original}' sin permisos.",
                usuario=actor.username,
                usuario_id=actor.id,
            )
            self._auditoria.registrar(
                AccionAuditoria.ACCESO_DENEGADO,
                actor=actor,
                entidad="documento",
                entidad_id=documento.id,
                resultado=ResultadoAuditoria.DENEGADO,
                detalle=f"Intento de eliminar el documento '{documento.nombre_original}' sin permisos.",
            )
            raise PermissionDeniedError(
                "Solo el autor del documento, un administrador o quien tenga permiso "
                "de eliminación pueden borrarlo."
            )

        archivo = settings.uploads_dir / documento.nombre_almacenado
        if archivo.exists():
            archivo.unlink(missing_ok=True)
        self._repo.delete(documento.id)
        self._alertas.registrar(
            TipoAlerta.DOCUMENTO_ELIMINADO,
            mensaje=(
                f"Documento '{documento.nombre_original}' eliminado del expediente "
                f"'{exp.identificador}'."
            ),
            usuario=actor.username,
            usuario_id=actor.id,
            severidad=SeveridadAlerta.ADVERTENCIA,
        )
        self._auditoria.registrar(
            AccionAuditoria.DOCUMENTO_ELIMINADO,
            actor=actor,
            entidad="documento",
            entidad_id=documento.id,
            detalle=(
                f"Documento '{documento.nombre_original}' eliminado del expediente "
                f"'{exp.identificador}'."
            ),
        )

    # --- utilidades internas -------------------------------------------
    def _obtener_con_expediente(self, documento_id: str, actor: User) -> tuple[Documento, Expediente]:
        documento = self._repo.get(documento_id)
        if documento is None:
            raise NotFoundError("El documento no existe.")
        exp = self._expedientes.get(documento.expediente_id)
        if exp is None:
            raise NotFoundError("El expediente asociado ya no existe.")
        asegurar_acceso_expediente(actor, exp)
        return documento, exp

    @staticmethod
    def _sanitizar_nombre(nombre: str) -> str:
        base = Path(str(nombre or "")).name.strip()
        if not base:
            raise ValidationError("El nombre del archivo no es válido.")
        return base[:255]

    @staticmethod
    def _nombre_almacenado(documento_id: str, nombre_original: str) -> str:
        sufijo = Path(nombre_original).suffix.lower()
        if len(sufijo) > 10 or not sufijo.replace(".", "").isalnum():
            sufijo = ""
        return f"{documento_id}{sufijo}"

    @staticmethod
    def _normalizar(valor: object, validos: set[str], enum_cls, campo: str):
        if isinstance(valor, enum_cls):
            return valor
        texto = str(valor or "").strip().lower()
        if texto not in validos:
            raise ValidationError(f"El {campo} indicado no es válido.")
        return enum_cls(texto)
