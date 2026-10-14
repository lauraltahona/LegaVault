"""Servicio de expedientes jurídicos (Módulos 2 y 5)."""

from __future__ import annotations

from app.core.constants import (
    ROLES_GESTION_EXPEDIENTES,
    EstadoExpediente,
    Rol,
    SeveridadAlerta,
    TipoAlerta,
    TipoProceso,
)
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.validators import validar_texto_obligatorio
from app.models.expediente import Expediente
from app.models.user import User
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.user_repository import UserRepository
from app.services.alerta_service import AlertaService
from app.services.permissions import (
    asegurar_acceso_expediente,
    asegurar_rol,
    es_admin,
    puede_acceder_expediente,
)

_ESTADOS = {estado.value for estado in EstadoExpediente}
_TIPOS_PROCESO = {tipo.value for tipo in TipoProceso}


class ExpedienteService:
    def __init__(
        self,
        repository: ExpedienteRepository,
        user_repository: UserRepository,
        alertas: AlertaService,
    ) -> None:
        self._repo = repository
        self._users = user_repository
        self._alertas = alertas

    # --- consultas ------------------------------------------------------
    def listar(
        self,
        actor: User,
        *,
        q: str | None = None,
        estado: EstadoExpediente | None = None,
        tipo_proceso: TipoProceso | None = None,
        abogado_id: str | None = None,
    ) -> list[Expediente]:
        objetivo = (q or "").strip().lower()

        def coincide(exp: Expediente) -> bool:
            if not puede_acceder_expediente(actor, exp):
                return False
            if estado is not None and exp.estado != estado:
                return False
            if tipo_proceso is not None and exp.tipo_proceso != tipo_proceso:
                return False
            if abogado_id and exp.abogado_responsable_id != abogado_id:
                return False
            if objetivo:
                campos = f"{exp.identificador} {exp.asunto} {exp.cliente}".lower()
                if objetivo not in campos:
                    return False
            return True

        return sorted(
            self._repo.find(coincide),
            key=lambda exp: exp.actualizado_en,
            reverse=True,
        )

    def obtener(self, expediente_id: str, actor: User) -> Expediente:
        exp = self._repo.get(expediente_id)
        if exp is None:
            raise NotFoundError("El expediente no existe.")
        asegurar_acceso_expediente(actor, exp)
        return exp

    # --- comandos -------------------------------------------------------
    def crear(self, datos: dict, actor: User) -> Expediente:
        asegurar_rol(actor, *ROLES_GESTION_EXPEDIENTES)
        exp = self._construir(datos, actor)
        self._repo.add(exp)
        self._alertas.registrar(
            TipoAlerta.EXPEDIENTE_CREADO,
            mensaje=f"Expediente '{exp.identificador}' creado.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        return exp

    def actualizar(self, expediente_id: str, datos: dict, actor: User) -> Expediente:
        exp = self.obtener(expediente_id, actor)
        self._asegurar_gestion(actor, exp)

        if "identificador" in datos and datos["identificador"] is not None:
            identificador = validar_texto_obligatorio(datos["identificador"], "identificador", 60)
            if self._repo.identificador_exists(identificador, exclude_id=exp.id):
                raise ConflictError("Ya existe un expediente con ese identificador.")
            exp.identificador = identificador
        if "asunto" in datos and datos["asunto"] is not None:
            exp.asunto = validar_texto_obligatorio(datos["asunto"], "asunto", 200)
        if "cliente" in datos and datos["cliente"] is not None:
            exp.cliente = validar_texto_obligatorio(datos["cliente"], "cliente", 200)
        if "descripcion" in datos and datos["descripcion"] is not None:
            exp.descripcion = str(datos["descripcion"]).strip()[:2000]
        if "tipo_proceso" in datos and datos["tipo_proceso"] is not None:
            exp.tipo_proceso = self._normalizar_enum(datos["tipo_proceso"], _TIPOS_PROCESO, TipoProceso, "tipo de proceso")
        if "estado" in datos and datos["estado"] is not None:
            exp.estado = self._normalizar_enum(datos["estado"], _ESTADOS, EstadoExpediente, "estado")
        if "abogado_responsable_id" in datos and datos["abogado_responsable_id"] is not None:
            responsable = self._validar_responsable(datos["abogado_responsable_id"])
            exp.abogado_responsable_id = responsable.id
            if responsable.id not in exp.usuarios_autorizados:
                exp.usuarios_autorizados.append(responsable.id)
        if "usuarios_autorizados" in datos and datos["usuarios_autorizados"] is not None:
            exp.usuarios_autorizados = self._validar_autorizados(datos["usuarios_autorizados"])

        exp.tocar()
        self._repo.update(exp)
        self._alertas.registrar(
            TipoAlerta.EXPEDIENTE_EDITADO,
            mensaje=f"Expediente '{exp.identificador}' actualizado.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        return exp

    def archivar(self, expediente_id: str, actor: User) -> Expediente:
        exp = self.obtener(expediente_id, actor)
        self._asegurar_gestion(actor, exp)
        exp.estado = EstadoExpediente.ARCHIVADO
        exp.tocar()
        self._repo.update(exp)
        self._alertas.registrar(
            TipoAlerta.EXPEDIENTE_ARCHIVADO,
            mensaje=f"Expediente '{exp.identificador}' archivado.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        return exp

    # --- utilidades internas -------------------------------------------
    def _construir(self, datos: dict, actor: User) -> Expediente:
        identificador = validar_texto_obligatorio(datos.get("identificador", ""), "identificador", 60)
        if self._repo.identificador_exists(identificador):
            raise ConflictError("Ya existe un expediente con ese identificador.")

        estado = self._normalizar_enum(
            datos.get("estado", EstadoExpediente.ABIERTO.value), _ESTADOS, EstadoExpediente, "estado"
        )
        tipo_proceso = self._normalizar_enum(
            datos.get("tipo_proceso", TipoProceso.OTRO.value), _TIPOS_PROCESO, TipoProceso, "tipo de proceso"
        )

        responsable_id = datos.get("abogado_responsable_id") or actor.id
        responsable = self._validar_responsable(responsable_id)

        autorizados = self._validar_autorizados(datos.get("usuarios_autorizados") or [])
        if responsable.id not in autorizados:
            autorizados.append(responsable.id)

        return Expediente(
            identificador=identificador,
            asunto=validar_texto_obligatorio(datos.get("asunto", ""), "asunto", 200),
            cliente=validar_texto_obligatorio(datos.get("cliente", ""), "cliente", 200),
            tipo_proceso=tipo_proceso,
            estado=estado,
            abogado_responsable_id=responsable.id,
            descripcion=str(datos.get("descripcion", "") or "").strip()[:2000],
            usuarios_autorizados=autorizados,
        )

    def _validar_responsable(self, user_id: str) -> User:
        user = self._users.get(str(user_id))
        if user is None or not user.activo:
            raise ValidationError("El abogado responsable indicado no existe o está inactivo.")
        if user.rol not in ROLES_GESTION_EXPEDIENTES:
            raise ValidationError("El responsable debe tener rol de administrador o abogado.")
        return user

    def _validar_autorizados(self, ids: list) -> list[str]:
        resultado: list[str] = []
        for user_id in ids:
            user = self._users.get(str(user_id))
            if user is None or not user.activo:
                raise ValidationError(f"El usuario autorizado '{user_id}' no existe o está inactivo.")
            if user.id not in resultado:
                resultado.append(user.id)
        return resultado

    def _asegurar_gestion(self, actor: User, exp: Expediente) -> None:
        if es_admin(actor):
            return
        if actor.rol == Rol.ABOGADO and puede_acceder_expediente(actor, exp):
            return

        self._alertas.registrar(
            TipoAlerta.ACCESO_DENEGADO,
            severidad=SeveridadAlerta.ADVERTENCIA,
            mensaje=f"Intento de modificar el expediente '{exp.identificador}' sin permisos.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        raise PermissionDeniedError("No tiene permisos para modificar este expediente.")

    @staticmethod
    def _normalizar_enum(valor: object, validos: set[str], enum_cls, campo: str):
        if isinstance(valor, enum_cls):
            return valor
        texto = str(valor or "").strip().lower()
        if texto not in validos:
            raise ValidationError(f"El {campo} indicado no es válido.")
        return enum_cls(texto)
