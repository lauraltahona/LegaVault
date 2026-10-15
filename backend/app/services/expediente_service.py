"""Servicio de expedientes jurídicos (Módulos 2 y 5)."""

from __future__ import annotations

from app.core.constants import (
    AccionAuditoria,
    ROLES_GESTION_EXPEDIENTES,
    EstadoExpediente,
    ResultadoAuditoria,
    SeveridadAlerta,
    TipoAlerta,
    TipoProceso,
)
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.validators import validar_texto_obligatorio
from app.models.expediente import Expediente, normalizar_permisos
from app.models.user import User
from app.repositories.expediente_repository import ExpedienteRepository
from app.repositories.user_repository import UserRepository
from app.services.alerta_service import AlertaService
from app.services.auditoria_service import AuditoriaService
from app.services.permissions import (
    asegurar_acceso_expediente,
    asegurar_rol,
    puede_acceder_expediente,
    puede_administrar_permisos,
    puede_gestionar_expediente,
)

_ESTADOS = {estado.value for estado in EstadoExpediente}
_TIPOS_PROCESO = {tipo.value for tipo in TipoProceso}


class ExpedienteService:
    def __init__(
        self,
        repository: ExpedienteRepository,
        user_repository: UserRepository,
        alertas: AlertaService,
        auditoria: AuditoriaService,
    ) -> None:
        self._repo = repository
        self._users = user_repository
        self._alertas = alertas
        self._auditoria = auditoria

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
        self._auditoria.registrar(
            AccionAuditoria.EXPEDIENTE_CREADO,
            actor=actor,
            entidad="expediente",
            entidad_id=exp.id,
            detalle=f"Expediente '{exp.identificador}' creado.",
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
            # Al retirar un usuario autorizado se descartan sus permisos granulares.
            exp.permisos = {
                usuario_id: acciones
                for usuario_id, acciones in exp.permisos.items()
                if usuario_id == exp.abogado_responsable_id
                or usuario_id in exp.usuarios_autorizados
            }

        exp.tocar()
        self._repo.update(exp)
        self._alertas.registrar(
            TipoAlerta.EXPEDIENTE_EDITADO,
            mensaje=f"Expediente '{exp.identificador}' actualizado.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.EXPEDIENTE_EDITADO,
            actor=actor,
            entidad="expediente",
            entidad_id=exp.id,
            detalle=f"Expediente '{exp.identificador}' actualizado.",
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
        self._auditoria.registrar(
            AccionAuditoria.EXPEDIENTE_ARCHIVADO,
            actor=actor,
            entidad="expediente",
            entidad_id=exp.id,
            detalle=f"Expediente '{exp.identificador}' archivado.",
        )
        return exp

    def actualizar_permisos(
        self, expediente_id: str, permisos: dict, actor: User
    ) -> Expediente:
        """Reemplaza la matriz de permisos granular del expediente (Módulo 5).

        Solo el administrador o el abogado responsable pueden administrarla.
        """

        exp = self.obtener(expediente_id, actor)
        self._asegurar_administracion_permisos(actor, exp)

        exp.permisos = self._validar_permisos(permisos, exp)
        exp.tocar()
        self._repo.update(exp)
        self._alertas.registrar(
            TipoAlerta.EXPEDIENTE_EDITADO,
            mensaje=f"Permisos del expediente '{exp.identificador}' actualizados.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.EXPEDIENTE_PERMISOS,
            actor=actor,
            entidad="expediente",
            entidad_id=exp.id,
            detalle=f"Permisos del expediente '{exp.identificador}' actualizados.",
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

    def _validar_permisos(self, permisos: object, exp: Expediente) -> dict[str, dict[str, bool]]:
        """Valida que la matriz solo afecte a usuarios autorizados existentes."""

        limpios = normalizar_permisos(permisos)
        autorizados = set(exp.usuarios_autorizados)
        for usuario_id in limpios:
            if usuario_id in (exp.abogado_responsable_id,):
                # El responsable siempre tiene control total; no se almacena.
                continue
            if usuario_id not in autorizados:
                raise ValidationError(
                    f"El usuario '{usuario_id}' no está autorizado en el expediente."
                )
            user = self._users.get(usuario_id)
            if user is None or not user.activo:
                raise ValidationError(
                    f"El usuario '{usuario_id}' no existe o está inactivo."
                )
        return {
            usuario_id: acciones
            for usuario_id, acciones in limpios.items()
            if usuario_id != exp.abogado_responsable_id
        }

    def _asegurar_gestion(self, actor: User, exp: Expediente) -> None:
        # Pueden editar/archivar el administrador, el abogado responsable o quien
        # tenga concedida la acción 'editar' en la matriz de permisos (Módulo 5).
        if puede_gestionar_expediente(actor, exp):
            return

        self._alertas.registrar(
            TipoAlerta.ACCESO_DENEGADO,
            severidad=SeveridadAlerta.ADVERTENCIA,
            mensaje=f"Intento de modificar el expediente '{exp.identificador}' sin permisos.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.ACCESO_DENEGADO,
            actor=actor,
            entidad="expediente",
            entidad_id=exp.id,
            resultado=ResultadoAuditoria.DENEGADO,
            detalle=f"Intento de modificar el expediente '{exp.identificador}' sin permisos.",
        )
        raise PermissionDeniedError("No tiene permisos para modificar este expediente.")

    def _asegurar_administracion_permisos(self, actor: User, exp: Expediente) -> None:
        # Solo admin o responsable; tener 'editar' no basta (evita escalada).
        if puede_administrar_permisos(actor, exp):
            return

        self._alertas.registrar(
            TipoAlerta.ACCESO_DENEGADO,
            severidad=SeveridadAlerta.ADVERTENCIA,
            mensaje=f"Intento de administrar los permisos del expediente '{exp.identificador}'.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.ACCESO_DENEGADO,
            actor=actor,
            entidad="expediente",
            entidad_id=exp.id,
            resultado=ResultadoAuditoria.DENEGADO,
            detalle=(
                f"Intento de administrar los permisos del expediente "
                f"'{exp.identificador}' sin permisos."
            ),
        )
        raise PermissionDeniedError("Solo el administrador o el responsable pueden administrar los permisos.")

    @staticmethod
    def _normalizar_enum(valor: object, validos: set[str], enum_cls, campo: str):
        if isinstance(valor, enum_cls):
            return valor
        texto = str(valor or "").strip().lower()
        if texto not in validos:
            raise ValidationError(f"El {campo} indicado no es válido.")
        return enum_cls(texto)
