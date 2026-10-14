"""Repositorio de alertas de seguridad (Módulo 7)."""

from __future__ import annotations

from pathlib import Path

from app.core.constants import SeveridadAlerta, TipoAlerta
from app.models.alerta import Alerta
from app.repositories.json_repository import JsonRepository


class AlertaRepository(JsonRepository[Alerta]):
    def __init__(self, file_path: str | Path) -> None:
        super().__init__(file_path, Alerta)

    def recientes(self, limite: int = 50) -> list[Alerta]:
        alertas = sorted(self.list_all(), key=lambda alerta: alerta.creado_en, reverse=True)
        return alertas[:limite]

    def contar_fallos_recientes(self, usuario: str, desde: object) -> int:
        objetivo = (usuario or "").strip().lower()
        return len(
            [
                alerta
                for alerta in self.list_all()
                if alerta.tipo == TipoAlerta.LOGIN_FALLIDO
                and alerta.usuario.lower() == objetivo
                and alerta.creado_en >= desde
            ]
        )

    def contar_por_severidad(self, severidad: SeveridadAlerta) -> int:
        return len(self.find(lambda alerta: alerta.severidad == severidad))
