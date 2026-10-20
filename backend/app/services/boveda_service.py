"""Servicio de bóveda cifrada de doble fondo (Módulo 4).

Concepto
--------
Cada bóveda guarda **dos vistas cifradas independientes**. Al crearla se eligen
**dos contraseñas distintas**: una abre la vista "principal" y la otra abre una
vista "oculta" (la doble fondo). Como las dos vistas tienen exactamente el mismo
formato y se almacenan **en orden aleatorio**, quien observe el archivo no puede
saber cuál es cuál ni que existe un segundo contenido.

Además, ambas vistas se rellenan (*padding*, mejora #15) hasta la **misma
cubeta** (``bucket_mb``), de forma que ocupan exactamente los mismos bytes: el
tamaño del archivo no delata el volumen real de cada fondo.

Garantías
---------
- El contenido se cifra siempre con AES-256-GCM (confidencialidad + integridad)
  usando una clave derivada con scrypt (ver :mod:`app.core.boveda_crypto`).
- El servicio **nunca** persiste contraseñas ni claves.
- Cada operación sensible se registra como alerta (Módulo 7) **sin** filtrar el
  contenido ni las credenciales.
"""

from __future__ import annotations

import random

from app.core.boveda_crypto import calcular_bucket, cifrar, descifrar, es_vista_valida
from app.core.config import settings
from app.core.constants import (
    ROLES_GESTION_BOVEDA,
    AccionAuditoria,
    ResultadoAuditoria,
    SeveridadAlerta,
    TipoAlerta,
)
from app.core.exceptions import (
    AuthenticationError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.validators import validar_password_boveda, validar_texto_obligatorio
from app.models.base import new_id, utcnow
from app.models.boveda import Boveda
from app.models.user import User
from app.repositories.boveda_repository import BovedaRepository
from app.repositories.expediente_repository import ExpedienteRepository
from app.services.alerta_service import AlertaService
from app.services.auditoria_service import AuditoriaService
from app.services.permissions import asegurar_rol, es_admin, puede_acceder_expediente

_MAX_ENTRADAS = 500
_MAX_TEXTO = 20000


class BovedaService:
    def __init__(
        self,
        repository: BovedaRepository,
        expediente_repository: ExpedienteRepository,
        alertas: AlertaService,
        auditoria: AuditoriaService,
    ) -> None:
        self._repo = repository
        self._expedientes = expediente_repository
        self._alertas = alertas
        self._auditoria = auditoria

    # --- consultas ------------------------------------------------------
    def listar(self, actor: User) -> list[Boveda]:
        return sorted(
            (boveda for boveda in self._repo.list_all() if self._puede_acceder(actor, boveda)),
            key=lambda boveda: boveda.actualizado_en,
            reverse=True,
        )

    def obtener(self, boveda_id: str, actor: User) -> Boveda:
        boveda = self._repo.get(boveda_id)
        if boveda is None:
            raise NotFoundError("La bóveda no existe.")
        self._asegurar_acceso(actor, boveda)
        return boveda

    # --- comandos -------------------------------------------------------
    def crear(self, datos: dict, actor: User) -> Boveda:
        asegurar_rol(actor, *ROLES_GESTION_BOVEDA)

        nombre = validar_texto_obligatorio(datos.get("nombre", ""), "nombre", 120)
        password_visible = validar_password_boveda(
            datos.get("password_visible", ""), "contraseña de la vista principal"
        )
        password_confidencial = validar_password_boveda(
            datos.get("password_confidencial", ""), "contraseña de la vista confidencial"
        )
        if password_visible == password_confidencial:
            raise ValidationError("Las dos contraseñas de la bóveda deben ser diferentes.")

        expediente_id = self._validar_expediente(datos.get("expediente_id"), actor)

        # Cubeta de padding (mejora #15), idéntica para las dos vistas.
        bucket_mb = self._bucket_solicitado(datos.get("bucket_mb"))

        contenido_visible = self._contenido_inicial(datos.get("contenido_visible"))
        contenido_confidencial = self._contenido_inicial(datos.get("contenido_confidencial"))
        vistas = [
            cifrar(contenido_visible, password_visible, bucket_mb=bucket_mb),
            cifrar(contenido_confidencial, password_confidencial, bucket_mb=bucket_mb),
        ]
        # El orden se aleatoriza para no revelar qué vista es "principal" u "oculta".
        random.SystemRandom().shuffle(vistas)

        boveda = Boveda(
            id=new_id(),
            nombre=nombre,
            descripcion=str(datos.get("descripcion", "") or "").strip()[:1000],
            expediente_id=expediente_id,
            creado_por_id=actor.id,
            vistas=vistas,
            bucket_mb=bucket_mb,
        )
        self._repo.add(boveda)
        self._alertas.registrar(
            TipoAlerta.BOVEDA_CREADA,
            mensaje=f"Bóveda cifrada '{boveda.nombre}' creada.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_CREADA,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=f"Bóveda cifrada '{boveda.nombre}' creada.",
        )
        return boveda

    def desbloquear(self, boveda_id: str, password: str, actor: User) -> dict:
        boveda = self.obtener(boveda_id, actor)
        _, contenido = self._localizar_vista(boveda, password, actor)
        self._alertas.registrar(
            TipoAlerta.BOVEDA_ABIERTA,
            mensaje=f"Bóveda '{boveda.nombre}' desbloqueada.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ABIERTA,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=f"Bóveda '{boveda.nombre}' desbloqueada.",
        )
        return contenido

    def agregar_entrada(self, boveda_id: str, password: str, datos: dict, actor: User) -> dict:
        boveda = self.obtener(boveda_id, actor)
        titulo = validar_texto_obligatorio(datos.get("titulo", ""), "título", 200)
        texto = str(datos.get("contenido", "") or "").strip()
        if not texto:
            raise ValidationError("El contenido de la entrada es obligatorio.")
        if len(texto) > _MAX_TEXTO:
            raise ValidationError(f"El contenido no puede superar {_MAX_TEXTO} caracteres.")

        indice, contenido = self._localizar_vista(boveda, password, actor)
        entradas = contenido.setdefault("entradas", [])
        if not isinstance(entradas, list):
            entradas = []
            contenido["entradas"] = entradas
        if len(entradas) >= _MAX_ENTRADAS:
            raise ValidationError("La bóveda alcanzó el número máximo de entradas.")

        entrada = self._nueva_entrada(titulo, texto)
        entradas.append(entrada)

        boveda.vistas[indice] = self._cifrar_para(boveda, contenido, password)
        boveda.tocar()
        self._repo.update(boveda)
        self._alertas.registrar(
            TipoAlerta.BOVEDA_EDITADA,
            mensaje=f"Se añadió una entrada a la bóveda '{boveda.nombre}'.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_EDITADA,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=f"Se añadió una entrada a la bóveda '{boveda.nombre}'.",
        )
        return entrada

    def cambiar_credenciales(
        self, boveda_id: str, password_actual: str, password_nueva: str, actor: User
    ) -> None:
        boveda = self.obtener(boveda_id, actor)
        password_nueva = validar_password_boveda(password_nueva, "nueva contraseña")
        indice, contenido = self._localizar_vista(boveda, password_actual, actor)

        # La nueva contraseña no debe abrir la otra vista (rompería la separación
        # de los dos fondos y el sellado de cada uno con su propia credencial).
        for otro in range(len(boveda.vistas)):
            if otro == indice:
                continue
            if es_vista_valida(boveda.vistas[otro]) and descifrar(boveda.vistas[otro], password_nueva) is not None:
                raise ValidationError("La nueva contraseña coincide con la de la otra vista.")

        boveda.vistas[indice] = self._cifrar_para(boveda, contenido, password_nueva)
        boveda.tocar()
        self._repo.update(boveda)
        self._alertas.registrar(
            TipoAlerta.BOVEDA_CREDENCIALES,
            mensaje=f"Se actualizaron las credenciales de acceso de la bóveda '{boveda.nombre}'.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_CREDENCIALES,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=f"Se actualizaron las credenciales de acceso de la bóveda '{boveda.nombre}'.",
        )

    def eliminar(self, boveda_id: str, actor: User) -> None:
        boveda = self.obtener(boveda_id, actor)
        if not es_admin(actor) and actor.id != boveda.creado_por_id:
            raise PermissionDeniedError(
                "Solo el creador de la bóveda o un administrador pueden eliminarla."
            )
        self._repo.delete(boveda.id)
        self._alertas.registrar(
            TipoAlerta.BOVEDA_ELIMINADA,
            mensaje=f"Bóveda cifrada '{boveda.nombre}' eliminada.",
            usuario=actor.username,
            usuario_id=actor.id,
            severidad=SeveridadAlerta.ADVERTENCIA,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ELIMINADA,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=f"Bóveda cifrada '{boveda.nombre}' eliminada.",
        )

    # --- autorización ---------------------------------------------------
    def _puede_acceder(self, actor: User, boveda: Boveda) -> bool:
        if es_admin(actor):
            return True
        if boveda.creado_por_id == actor.id:
            return True
        if boveda.expediente_id:
            expediente = self._expedientes.get(boveda.expediente_id)
            if expediente is not None and puede_acceder_expediente(actor, expediente):
                return True
        return False

    def _asegurar_acceso(self, actor: User, boveda: Boveda) -> None:
        if self._puede_acceder(actor, boveda):
            return
        self._alertas.registrar(
            TipoAlerta.ACCESO_DENEGADO,
            severidad=SeveridadAlerta.ADVERTENCIA,
            mensaje=f"Intento de acceder a la bóveda '{boveda.nombre}' sin permisos.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.ACCESO_DENEGADO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            resultado=ResultadoAuditoria.DENEGADO,
            detalle=f"Intento de acceder a la bóveda '{boveda.nombre}' sin permisos.",
        )
        raise PermissionDeniedError("No tiene permisos para acceder a esta bóveda.")

    # --- utilidades internas -------------------------------------------
    def _localizar_vista(self, boveda: Boveda, password: str, actor: User) -> tuple[int, dict]:
        """Devuelve ``(índice, contenido)`` de la vista que abre ``password``.

        Si ninguna vista se descifra, registra el intento fallido y lanza un
        error **genérico** (no revela cuántas vistas hay ni cuál se acercó).
        """

        for indice, vista in enumerate(boveda.vistas):
            if not es_vista_valida(vista):
                continue
            contenido = descifrar(vista, password)
            if contenido is not None:
                return indice, contenido

        self._alertas.registrar(
            TipoAlerta.BOVEDA_ACCESO_FALLIDO,
            mensaje=f"Intento fallido de abrir la bóveda '{boveda.nombre}'.",
            usuario=actor.username,
            usuario_id=actor.id,
            severidad=SeveridadAlerta.ADVERTENCIA,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ACCESO_FALLIDO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            resultado=ResultadoAuditoria.DENEGADO,
            detalle=f"Intento fallido de abrir la bóveda '{boveda.nombre}'.",
        )
        raise AuthenticationError("Contraseña de bóveda incorrecta.")

    def _validar_expediente(self, expediente_id: object, actor: User) -> str:
        identificador = str(expediente_id or "").strip()
        if not identificador:
            return ""
        expediente = self._expedientes.get(identificador)
        if expediente is None:
            raise ValidationError("El expediente indicado no existe.")
        if not puede_acceder_expediente(actor, expediente):
            raise PermissionDeniedError("No tiene permisos sobre el expediente indicado.")
        return expediente.id

    @staticmethod
    def _contenido_inicial(texto: object) -> dict:
        entradas: list[dict] = []
        limpio = str(texto or "").strip()
        if limpio:
            entradas.append(BovedaService._nueva_entrada("Contenido inicial", limpio[:_MAX_TEXTO]))
        return {"entradas": entradas}

    @staticmethod
    def _bucket_solicitado(valor: object) -> int:
        """Cubeta pedida al crear la bóveda (0 desactiva el padding).

        Si el cliente no indica nada se usa el valor configurado
        (``LEGALVAULT_BOVEDA_BUCKET_MB``, 1 MB por defecto).
        """

        if valor is None or valor == "":
            pedido = settings.boveda_bucket_mb
        else:
            try:
                pedido = int(valor)
            except (TypeError, ValueError):
                raise ValidationError("La cubeta de la bóveda no es válida.") from None
        if pedido < 0:
            raise ValidationError("La cubeta de la bóveda no es válida.")
        return pedido

    @staticmethod
    def _cifrar_para(boveda: Boveda, contenido: dict, password: str) -> dict:
        """Re-cifra una vista **conservando la cubeta** de la bóveda.

        Si la bóveda es antigua (``bucket_mb == 0``) se mantiene sin padding, de
        modo que las bóvedas heredadas siguen abriéndose y editándose igual.
        """

        return cifrar(contenido, password, bucket_mb=boveda.bucket_mb)

    @staticmethod
    def _nueva_entrada(titulo: str, contenido: str) -> dict:
        return {
            "id": new_id(),
            "titulo": titulo,
            "contenido": contenido,
            "creado_en": utcnow().isoformat(),
        }
