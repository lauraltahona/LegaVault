"""Modelo de alerta de seguridad (Módulo 7).

Las alertas nunca contienen contraseñas, claves ni el contenido de los
documentos: solo metadatos del evento (fecha, usuario, tipo, severidad).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.constants import SeveridadAlerta, TipoAlerta
from app.models.base import BaseEntity, decode_datetime


@dataclass
class Alerta(BaseEntity):
    tipo: TipoAlerta = TipoAlerta.LOGIN_EXITOSO
    severidad: SeveridadAlerta = SeveridadAlerta.INFO
    mensaje: str = ""
    # Identificación del afectado. Para usuarios desconocidos se usa el texto
    # introducido, nunca la contraseña.
    usuario: str = ""
    usuario_id: str = ""
    ip: str = ""
    leida: bool = False
    # Identificador de la regla de correlación que generó esta alerta
    # (vacío para las alertas "nativas" registradas directamente por los
    # servicios). Campo aditivo: los JSON antiguos cargan sin él (Módulo 7).
    regla: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "Alerta":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            tipo=TipoAlerta(data.get("tipo", TipoAlerta.LOGIN_EXITOSO.value)),
            severidad=SeveridadAlerta(data.get("severidad", SeveridadAlerta.INFO.value)),
            mensaje=data.get("mensaje", ""),
            usuario=data.get("usuario", ""),
            usuario_id=data.get("usuario_id", ""),
            ip=data.get("ip", ""),
            leida=bool(data.get("leida", False)),
            regla=data.get("regla", ""),
        )
