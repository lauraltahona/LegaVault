"""Modelo de expediente jurídico (Módulos 2 y 5)."""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.constants import ACCIONES_PERMISO, EstadoExpediente, TipoProceso
from app.models.base import BaseEntity, decode_datetime


def normalizar_permisos(raw: object) -> dict[str, dict[str, bool]]:
    """Normaliza la matriz de permisos ``{usuario_id: {accion: bool}}``.

    Descarta claves y acciones desconocidas para que el modelo almacene siempre
    una estructura homogénea y segura.
    """

    resultado: dict[str, dict[str, bool]] = {}
    if not isinstance(raw, dict):
        return resultado
    for usuario_id, acciones in raw.items():
        if not isinstance(acciones, dict):
            continue
        limpias = {
            accion: bool(valor)
            for accion, valor in acciones.items()
            if accion in ACCIONES_PERMISO
        }
        if limpias:
            resultado[str(usuario_id)] = limpias
    return resultado


@dataclass
class Expediente(BaseEntity):
    identificador: str = ""
    asunto: str = ""
    cliente: str = ""
    tipo_proceso: TipoProceso = TipoProceso.OTRO
    estado: EstadoExpediente = EstadoExpediente.ABIERTO
    abogado_responsable_id: str = ""
    descripcion: str = ""
    # Usuarios (además del responsable) con acceso autorizado al expediente.
    usuarios_autorizados: list[str] = field(default_factory=list)
    # Matriz granular de permisos por usuario (Módulo 5): refina las acciones
    # por encima de los valores por defecto derivados del rol y del acceso.
    permisos: dict[str, dict[str, bool]] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict) -> "Expediente":
        return cls(
            id=data["id"],
            creado_en=decode_datetime(data.get("creado_en")),
            actualizado_en=decode_datetime(data.get("actualizado_en")),
            identificador=data.get("identificador", ""),
            asunto=data.get("asunto", ""),
            cliente=data.get("cliente", ""),
            tipo_proceso=TipoProceso(data.get("tipo_proceso", TipoProceso.OTRO.value)),
            estado=EstadoExpediente(data.get("estado", EstadoExpediente.ABIERTO.value)),
            abogado_responsable_id=data.get("abogado_responsable_id", ""),
            descripcion=data.get("descripcion", ""),
            usuarios_autorizados=list(data.get("usuarios_autorizados") or []),
            permisos=normalizar_permisos(data.get("permisos")),
        )
