"""LegalVault - Backend (FastAPI).

Arquitectura MVC + capa de servicios:

    models/        -> Modelo de dominio (entidades del negocio).
    repositories/  -> Acceso a datos (persistencia en JSON).
    services/      -> Lógica de negocio / reglas de la aplicación.
    controllers/   -> Controladores (routers HTTP, frontera de la API).
    schemas/       -> Contratos de entrada/salida (vista serializable).
"""

__version__ = "1.0.0"
