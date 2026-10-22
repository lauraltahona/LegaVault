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

Adjuntos (mejora M4.1 / Fase 6)
------------------------------
Cada vista admite además **archivos adjuntos**. Los metadatos (nombre, mime,
tamaño, hash del texto plano) viven **dentro** del JSON cifrado de la vista y
los **bytes** en un blob aparte de tamaño fijo
(``data/bovedas/{id}/adjuntos.bin``): dos segmentos, uno por fondo, del **mismo
tamaño exacto** sea cual sea el contenido. Así ni el número de archivos ni su
tamaño delatan nada.

Garantías
---------
- El contenido se cifra siempre con AES-256-GCM (confidencialidad + integridad)
  usando una clave derivada con scrypt (ver :mod:`app.core.boveda_crypto`).
- El servicio **nunca** persiste contraseñas ni claves.
- Cada operación sensible se registra como alerta (Módulo 7) **sin** filtrar el
  contenido ni las credenciales.
"""

from __future__ import annotations

import base64
import hashlib
import os
import random

from app.core import boveda_adjuntos
from app.core.boveda_adjuntos import ErrorAdjuntos
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
    ConflictError,
    NotFoundError,
    PermissionDeniedError,
    ValidationError,
)
from app.core.magic_bytes import validar_tipo_archivo
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
_MAX_NOMBRE_ARCHIVO = 255
_MAX_TITULO_ADJUNTO = 200

# MIME que se guarda en los metadatos según el formato **detectado** por magic
# bytes (nunca según el Content-Type que declara el navegador: lo controla
# quien sube el archivo).
_MIME_POR_FORMATO = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "zip": "application/zip",
    "texto": "text/plain",
}
_MIME_POR_EXTENSION = {".csv": "text/csv"}


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
        # Capacidad de adjuntos por fondo (Fase 6), idéntica para las dos vistas.
        adjuntos_mb = self._adjuntos_mb_solicitado(datos.get("adjuntos_mb"))
        capacidad_bytes = adjuntos_mb * 1024 * 1024

        contenido_visible = self._contenido_inicial(datos.get("contenido_visible"))
        contenido_confidencial = self._contenido_inicial(datos.get("contenido_confidencial"))
        # Cada vista nace con su propio bloque de adjuntos (clave y base de
        # nonce distintas): así cambiar la contraseña de un fondo no obliga a
        # recifrar sus archivos.
        for contenido in (contenido_visible, contenido_confidencial):
            contenido["version"] = 2
            contenido["adjuntos"] = self._inicializar_adjuntos(capacidad_bytes)

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
            formato=2,
            adjuntos_mb=adjuntos_mb,
        )
        self._repo.add(boveda)
        # El blob nace con los dos segmentos del mismo tamaño (solo relleno):
        # su tamaño no depende de lo que se adjunte después.
        boveda_adjuntos.crear_blob_vacio(
            boveda_adjuntos.ruta_blob(settings.bovedas_dir, boveda.id),
            boveda_adjuntos.bytes_segmento(capacidad_bytes, settings.boveda_chunk_kb),
        )
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

        # Solo se re-cifra el JSON de la vista: los chunks de los adjuntos **no**
        # se tocan, porque su clave es propia de la vista y no deriva de la
        # contraseña (decisión D4 del spec de la Fase 6).
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
        # El directorio de adjuntos se borra con la bóveda: no queda nada
        # huérfano en disco.
        boveda_adjuntos.eliminar_blob(settings.bovedas_dir, boveda.id)
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

    # --- adjuntos (Fase 6, mejora M4.1) ---------------------------------
    def adjuntar(
        self,
        boveda_id: str,
        password: str,
        *,
        nombre: str,
        contenido: bytes,
        titulo: str = "",
        actor: User,
    ) -> dict:
        """Adjunta un archivo **al fondo que abre ``password``**.

        El servidor resuelve solo qué vista es: la contraseña del fondo es la
        credencial (decisión D6 del spec). Orden de operaciones (spec §7):

        1. acceso + formato v2 + contraseña,
        2. tipo real del archivo (magic bytes) y tamaño,
        3. reserva de slots e **índice de nonce** (persistido antes de
           escribir el blob),
        4. cifrado de los chunks y SHA-256 del texto plano,
        5. escritura del blob (atómica),
        6. guardado del metadato en el JSON cifrado de la vista.

        Si fallan los pasos 5 o 6 se revierte el metadato, pero **el contador
        nunca retrocede**: reutilizar un nonce con la misma clave rompería el
        GCM por completo.
        """

        boveda = self.obtener(boveda_id, actor)
        self._asegurar_formato_v2(boveda)
        indice, contenido_vista = self._localizar_vista(boveda, password, actor)

        nombre_seguro = self._sanitizar_nombre(nombre)
        if not contenido:
            raise ValidationError("El archivo está vacío.")
        try:
            formato = validar_tipo_archivo(
                nombre_seguro,
                contenido,
                extensiones_permitidas=settings.extensiones_archivo_permitidas,
            )
        except ValidationError as exc:
            self._registrar_rechazo_adjunto(actor, boveda, nombre_seguro, exc.message)
            raise

        bloque = self._bloque_adjuntos(contenido_vista)
        chunk_bytes = int(bloque["chunk_bytes"])
        slots = int(bloque["slots"])
        cuantos = max(1, -(-len(contenido) // chunk_bytes))
        if cuantos > slots:
            raise ValidationError(self._mensaje_capacidad(boveda, bloque, len(contenido)))

        # Reserva física: un tramo contiguo de slots libres. Al borrar un
        # archivo sus bytes quedan como espacio muerto, pero el slot puede
        # reutilizarse: el límite real es la capacidad total del fondo.
        slot_inicio = self._reservar_slots(bloque, cuantos, boveda)

        # Reserva del índice de nonce: monótono y nunca reutilizado.
        inicio_nonce = int(bloque["contador"])
        bloque["contador"] = inicio_nonce + cuantos
        # Se persiste el contador ANTES de escribir el blob: si el proceso
        # muriese ahora, esos nonces quedarían consumidos (nunca repetidos).
        boveda.vistas[indice] = self._cifrar_para(boveda, contenido_vista, password)
        boveda.tocar()
        self._repo.update(boveda)

        clave = self._b64_decode(bloque["clave"])
        iv_base = self._b64_decode(bloque["iv_base"])
        digest = hashlib.sha256(contenido).hexdigest()
        slot_total = chunk_bytes + boveda_adjuntos.TAG_BYTES
        cambios: dict[int, bytes] = {}
        for numero in range(cuantos):
            trozo = contenido[numero * chunk_bytes : (numero + 1) * chunk_bytes]
            cambios[slot_inicio + numero] = boveda_adjuntos.cifrar_chunk(
                clave,
                iv_base,
                boveda.id,
                indice,
                inicio_nonce + numero,
                trozo,
                chunk_bytes,
            )

        # Escritura del blob: el segmento contrario se copia byte a byte.
        boveda_adjuntos.actualizar_segmento(
            boveda_adjuntos.ruta_blob(settings.bovedas_dir, boveda.id),
            indice,
            slots * slot_total,
            slot_total,
            cambios,
        )

        adjunto = {
            "id": new_id(),
            "nombre": nombre_seguro,
            "mime": self._mime_de(nombre_seguro, formato),
            "tamano_bytes": len(contenido),
            "sha256": digest,
            "chunk_inicio": inicio_nonce,
            "chunks": cuantos,
            "slot_inicio": slot_inicio,
            "titulo": str(titulo or "").strip()[:_MAX_TITULO_ADJUNTO],
            "creado_en": utcnow().isoformat(),
        }
        bloque["archivos"].append(adjunto)
        boveda.vistas[indice] = self._cifrar_para(boveda, contenido_vista, password)
        boveda.tocar()
        self._repo.update(boveda)

        self._alertas.registrar(
            TipoAlerta.BOVEDA_ADJUNTO_CARGADO,
            mensaje=(
                f"Adjunto '{adjunto['nombre']}' ({adjunto['mime']}, "
                f"{adjunto['tamano_bytes']} bytes) cargado en la bóveda '{boveda.nombre}'."
            ),
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ADJUNTO_CARGADO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=(
                f"Adjunto '{adjunto['nombre']}' (sha256 {adjunto['sha256']}) cargado "
                f"en la bóveda '{boveda.nombre}'."
            ),
        )
        return adjunto

    def descargar_adjunto(
        self, boveda_id: str, adjunto_id: str, password: str, actor: User
    ) -> dict:
        """Descarga un adjunto: re-verifica el SHA-256 antes de servirlo."""

        boveda = self.obtener(boveda_id, actor)
        self._asegurar_formato_v2(boveda)
        indice, contenido_vista = self._localizar_vista(boveda, password, actor)
        bloque = self._bloque_adjuntos(contenido_vista)
        archivo = self._buscar_adjunto(bloque, adjunto_id)

        plano, motivo = self._leer_adjunto(boveda, indice, bloque, archivo)
        if plano is None:
            self._registrar_corrupcion_adjunto(actor, boveda, archivo, motivo)
            raise ConflictError(
                "Verificación de integridad fallida: el contenido del adjunto no "
                "coincide con el registrado. La descarga queda bloqueada y se generó "
                "una alerta de seguridad."
            )

        self._alertas.registrar(
            TipoAlerta.BOVEDA_ADJUNTO_DESCARGADO,
            mensaje=(
                f"Adjunto '{archivo['nombre']}' descargado de la bóveda '{boveda.nombre}'."
            ),
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ADJUNTO_DESCARGADO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=(
                f"Adjunto '{archivo['nombre']}' descargado de la bóveda '{boveda.nombre}'."
            ),
        )
        return {
            "contenido": plano,
            "nombre": archivo["nombre"],
            "mime": archivo.get("mime") or "application/octet-stream",
            "sha256": archivo.get("sha256", ""),
        }

    def verificar_adjunto(
        self, boveda_id: str, adjunto_id: str, password: str, actor: User
    ) -> dict:
        """Re-verifica la integridad (SHA-256) de un adjunto."""

        boveda = self.obtener(boveda_id, actor)
        self._asegurar_formato_v2(boveda)
        indice, contenido_vista = self._localizar_vista(boveda, password, actor)
        bloque = self._bloque_adjuntos(contenido_vista)
        archivo = self._buscar_adjunto(bloque, adjunto_id)

        plano, motivo = self._leer_adjunto(boveda, indice, bloque, archivo)
        esperado = archivo.get("sha256", "")
        if plano is None:
            self._registrar_corrupcion_adjunto(actor, boveda, archivo, motivo)
            return {
                "id": archivo["id"],
                "integro": False,
                "checksum_esperado": esperado,
                "checksum_calculado": None,
                "tamano_esperado": int(archivo.get("tamano_bytes") or 0),
                "tamano_calculado": None,
                "verificado_en": utcnow().isoformat(),
                "mensaje": (
                    f"¡Integridad comprometida! El adjunto '{archivo['nombre']}' no "
                    "supera la autenticación del cifrado: se generó una alerta crítica."
                ),
            }

        calculado = hashlib.sha256(plano).hexdigest()
        integro = calculado == esperado
        if not integro:
            self._registrar_corrupcion_adjunto(
                actor,
                boveda,
                archivo,
                "El SHA-256 del texto plano no coincide con el metadato registrado.",
            )
        else:
            self._auditoria.registrar(
                AccionAuditoria.BOVEDA_ADJUNTO_DESCARGADO,
                actor=actor,
                entidad="boveda",
                entidad_id=boveda.id,
                detalle=(
                    f"Verificación de integridad correcta del adjunto "
                    f"'{archivo['nombre']}' de la bóveda '{boveda.nombre}'."
                ),
            )
        return {
            "id": archivo["id"],
            "integro": integro,
            "checksum_esperado": esperado,
            "checksum_calculado": calculado,
            "tamano_esperado": int(archivo.get("tamano_bytes") or 0),
            "tamano_calculado": len(plano),
            "verificado_en": utcnow().isoformat(),
            "mensaje": (
                "SHA-256 verificado: el adjunto descifrado coincide con el metadato "
                "registrado."
                if integro
                else (
                    f"¡Integridad comprometida! El SHA-256 del adjunto "
                    f"'{archivo['nombre']}' no coincide con el registrado; se generó "
                    "una alerta crítica."
                )
            ),
        }

    def eliminar_adjunto(
        self, boveda_id: str, adjunto_id: str, password: str, actor: User
    ) -> None:
        """Elimina el metadato de un adjunto.

        Los **bytes no se borran**: el blob mantiene exactamente su tamaño (si
        encogiera, el tamaño delataría cuántas descargas hubo) y el contador de
        nonces **no se libera** (reutilizar un nonce rompe el GCM).
        """

        boveda = self.obtener(boveda_id, actor)
        self._asegurar_formato_v2(boveda)
        indice, contenido_vista = self._localizar_vista(boveda, password, actor)
        bloque = self._bloque_adjuntos(contenido_vista)
        archivo = self._buscar_adjunto(bloque, adjunto_id)

        bloque["archivos"] = [
            item for item in bloque["archivos"] if item.get("id") != adjunto_id
        ]
        boveda.vistas[indice] = self._cifrar_para(boveda, contenido_vista, password)
        boveda.tocar()
        self._repo.update(boveda)

        self._alertas.registrar(
            TipoAlerta.BOVEDA_ADJUNTO_ELIMINADO,
            mensaje=f"Adjunto '{archivo['nombre']}' eliminado de la bóveda '{boveda.nombre}'.",
            usuario=actor.username,
            usuario_id=actor.id,
            severidad=SeveridadAlerta.ADVERTENCIA,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ADJUNTO_ELIMINADO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            resultado=ResultadoAuditoria.OK,
            detalle=(
                f"Adjunto '{archivo['nombre']}' eliminado de la bóveda '{boveda.nombre}'. "
                "Los bytes permanecen cifrados en el blob (tamaño constante)."
            ),
        )

    def modernizar(
        self, boveda_id: str, password_visible: str, password_confidencial: str, actor: User
    ) -> Boveda:
        """Migra una bóveda v1 (solo texto) al formato v2 (con adjuntos).

        Exige **las dos contraseñas**: sin ellas no se puede garantizar que
        ambas vistas queden cifradas con la misma cubeta ni con el mismo
        tamaño de segmento, que es lo que sostiene la negación plausible.
        """

        boveda = self.obtener(boveda_id, actor)
        if password_visible == password_confidencial:
            raise ValidationError("Las dos contraseñas de la bóveda deben ser diferentes.")

        indices: dict[str, int] = {}
        for etiqueta, password in (
            ("visible", password_visible),
            ("confidencial", password_confidencial),
        ):
            encontrados = [
                indice
                for indice, vista in enumerate(boveda.vistas)
                if es_vista_valida(vista) and descifrar(vista, password) is not None
            ]
            if len(encontrados) != 1:
                raise ValidationError(
                    "La contraseña indicada no abre exactamente un fondo de la bóveda."
                )
            indices[etiqueta] = encontrados[0]

        if indices["visible"] == indices["confidencial"]:
            raise ValidationError(
                "Las dos contraseñas deben abrir fondos distintos de la bóveda."
            )

        # La capacidad se conserva si la bóveda ya la tenía; si no, se toma la
        # configurada por defecto.
        adjuntos_mb = boveda.adjuntos_mb or settings.boveda_adjuntos_mb
        capacidad_bytes = adjuntos_mb * 1024 * 1024
        bucket_mb = boveda.bucket_mb or settings.boveda_bucket_mb

        for etiqueta, password in (
            ("visible", password_visible),
            ("confidencial", password_confidencial),
        ):
            indice = indices[etiqueta]
            contenido = descifrar(boveda.vistas[indice], password) or {}
            bloque = contenido.get("adjuntos")
            if not isinstance(bloque, dict):
                # Bóveda v1: se inicializa el bloque desde cero.
                bloque = self._inicializar_adjuntos(capacidad_bytes)
                contenido["adjuntos"] = bloque
            contenido["version"] = 2
            boveda.vistas[indice] = cifrar(contenido, password, bucket_mb=bucket_mb)

        boveda.bucket_mb = bucket_mb
        boveda.formato = 2
        boveda.adjuntos_mb = adjuntos_mb
        boveda.tocar()
        self._repo.update(boveda)

        # El blob solo se crea si no existe: nunca se pisa lo que ya hay.
        ruta = boveda_adjuntos.ruta_blob(settings.bovedas_dir, boveda.id)
        if not ruta.exists():
            boveda_adjuntos.crear_blob_vacio(
                ruta,
                boveda_adjuntos.bytes_segmento(capacidad_bytes, settings.boveda_chunk_kb),
            )

        self._alertas.registrar(
            TipoAlerta.BOVEDA_EDITADA,
            mensaje=f"Bóveda '{boveda.nombre}' modernizada al formato con adjuntos.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_EDITADA,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            detalle=(
                f"Bóveda '{boveda.nombre}' modernizada al formato v2 (con adjuntos, "
                f"capacidad de {adjuntos_mb} MB por fondo)."
            ),
        )
        return boveda

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
        # 401 (no 422): la credencial es incorrecta, no los datos enviados.
        # El mensaje es genérico para no revelar cuántas vistas hay ni cuál se
        # acercó (regla innegociable de no filtrar información por los errores).
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
    def _adjuntos_mb_solicitado(valor: object) -> int:
        """Capacidad de adjuntos por fondo (escalera 1 / 5 / 25 MB)."""

        if valor is None or valor == "":
            return settings.boveda_adjuntos_mb
        try:
            pedido = int(valor)
        except (TypeError, ValueError):
            raise ValidationError("La capacidad de adjuntos no es válida.") from None
        if pedido not in boveda_adjuntos.ESCALERA_ADJUNTOS_MB:
            escalera = ", ".join(f"{mb} MB" for mb in boveda_adjuntos.ESCALERA_ADJUNTOS_MB)
            raise ValidationError(
                f"La capacidad de adjuntos no es válida. Capacidades admitidas: {escalera}."
            )
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

    # --- adjuntos: utilidades internas ----------------------------------
    @staticmethod
    def _inicializar_adjuntos(capacidad_bytes: int) -> dict:
        """Crea el bloque de adjuntos de una vista (v2).

        La clave (32 B) y la base del nonce (8 B) son **aleatorias y propias de
        la vista**: así, cambiar la contraseña de un fondo no obliga a recifrar
        sus archivos y la clave nunca sale del ciphertext.
        """

        chunk_bytes = boveda_adjuntos.bytes_chunk(capacidad_bytes, settings.boveda_chunk_kb)
        slots = boveda_adjuntos.slots_por_capacidad(capacidad_bytes, settings.boveda_chunk_kb)
        return {
            "iv_base": base64.b64encode(os.urandom(boveda_adjuntos.IV_BASE_BYTES)).decode("ascii"),
            "clave": base64.b64encode(os.urandom(boveda_adjuntos.CLAVE_BYTES)).decode("ascii"),
            "contador": 0,
            "slots": slots,
            "chunk_bytes": chunk_bytes,
            "archivos": [],
        }

    @staticmethod
    def _bloque_adjuntos(contenido: dict) -> dict:
        """Devuelve el bloque de adjuntos de una vista (o error si no existe)."""

        bloque = contenido.get("adjuntos")
        if not isinstance(bloque, dict):
            raise ConflictError(
                "Esta bóveda usa el formato anterior (solo texto). "
                "Modernícela para poder adjuntar archivos."
            )
        bloque.setdefault("archivos", [])
        return bloque

    @staticmethod
    def _asegurar_formato_v2(boveda: Boveda) -> None:
        if boveda.formato < 2:
            raise ConflictError(
                "Esta bóveda usa el formato anterior (solo texto). "
                "Use la opción de modernizar la bóveda para poder adjuntar archivos."
            )

    @staticmethod
    def _buscar_adjunto(bloque: dict, adjunto_id: str) -> dict:
        for archivo in bloque.get("archivos") or []:
            if isinstance(archivo, dict) and archivo.get("id") == adjunto_id:
                return archivo
        raise NotFoundError("El adjunto no existe en este fondo.")

    @staticmethod
    def _reservar_slots(bloque: dict, cuantos: int, boveda: Boveda) -> int:
        """Reserva un tramo contiguo de slots libres y devuelve el primero."""

        slots = int(bloque.get("slots") or 0)
        ocupados: set[int] = set()
        for archivo in bloque.get("archivos") or []:
            if not isinstance(archivo, dict):
                continue
            inicio = int(archivo.get("slot_inicio") or 0)
            for numero in range(int(archivo.get("chunks") or 0)):
                ocupados.add(inicio + numero)
        libres = sorted(set(range(slots)) - ocupados)
        for posicion in range(len(libres)):
            tramo = 1
            while (
                posicion + tramo < len(libres)
                and libres[posicion + tramo] == libres[posicion] + tramo
            ):
                tramo += 1
            if tramo >= cuantos:
                return libres[posicion]
        raise ValidationError(
            BovedaService._mensaje_capacidad(boveda, bloque, 0)
        )

    @staticmethod
    def _mensaje_capacidad(boveda: Boveda, bloque: dict, tamano: int) -> str:
        capacidad_mb = boveda.adjuntos_mb or settings.boveda_adjuntos_mb
        utiles = boveda_adjuntos.bytes_utiles(
            capacidad_mb * 1024 * 1024, settings.boveda_chunk_kb
        )
        if tamano:
            return (
                f"El archivo no cabe en este fondo: la capacidad disponible es de "
                f"{utiles // (1024 * 1024)} MB y el archivo ocupa "
                f"{tamano // (1024 * 1024) + 1} MB."
            )
        return (
            f"No queda espacio libre en este fondo: la capacidad total es de "
            f"{utiles // (1024 * 1024)} MB. Borre algún adjunto para liberar espacio."
        )

    @staticmethod
    def _leer_adjunto(
        boveda: Boveda, indice: int, bloque: dict, archivo: dict
    ) -> tuple[bytes | None, str]:
        """Lee y descifra un adjunto.

        Devuelve ``(plano, "")`` si todo cuadra o ``(None, motivo)`` si el
        contenido está alterado o no se puede leer.
        """

        try:
            clave = BovedaService._b64_decode(bloque["clave"])
            iv_base = BovedaService._b64_decode(bloque["iv_base"])
        except (KeyError, ValueError, TypeError):
            return None, "Los metadatos del adjunto están incompletos."

        chunk_bytes = int(bloque.get("chunk_bytes") or 0)
        slots = int(bloque.get("slots") or 0)
        if chunk_bytes <= 0 or slots <= 0:
            return None, "Los metadatos del adjunto están incompletos."
        slot_total = chunk_bytes + boveda_adjuntos.TAG_BYTES
        segmento_bytes = slots * slot_total

        ruta = boveda_adjuntos.ruta_blob(settings.bovedas_dir, boveda.id)
        try:
            segmento = boveda_adjuntos.leer_segmento(ruta, indice, segmento_bytes)
        except (ErrorAdjuntos, OSError):
            return None, "El archivo de adjuntos no está disponible."

        inicio_nonce = int(archivo.get("chunk_inicio") or 0)
        slot_inicio = int(archivo.get("slot_inicio") or 0)
        cuantos = int(archivo.get("chunks") or 0)
        trozos: list[bytes] = []
        for numero in range(cuantos):
            offset = (slot_inicio + numero) * slot_total
            cifrado = segmento[offset : offset + slot_total]
            if len(cifrado) != slot_total:
                return None, "El archivo de adjuntos está incompleto."
            try:
                trozos.append(
                    boveda_adjuntos.descifrar_chunk(
                        clave,
                        iv_base,
                        boveda.id,
                        indice,
                        inicio_nonce + numero,
                        cifrado,
                        chunk_bytes,
                    )
                )
            except ErrorAdjuntos:
                return None, (
                    "El chunk cifrado no supera la autenticación: el contenido fue alterado."
                )

        total = int(archivo.get("tamano_bytes") or 0)
        plano = b"".join(trozos)[:total]
        if hashlib.sha256(plano).hexdigest() != archivo.get("sha256"):
            return None, "El SHA-256 del texto plano no coincide con el metadato registrado."
        return plano, ""

    @staticmethod
    def _b64_decode(valor: object) -> bytes:
        return base64.b64decode(str(valor or "").encode("ascii"))

    @staticmethod
    def _mime_de(nombre: str, formato: str) -> str:
        extension = os.path.splitext(str(nombre))[1].lower()
        if formato == "texto":
            return _MIME_POR_EXTENSION.get(extension, "text/plain")
        return _MIME_POR_FORMATO.get(formato, "application/octet-stream")

    @staticmethod
    def _sanitizar_nombre(nombre: str) -> str:
        base = os.path.basename(str(nombre or "").replace("\\", "/")).strip()
        if not base:
            raise ValidationError("El nombre del archivo no es válido.")
        return base[:_MAX_NOMBRE_ARCHIVO]

    # --- adjuntos: alertas y auditoría ----------------------------------
    def _registrar_rechazo_adjunto(
        self, actor: User, boveda: Boveda, nombre: str, motivo: str
    ) -> None:
        """Rechazo por validación de tipo (magic bytes) o archivo vacío.

        Solo se registran metadatos del intento; el contenido del archivo
        jamás se almacena ni se refleja en los mensajes.
        """

        mensaje = (
            f"Adjunto '{nombre}' rechazado en la bóveda '{boveda.nombre}': {motivo}"
        )
        self._alertas.registrar(
            TipoAlerta.BOVEDA_ADJUNTO_RECHAZADO,
            severidad=SeveridadAlerta.ADVERTENCIA,
            mensaje=mensaje,
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ADJUNTO_RECHAZADO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            resultado=ResultadoAuditoria.DENEGADO,
            detalle=mensaje,
        )

    def _registrar_corrupcion_adjunto(
        self, actor: User, boveda: Boveda, archivo: dict, motivo: str
    ) -> None:
        """Alerta crítica + auditoría cuando el adjunto no supera la verificación."""

        mensaje = (
            f"El adjunto '{archivo.get('nombre', '')}' de la bóveda '{boveda.nombre}' "
            f"no supera la verificación de integridad: {motivo}"
        )
        self._alertas.registrar(
            TipoAlerta.BOVEDA_ADJUNTO_CORRUPTO,
            severidad=SeveridadAlerta.CRITICA,
            mensaje=mensaje,
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.BOVEDA_ADJUNTO_CORRUPTO,
            actor=actor,
            entidad="boveda",
            entidad_id=boveda.id,
            resultado=ResultadoAuditoria.ERROR,
            detalle=mensaje,
        )
