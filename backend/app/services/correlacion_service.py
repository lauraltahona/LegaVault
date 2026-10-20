"""Reglas de correlación de alertas (Módulo 7, mejora #13).

Detección básica de anomalías estilo SIEM: en lugar de mirar una alerta aisla­da,
este servicio analiza **varias alertas en conjunto** (el histórico persistido en
``alertas.json``) y, cuando detecta un patrón sospechoso, genera una alerta
``PATRON_SOSPECHOSO`` asociada a la regla que disparó.

Principios de diseño (aditividad, ver `LegalVault_Plan_Siguiente_Nivel.md`):

- **No modifica ni elimina alertas existentes**: solo agrega las suyas.
- **No rompe los flujos actuales**: los servicios que registran alertas no
  cambian; el enganche es un único punto opcional en ``AlertaService``.
- **Sin bucles**: las alertas ``PATRON_SOSPECHOSO`` no se retroalimentan y las
  generadas se escriben directamente en el repositorio (sin pasar de nuevo por
  ``AlertaService.registrar``).
- **Sin secretos**: los mensajes describen el patrón (regla, sujeto, ventana,
  umbral); nunca incluyen contraseñas, claves ni contenido de documentos.
- **Sin spam**: cada regla tiene un periodo de enfriamiento por sujeto; no se
  repite la misma alerta si el patrón continúa dentro de su ventana.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from app.core.config import settings
from app.core.constants import SeveridadAlerta, TipoAlerta
from app.models.alerta import Alerta
from app.models.base import utcnow
from app.repositories.alerta_repository import AlertaRepository

# Eventos considerados "denegación" para la regla de ráfagas. Incluye
# ``CUENTA_BLOQUEADA`` porque forma parte de la secuencia de denegaciones
# (el bloqueo es la consecuencia del último intento fallido).
TIPOS_DENEGACION = (
    TipoAlerta.LOGIN_FALLIDO,
    TipoAlerta.ACCESO_DENEGADO,
    TipoAlerta.BOVEDA_ACCESO_FALLIDO,
    TipoAlerta.CUENTA_BLOQUEADA,
)


@dataclass(frozen=True)
class ReglaCorrelacion:
    """Descripción declarativa de una regla (idéntica a la que se expone en la API)."""

    id: str
    descripcion: str
    severidad: SeveridadAlerta
    tipos_vigilados: tuple[TipoAlerta, ...]
    # Reglas de umbral: disparan al alcanzar ``umbral`` eventos del mismo
    # sujeto dentro de ``ventana_segundos``. La regla de IP nueva no usa
    # umbral/ventana sino ``cooldown_segundos`` para el enfriamiento.
    umbral: int | None = None
    ventana_segundos: int | None = None
    cooldown_segundos: int | None = None


class CorrelacionAlertasService:
    """Aplica reglas de correlación sobre el histórico de alertas."""

    def __init__(self, repository: AlertaRepository) -> None:
        self._repo = repository
        self._reglas = self._construir_reglas()

    # --- definición de reglas -------------------------------------------
    def _construir_reglas(self) -> tuple[ReglaCorrelacion, ...]:
        return (
            ReglaCorrelacion(
                id="denegados_rapidos",
                descripcion=(
                    f"{settings.corr_denegados_umbral} o más eventos de denegación del mismo "
                    f"usuario en {settings.corr_denegados_minutos} minutos "
                    "(intentos de sesión fallidos, accesos denegados, accesos fallidos a "
                    "bóvedas o bloqueos de cuenta): posible fuerza bruta o escaneo de permisos."
                ),
                severidad=SeveridadAlerta.CRITICA,
                tipos_vigilados=TIPOS_DENEGACION,
                umbral=settings.corr_denegados_umbral,
                ventana_segundos=settings.corr_denegados_minutos * 60,
            ),
            ReglaCorrelacion(
                id="descargas_masivas",
                descripcion=(
                    f"{settings.corr_descargas_umbral} o más documentos descargados por el mismo "
                    f"usuario en {settings.corr_descargas_segundos} segundos: posible extracción "
                    "masiva de información (fuga de datos)."
                ),
                severidad=SeveridadAlerta.ADVERTENCIA,
                tipos_vigilados=(TipoAlerta.DOCUMENTO_DESCARGADO,),
                umbral=settings.corr_descargas_umbral,
                ventana_segundos=settings.corr_descargas_segundos,
            ),
            ReglaCorrelacion(
                id="ip_nunca_vista",
                descripcion=(
                    "Inicio de sesión desde una IP que nunca se había visto para ese usuario "
                    "(requiere un inicio de sesión previo como línea base): posible robo de "
                    "credenciales o acceso desde otro dispositivo/ubicación."
                ),
                severidad=SeveridadAlerta.ADVERTENCIA,
                tipos_vigilados=(TipoAlerta.LOGIN_EXITOSO,),
                cooldown_segundos=settings.corr_ip_cooldown_minutos * 60,
            ),
        )

    def reglas(self) -> list[ReglaCorrelacion]:
        """Reglas activas (para el endpoint educativo ``GET /alertas/reglas``)."""

        return list(self._reglas)

    # --- evaluación ------------------------------------------------------
    def evaluar(self, alerta: Alerta) -> list[Alerta]:
        """Aplica las reglas a una alerta recién registrada.

        Devuelve las alertas ``PATRON_SOSPECHOSO`` generadas (cero o más).
        Las alertas de correlación no se evalúan para evitar bucles y una
        regla que falle nunca interrumpe el registro del evento original.
        """

        if alerta.tipo == TipoAlerta.PATRON_SOSPECHOSO:
            return []
        generadas: list[Alerta] = []
        for regla in self._reglas:
            if alerta.tipo not in regla.tipos_vigilados:
                continue
            try:
                generada = self._aplicar(regla, alerta)
            except Exception:
                continue
            if generada is not None:
                generadas.append(generada)
        return generadas

    def _aplicar(self, regla: ReglaCorrelacion, alerta: Alerta) -> Alerta | None:
        if regla.id == "ip_nunca_vista":
            return self._evaluar_ip_nueva(regla, alerta)
        return self._evaluar_rafaga(regla, alerta)

    def _evaluar_rafaga(self, regla: ReglaCorrelacion, alerta: Alerta) -> Alerta | None:
        """Regla de umbral: N eventos del mismo sujeto dentro de una ventana."""

        objetivo = _normalizar(alerta.usuario)
        if not objetivo:
            return None
        ahora = alerta.creado_en or utcnow()
        assert regla.umbral is not None and regla.ventana_segundos is not None
        desde = ahora - timedelta(seconds=regla.ventana_segundos)

        coincidentes = [
            existente
            for existente in self._repo.list_all()
            if existente.tipo in regla.tipos_vigilados
            and _normalizar(existente.usuario) == objetivo
            and existente.creado_en is not None
            and desde <= existente.creado_en <= ahora
        ]
        if len(coincidentes) < regla.umbral:
            return None
        if self._en_enfriamiento(regla, objetivo, ahora):
            return None

        return self._generar(
            regla,
            usuario=alerta.usuario.strip(),
            usuario_id=alerta.usuario_id,
            ip=alerta.ip,
            ahora=ahora,
            mensaje=(
                f"Patrón sospechoso detectado (regla '{regla.id}'): "
                f"{len(coincidentes)} eventos de denegación del usuario "
                f"'{alerta.usuario.strip()}' en los últimos "
                f"{_texto_ventana(regla.ventana_segundos)}."
            ),
        )

    def _evaluar_ip_nueva(self, regla: ReglaCorrelacion, alerta: Alerta) -> Alerta | None:
        """Regla de línea base: la IP del login nunca se había visto antes."""

        objetivo = _normalizar(alerta.usuario)
        ip = (alerta.ip or "").strip()
        if not objetivo or not ip:
            return None
        ahora = alerta.creado_en or utcnow()

        previos = [
            existente
            for existente in self._repo.list_all()
            if existente.tipo == TipoAlerta.LOGIN_EXITOSO
            and _normalizar(existente.usuario) == objetivo
            and existente.id != alerta.id
        ]
        ips_vistas = {(existente.ip or "").strip() for existente in previos}
        ips_vistas.discard("")
        if not ips_vistas or ip in ips_vistas:
            # Sin línea base (primer login) o IP ya conocida: no hay patrón.
            return None
        if self._en_enfriamiento(regla, objetivo, ahora):
            return None

        return self._generar(
            regla,
            usuario=alerta.usuario.strip(),
            usuario_id=alerta.usuario_id,
            ip=ip,
            ahora=ahora,
            mensaje=(
                f"Patrón sospechoso detectado (regla '{regla.id}'): inicio de sesión "
                f"desde la IP '{ip}', nunca vista antes para el usuario "
                f"'{alerta.usuario.strip()}' ({len(ips_vistas)} IP(s) previa(s) conocida(s))."
            ),
        )

    # --- utilidades internas ---------------------------------------------
    def _en_enfriamiento(self, regla: ReglaCorrelacion, objetivo: str, ahora: datetime) -> bool:
        """¿Ya se alertó de esta regla para este sujeto dentro del enfriamiento?"""

        cooldown = regla.cooldown_segundos or regla.ventana_segundos or 0
        desde = ahora - timedelta(seconds=cooldown)
        return any(
            existente.tipo == TipoAlerta.PATRON_SOSPECHOSO
            and existente.regla == regla.id
            and _normalizar(existente.usuario) == objetivo
            and existente.creado_en is not None
            and existente.creado_en >= desde
            for existente in self._repo.list_all()
        )

    def _generar(
        self,
        regla: ReglaCorrelacion,
        *,
        usuario: str,
        usuario_id: str,
        ip: str,
        ahora: datetime,
        mensaje: str,
    ) -> Alerta:
        """Escribe la alerta de correlación directamente en el repositorio.

        No pasa por ``AlertaService.registrar``: además de evitar recursión,
        garantiza que la alerta generada tampoco vuelva a evaluarse.
        """

        alerta = Alerta(
            tipo=TipoAlerta.PATRON_SOSPECHOSO,
            severidad=regla.severidad,
            mensaje=mensaje,
            usuario=usuario,
            usuario_id=usuario_id,
            ip=ip,
            regla=regla.id,
        )
        # Se ancla al momento del evento que disparó la regla para que las
        # ventanas y enfriamientos siguientes midan contra la misma línea
        # de tiempo (relevante en pruebas con eventos retrodatados).
        alerta.creado_en = ahora
        alerta.actualizado_en = ahora
        return self._repo.add(alerta)


def _normalizar(usuario: str | None) -> str:
    return (usuario or "").strip().lower()


def _texto_ventana(segundos: int) -> str:
    if segundos % 60 == 0:
        minutos = segundos // 60
        return f"{minutos} minuto(s)"
    return f"{segundos} segundos"
