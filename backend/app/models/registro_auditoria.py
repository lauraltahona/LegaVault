"""Modelo de registro de auditoría (Módulo 6).

Cada registro se encadena con el anterior mediante SHA-256, de forma que el
archivo es **append-only lógico**: modificar, insertar o reordenar registros a
mano rompe la cadena y es detectable con :meth:`calcular_hash` /
``verificar_cadena`` del repositorio.

La auditoría nunca contiene contraseñas, claves ni el contenido de los
documentos: solo metadatos del evento.
"""

from __future__ import annotations

import hashlib
import json

from dataclasses import dataclass

from app.core.constants import AccionAuditoria, ResultadoAuditoria
from app.models.base import BaseEntity, decode_datetime

# Primer eslabón de la cadena: valor fijo conocido por todos.
HASH_GENESIS = "0" * 64


@dataclass
class RegistroAuditoria(BaseEntity):
    accion: AccionAuditoria = AccionAuditoria.LOGIN
    resultado: ResultadoAuditoria = ResultadoAuditoria.OK
    # Entidad afectada (p. ej. "expediente", "documento", "boveda", "usuario").
    entidad: str = ""
    entidad_id: str = ""
    # Autor de la acción. Para eventos anónimos (login fallido) se usa el texto
    # introducido, nunca la contraseña.
    usuario: str = ""
    usuario_id: str = ""
    rol: str = ""
    detalle: str = ""
    ip: str = ""
    # Encadenado de integridad.
    hash_anterior: str = HASH_GENESIS
    hash_actual: str = ""

    def _carga_canonica(self) -> str:
        """Serializa el registro (sin su propio hash) de forma determinista."""

        datos = self.to_dict()
        datos.pop("hash_actual", None)
        return json.dumps(datos, sort_keys=True, ensure_ascii=False, separators=(",", ":"))

    def calcular_hash(self) -> str:
        """Calcula ``SHA256(hash_anterior + carga_canónica)``."""

        material = f"{self.hash_anterior}{self._carga_canonica()}"
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    @classmethod
    def from_dict(cls, data: dict) -> "RegistroAuditoria":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            accion=AccionAuditoria(data.get("accion", AccionAuditoria.LOGIN.value)),
            resultado=ResultadoAuditoria(
                data.get("resultado", ResultadoAuditoria.OK.value)
            ),
            entidad=data.get("entidad", ""),
            entidad_id=data.get("entidad_id", ""),
            usuario=data.get("usuario", ""),
            usuario_id=data.get("usuario_id", ""),
            rol=data.get("rol", ""),
            detalle=data.get("detalle", ""),
            ip=data.get("ip", ""),
            hash_anterior=data.get("hash_anterior", HASH_GENESIS),
            hash_actual=data.get("hash_actual", ""),
        )
