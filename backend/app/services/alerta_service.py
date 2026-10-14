"""Servicio de alertas y eventos de seguridad (Módulo 7).

Responsable de registrar eventos (nunca secretos) y de exponerlos al
administrador. También concentra el resumen que alimenta el panel de alertas.
"""

from __future__ import annotations

from datetime import datetime

from app.core.constants import SeveridadAlerta, TipoAlerta
from app.core.exceptions import NotFoundError
from app.models.alerta import Alerta
from app.repositories.alerta_repository import AlertaRepository

# Mensajes descriptivos por tipo de evento (sin datos sensibles).
_DESCRIPCIONES: dict[TipoAlerta, str] = {
    TipoAlerta.LOGIN_EXITOSO: "Inicio de sesión exitoso.",
    TipoAlerta.LOGIN_FALLIDO: "Intento de inicio de sesión fallido.",
    TipoAlerta.CUENTA_BLOQUEADA: "Cuenta bloqueada temporalmente por intentos fallidos.",
    TipoAlerta.CUENTA_DESBLOQUEADA: "Cuenta desbloqueada.",
    TipoAlerta.ACCESO_DENEGADO: "Intento de acceso denegado por falta de permisos.",
    TipoAlerta.USUARIO_CREADO: "Usuario creado.",
    TipoAlerta.USUARIO_EDITADO: "Usuario editado.",
    TipoAlerta.USUARIO_DESACTIVADO: "Usuario desactivado.",
    TipoAlerta.EXPEDIENTE_CREADO: "Expediente creado.",
    TipoAlerta.EXPEDIENTE_EDITADO: "Expediente editado.",
    TipoAlerta.EXPEDIENTE_ARCHIVADO: "Expediente archivado.",
    TipoAlerta.DOCUMENTO_CARGADO: "Documento cargado.",
    TipoAlerta.DOCUMENTO_DESCARGADO: "Documento descargado.",
    TipoAlerta.DOCUMENTO_ELIMINADO: "Documento eliminado.",
}

# Severidad por defecto según el tipo de evento.
_SEVERIDAD_POR_DEFECTO: dict[TipoAlerta, SeveridadAlerta] = {
    TipoAlerta.LOGIN_FALLIDO: SeveridadAlerta.ADVERTENCIA,
    TipoAlerta.CUENTA_BLOQUEADA: SeveridadAlerta.CRITICA,
    TipoAlerta.ACCESO_DENEGADO: SeveridadAlerta.ADVERTENCIA,
    TipoAlerta.DOCUMENTO_ELIMINADO: SeveridadAlerta.ADVERTENCIA,
    TipoAlerta.USUARIO_DESACTIVADO: SeveridadAlerta.ADVERTENCIA,
}


class AlertaService:
    def __init__(self, repository: AlertaRepository) -> None:
        self._repo = repository

    def registrar(
        self,
        tipo: TipoAlerta,
        *,
        mensaje: str | None = None,
        severidad: SeveridadAlerta | None = None,
        usuario: str = "",
        usuario_id: str = "",
        ip: str = "",
    ) -> Alerta:
        """Registra un evento de seguridad.

        No debe recibirse ni almacenarse contraseñas, claves ni contenido de
        documentos: únicamente metadatos del evento.
        """

        alerta = Alerta(
            tipo=tipo,
            severidad=severidad or _SEVERIDAD_POR_DEFECTO.get(tipo, SeveridadAlerta.INFO),
            mensaje=mensaje or _DESCRIPCIONES.get(tipo, tipo.value),
            usuario=usuario,
            usuario_id=usuario_id,
            ip=ip,
        )
        return self._repo.add(alerta)

    def listar(
        self,
        *,
        tipo: TipoAlerta | None = None,
        severidad: SeveridadAlerta | None = None,
        usuario: str | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        solo_no_leidas: bool = False,
        limite: int | None = None,
    ) -> list[Alerta]:
        objetivo = (usuario or "").strip().lower()
        alertas = self._repo.list_all()

        def coincide(alerta: Alerta) -> bool:
            if tipo is not None and alerta.tipo != tipo:
                return False
            if severidad is not None and alerta.severidad != severidad:
                return False
            if objetivo and objetivo not in alerta.usuario.lower():
                return False
            if desde is not None and alerta.creado_en < desde:
                return False
            if hasta is not None and alerta.creado_en > hasta:
                return False
            if solo_no_leidas and alerta.leida:
                return False
            return True

        resultado = [alerta for alerta in alertas if coincide(alerta)]
        resultado.sort(key=lambda alerta: alerta.creado_en, reverse=True)
        if limite is not None:
            resultado = resultado[:limite]
        return resultado

    def resumen(self) -> dict:
        """Conteos agregados para el panel de alertas del administrador."""

        alertas = self._repo.list_all()
        por_severidad = {severidad.value: 0 for severidad in SeveridadAlerta}
        por_tipo: dict[str, int] = {}
        for alerta in alertas:
            por_severidad[alerta.severidad.value] = por_severidad.get(alerta.severidad.value, 0) + 1
            por_tipo[alerta.tipo.value] = por_tipo.get(alerta.tipo.value, 0) + 1
        return {
            "total": len(alertas),
            "no_leidas": len([alerta for alerta in alertas if not alerta.leida]),
            "por_severidad": por_severidad,
            "por_tipo": por_tipo,
        }

    def marcar_leida(self, alerta_id: str, leida: bool = True) -> Alerta:
        alerta = self._repo.get(alerta_id)
        if alerta is None:
            raise NotFoundError("La alerta no existe.")
        alerta.leida = leida
        alerta.tocar()
        return self._repo.update(alerta)

    def marcar_todas_leidas(self) -> int:
        alertas = self._repo.list_all()
        pendientes = [alerta for alerta in alertas if not alerta.leida]
        for alerta in pendientes:
            alerta.leida = True
            alerta.tocar()
        for alerta in pendientes:
            self._repo.update(alerta)
        return len(pendientes)
