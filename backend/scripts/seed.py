"""Datos ficticios de demostración (se ejecuta manualmente).

Uso (desde la carpeta ``backend``):
    python -m scripts.seed
"""

from __future__ import annotations

from app.core.bootstrap import asegurar_datos_iniciales
from app.core.constants import (
    EstadoExpediente,
    NivelSensibilidad,
    Rol,
    TipoDocumento,
    TipoProceso,
)
from app.core.container import (
    auditoria_repository,
    boveda_repository,
    boveda_service,
    documento_repository,
    documento_service,
    expediente_repository,
    expediente_service,
    user_repository,
    user_service,
)
from app.models.user import User


def _crear_usuario_si_no_existe(actor: User, datos: dict) -> User:
    existente = user_repository().get_by_username(datos["username"])
    if existente is not None:
        return existente
    return user_service().crear(datos, actor=actor)


def ejecutar() -> None:
    asegurar_datos_iniciales()

    admin = user_repository().get_by_username("admin")
    if admin is None:  # pragma: no cover - no debería ocurrir tras el bootstrap
        raise RuntimeError("No se encontró el administrador inicial.")

    abogado = _crear_usuario_si_no_existe(
        admin,
        {
            "username": "abogado.demo",
            "nombre_completo": "Laura Gómez (abogada)",
            "email": "laura.gomez@legalvault.local",
            "password": "Abogado123!",
            "rol": Rol.ABOGADO,
        },
    )
    asistente = _crear_usuario_si_no_existe(
        admin,
        {
            "username": "asistente.demo",
            "nombre_completo": "Mario Ruiz (asistente)",
            "email": "mario.ruiz@legalvault.local",
            "password": "Asistente123!",
            "rol": Rol.ASISTENTE,
        },
    )

    existentes = expediente_service().listar(admin)
    if not any(exp.identificador == "EXP-2026-001" for exp in existentes):
        expediente = expediente_service().crear(
            {
                "identificador": "EXP-2026-001",
                "asunto": "Reclamación de cantidad por incumplimiento de contrato",
                "cliente": "Construcciones Delta S.L.",
                "tipo_proceso": TipoProceso.CIVIL.value,
                "estado": EstadoExpediente.EN_TRAMITE.value,
                "abogado_responsable_id": abogado.id,
                "descripcion": "Expediente de demostración con datos ficticios.",
                "usuarios_autorizados": [asistente.id],
            },
            actor=abogado,
        )

        documento_service().subir(
            abogado,
            expediente_id=expediente.id,
            contenido=b"Contrato de demostracion (contenido ficticio).\n",
            nombre_original="contrato_demo.txt",
            tipo=TipoDocumento.CONTRATO.value,
            nivel_sensibilidad=NivelSensibilidad.INTERNO.value,
            descripcion="Documento de ejemplo.",
        )
        documento_service().subir(
            abogado,
            expediente_id=expediente.id,
            contenido=b"Declaracion confidencial de ejemplo (ficticia).\n",
            nombre_original="declaracion_confidencial_demo.txt",
            tipo=TipoDocumento.DECLARACION.value,
            nivel_sensibilidad=NivelSensibilidad.CONFIDENCIAL.value,
            descripcion="Solo visible para abogados y administradores.",
        )

    # --- Bóveda cifrada de doble fondo (Módulo 4) -----------------------
    if boveda_repository().count() == 0:
        expediente_demo = expediente_repository().first(
            lambda exp: exp.identificador == "EXP-2026-001"
        )
        boveda = boveda_service().crear(
            {
                "nombre": "Reserva estratégica del caso",
                "descripcion": "Bóveda de demostración con doble fondo (datos ficticios).",
                "expediente_id": expediente_demo.id if expediente_demo else "",
                "password_visible": "BovedaPublica123!",
                "password_confidencial": "BovedaReservada123!",
                "contenido_visible": (
                    "Notas de trabajo: contactos del cliente y calendario de plazos."
                ),
                "contenido_confidencial": (
                    "Estrategia reservada: evaluación interna del riesgo y margen de "
                    "negociación confidencial."
                ),
                # Fase 6: la bóveda de demo nace ya en formato v2 (con
                # adjuntos), con 5 MB de capacidad por fondo.
                "adjuntos_mb": 5,
            },
            actor=abogado,
        )
        # Un archivo de ejemplo en **cada** fondo: los bytes van al blob de
        # tamaño fijo y los metadatos al JSON cifrado de su vista.
        boveda_service().adjuntar(
            boveda.id,
            "BovedaPublica123!",
            nombre="notas_trabajo.txt",
            contenido=(
                "Notas de trabajo (contenido ficticio de demostración).\n"
                "Agenda de plazos y contactos del cliente.\n"
            ).encode("utf-8"),
            titulo="Notas de trabajo",
            actor=abogado,
        )
        boveda_service().adjuntar(
            boveda.id,
            "BovedaReservada123!",
            nombre="evaluacion_riesgo.txt",
            contenido=(
                "Evaluación interna del riesgo (contenido ficticio y reservado).\n"
                "Margen de negociación confidencial.\n"
            ).encode("utf-8"),
            titulo="Evaluación del riesgo",
            actor=abogado,
        )

    print("\n[LegalVault] Datos de demostración listos.")
    print("  admin           / Admin123!")
    print("  abogado.demo    / Abogado123!")
    print("  asistente.demo  / Asistente123!")
    print(
        "  bóveda: pasa 'BovedaPublica123!' o 'BovedaReservada123!' para cada vista"
    )
    print(f"  documentos: {documento_repository().count()}")
    print(f"  bóvedas:    {boveda_repository().count()}")
    integro, _ = auditoria_repository().verificar_cadena()
    print(
        f"  auditoría:  {auditoria_repository().count()} registros "
        f"(cadena {'íntegra' if integro else 'ALTERADA'})"
    )


if __name__ == "__main__":
    ejecutar()
