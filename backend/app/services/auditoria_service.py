"""Servicio de auditoría (Módulo 6).

Registra **todas** las acciones relevantes en un log local append-only con
cadena de hashes. Se mantiene separado del servicio de alertas (Módulo 7):
las alertas son la vista de seguridad para el administrador; la auditoría es el
registro completo y verificable de la actividad.

El servicio nunca recibe ni almacena contraseñas, claves ni el contenido de los
documentos.
"""

from __future__ import annotations

from datetime import datetime

from app.core.constants import AccionAuditoria, ResultadoAuditoria
from app.models.base import utcnow
from app.models.registro_auditoria import RegistroAuditoria
from app.models.user import User
from app.repositories.auditoria_repository import AuditoriaRepository


class AuditoriaService:
    def __init__(self, repository: AuditoriaRepository) -> None:
        self._repo = repository

    # --- escritura ------------------------------------------------------
    def registrar(
        self,
        accion: AccionAuditoria,
        *,
        actor: User | None = None,
        usuario: str = "",
        usuario_id: str = "",
        rol: str = "",
        entidad: str = "",
        entidad_id: str = "",
        resultado: ResultadoAuditoria = ResultadoAuditoria.OK,
        detalle: str = "",
        ip: str = "",
    ) -> RegistroAuditoria:
        """Añade un registro a la cadena de auditoría.

        Si se indica ``actor`` se completan automáticamente ``usuario``,
        ``usuario_id`` y ``rol``; para eventos anónimos (p. ej. un login fallido
        con un usuario inexistente) se pasan esos campos explícitamente.
        """

        if actor is not None:
            usuario = usuario or actor.username
            usuario_id = usuario_id or actor.id
            rol = rol or (actor.rol.value if actor.rol else "")

        registro = RegistroAuditoria(
            accion=accion,
            resultado=resultado,
            entidad=entidad,
            entidad_id=entidad_id,
            usuario=usuario,
            usuario_id=usuario_id,
            rol=rol,
            detalle=detalle,
            ip=ip,
        )
        return self._repo.append(registro)

    # --- consulta -------------------------------------------------------
    def listar(
        self,
        *,
        accion: AccionAuditoria | None = None,
        resultado: ResultadoAuditoria | None = None,
        usuario: str | None = None,
        entidad: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int | None = None,
    ) -> list[RegistroAuditoria]:
        objetivo_usuario = (usuario or "").strip().lower()
        objetivo_entidad = (entidad or "").strip().lower()

        def coincide(registro: RegistroAuditoria) -> bool:
            if accion is not None and registro.accion != accion:
                return False
            if resultado is not None and registro.resultado != resultado:
                return False
            if objetivo_usuario and objetivo_usuario not in registro.usuario.lower():
                return False
            if objetivo_entidad and objetivo_entidad != registro.entidad.lower():
                return False
            if desde is not None and registro.creado_en < desde:
                return False
            if hasta is not None and registro.creado_en > hasta:
                return False
            return True

        registros = sorted(
            (r for r in self._repo.list_all() if coincide(r)),
            key=lambda r: r.creado_en,
            reverse=True,
        )
        if limite is not None:
            registros = registros[:limite]
        return registros

    def verificar_integridad(self) -> dict:
        """Comprueba la cadena y devuelve un resumen del resultado."""

        integro, indice = self._repo.verificar_cadena()
        return {
            "integro": integro,
            "total": self._repo.count(),
            "indice_roto": indice,
            "verificado_en": utcnow().isoformat(),
        }

    def resumen(self) -> dict:
        registros = self._repo.list_all()
        por_resultado = {resultado.value: 0 for resultado in ResultadoAuditoria}
        por_accion: dict[str, int] = {}
        for registro in registros:
            por_resultado[registro.resultado.value] = (
                por_resultado.get(registro.resultado.value, 0) + 1
            )
            por_accion[registro.accion.value] = por_accion.get(registro.accion.value, 0) + 1
        return {
            "total": len(registros),
            "por_resultado": por_resultado,
            "por_accion": por_accion,
        }
