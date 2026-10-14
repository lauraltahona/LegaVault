"""Entidades del dominio (Modelo dentro del patrón MVC).

Son ``dataclasses`` puras: no dependen de FastAPI ni de la persistencia.
Su serialización a/desde ``dict`` la consume la capa de repositorios.
"""

from app.models.alerta import Alerta
from app.models.documento import Documento
from app.models.expediente import Expediente
from app.models.user import User

__all__ = ["Alerta", "Documento", "Expediente", "User"]
