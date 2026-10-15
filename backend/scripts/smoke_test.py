"""Prueba de humo end-to-end de la API (se ejecuta manualmente).

Usa un directorio de datos temporal para no tocar los datos reales.

Uso (desde la carpeta ``backend``):
    python -m scripts.smoke_test
"""

from __future__ import annotations

import io
import os
import tempfile

# Debe fijarse antes de importar la configuración de la aplicación.
_TMP = tempfile.mkdtemp(prefix="legalvault_smoke_")
os.environ["LEGALVAULT_DATA_DIR"] = _TMP
os.environ["LEGALVAULT_MAX_INTENTOS"] = "3"

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402

cliente = TestClient(app)
_fallos = 0


def comprobar(condicion: bool, etiqueta: str) -> None:
    global _fallos
    estado = "OK  " if condicion else "FALLO"
    print(f"[{estado}] {etiqueta}")
    if not condicion:
        _fallos += 1


def login(username: str, password: str):
    return cliente.post("/api/auth/login", json={"username": username, "password": password})


def cabecera(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def main() -> int:
    with TestClient(app) as _:
        pass  # dispara el lifespan (bootstrap del admin)

    # --- Módulo 1: autenticación ---
    respuesta = login("admin", "Admin123!")
    comprobar(respuesta.status_code == 200, "Login del administrador")
    token_admin = respuesta.json()["access_token"]

    comprobar(
        cliente.get("/api/auth/me", headers=cabecera(token_admin)).status_code == 200,
        "GET /auth/me con token válido",
    )
    comprobar(
        cliente.get("/api/auth/me").status_code == 401,
        "GET /auth/me sin token devuelve 401",
    )
    comprobar(login("admin", "incorrecta").status_code == 401, "Login con contraseña incorrecta devuelve 401")
    comprobar(login("noexiste", "x").status_code == 401, "Login con usuario inexistente devuelve 401")

    # --- Módulo 1: gestión de usuarios ---
    creado = cliente.post(
        "/api/usuarios",
        headers=cabecera(token_admin),
        json={
            "username": "abogado.smoke",
            "nombre_completo": "Abogado de prueba",
            "email": "abogado.smoke@legalvault.local",
            "password": "Abogado123!",
            "rol": "abogado",
        },
    )
    comprobar(creado.status_code == 201, "Crear usuario abogado")
    abogado = creado.json()
    comprobar("password_hash" not in abogado, "La respuesta no expone el hash de contraseña")

    comprobar(
        cliente.post(
            "/api/usuarios",
            headers=cabecera(token_admin),
            json={
                "username": "abogado.smoke",
                "nombre_completo": "Duplicado",
                "email": "otro@legalvault.local",
                "password": "Abogado123!",
                "rol": "abogado",
            },
        ).status_code == 409,
        "Usuario duplicado devuelve 409",
    )

    asistente = cliente.post(
        "/api/usuarios",
        headers=cabecera(token_admin),
        json={
            "username": "asistente.smoke",
            "nombre_completo": "Asistente de prueba",
            "email": "asistente.smoke@legalvault.local",
            "password": "Asistente123!",
            "rol": "asistente",
        },
    ).json()

    token_abogado = login("abogado.smoke", "Abogado123!").json()["access_token"]
    token_asistente = login("asistente.smoke", "Asistente123!").json()["access_token"]

    comprobar(
        cliente.get("/api/usuarios", headers=cabecera(token_abogado)).status_code == 403,
        "Un abogado no puede listar usuarios (403)",
    )
    seleccion = cliente.get("/api/usuarios/seleccion", headers=cabecera(token_abogado))
    comprobar(
        seleccion.status_code == 200 and all("email" not in u for u in seleccion.json()),
        "El abogado puede consultar la selección mínima de usuarios (sin correos)",
    )
    comprobar(
        cliente.get("/api/usuarios/seleccion", headers=cabecera(token_asistente)).status_code == 403,
        "El asistente no puede consultar la selección de usuarios (403)",
    )

    # --- Módulo 2: expedientes ---
    expediente = cliente.post(
        "/api/expedientes",
        headers=cabecera(token_abogado),
        json={
            "identificador": "EXP-SMOKE-1",
            "asunto": "Caso de prueba",
            "cliente": "Cliente Ficticio S.A.",
            "tipo_proceso": "civil",
            "abogado_responsable_id": abogado["id"],
            "usuarios_autorizados": [asistente["id"]],
        },
    )
    comprobar(expediente.status_code == 201, "Crear expediente como abogado")
    expediente_id = expediente.json()["id"]
    comprobar(expediente.json()["abogado_responsable_nombre"] == "Abogado de prueba", "Nombre del responsable enriquecido")

    comprobar(
        len(cliente.get("/api/expedientes", headers=cabecera(token_abogado)).json()) == 1,
        "El abogado ve su expediente",
    )
    comprobar(
        len(cliente.get("/api/expedientes?q=ficticio", headers=cabecera(token_abogado)).json()) == 1,
        "Búsqueda de expedientes por texto",
    )
    comprobar(
        len(cliente.get("/api/expedientes?estado=archivado", headers=cabecera(token_admin)).json()) == 0,
        "Filtro por estado",
    )

    # --- Módulo 3: documentos ---
    publico = cliente.post(
        "/api/documentos",
        headers=cabecera(token_abogado),
        data={
            "expediente_id": expediente_id,
            "tipo": "contrato",
            "nivel_sensibilidad": "interno",
            "descripcion": "Contrato de prueba",
        },
        files={"archivo": ("contrato.txt", io.BytesIO(b"contenido del contrato"), "text/plain")},
    )
    comprobar(publico.status_code == 201, "Cargar documento interno")
    comprobar(len(publico.json()["checksum_sha256"]) == 64, "Se calcula el checksum SHA-256")

    confidencial = cliente.post(
        "/api/documentos",
        headers=cabecera(token_abogado),
        data={
            "expediente_id": expediente_id,
            "tipo": "declaracion",
            "nivel_sensibilidad": "confidencial",
        },
        files={"archivo": ("declaracion.txt", io.BytesIO(b"secreto"), "text/plain")},
    )
    comprobar(confidencial.status_code == 201, "Cargar documento confidencial")
    confidencial_id = confidencial.json()["id"]

    comprobar(
        len(cliente.get("/api/documentos", headers=cabecera(token_abogado)).json()) == 2,
        "El abogado ve los dos documentos",
    )
    comprobar(
        len(cliente.get("/api/documentos", headers=cabecera(token_asistente)).json()) == 1,
        "El asistente no ve el documento confidencial",
    )
    comprobar(
        cliente.get(
            f"/api/documentos/{confidencial_id}/descargar", headers=cabecera(token_asistente)
        ).status_code == 403,
        "El asistente no puede descargar el documento confidencial (403)",
    )
    descarga = cliente.get(
        f"/api/documentos/{publico.json()['id']}/descargar", headers=cabecera(token_abogado)
    )
    comprobar(descarga.status_code == 200, "Descargar documento autorizado")

    # --- Módulo 5: permisos granulares por expediente ---
    comprobar(
        cliente.put(
            f"/api/expedientes/{expediente_id}",
            headers=cabecera(token_asistente),
            json={"asunto": "Intento del asistente"},
        ).status_code == 403,
        "El asistente autorizado no puede editar el expediente (403)",
    )
    conceder = cliente.put(
        f"/api/expedientes/{expediente_id}/permisos",
        headers=cabecera(token_abogado),
        json={"permisos": {asistente["id"]: {"editar": True}}},
    )
    comprobar(conceder.status_code == 200, "El responsable administra la matriz de permisos")
    comprobar(
        conceder.json()["permisos"][asistente["id"]]["editar"] is True,
        "La matriz concede 'editar' al asistente",
    )
    comprobar(
        cliente.put(
            f"/api/expedientes/{expediente_id}",
            headers=cabecera(token_asistente),
            json={"asunto": "Edición autorizada"},
        ).status_code == 200,
        "Con el permiso concedido el asistente edita el expediente",
    )
    comprobar(
        cliente.put(
            f"/api/expedientes/{expediente_id}/permisos",
            headers=cabecera(token_asistente),
            json={"permisos": {asistente["id"]: {"editar": True}}},
        ).status_code == 403,
        "Un usuario autorizado no administra la matriz de permisos (403)",
    )
    comprobar(
        cliente.put(
            f"/api/expedientes/{expediente_id}/permisos",
            headers=cabecera(token_abogado),
            json={"permisos": {"usuario-inexistente": {"leer": True}}},
        ).status_code == 422,
        "La matriz rechaza usuarios no autorizados (422)",
    )

    # --- Módulo 4: bóveda cifrada de doble fondo ---
    PW_VISIBLE = "BovedaVisible123!"
    PW_RESERVADA = "BovedaReservada123!"
    boveda = cliente.post(
        "/api/bovedas",
        headers=cabecera(token_abogado),
        json={
            "nombre": "Reserva estratégica (smoke)",
            "expediente_id": expediente_id,
            "password_visible": PW_VISIBLE,
            "password_confidencial": PW_RESERVADA,
            "contenido_visible": "Contenido principal de la bóveda.",
            "contenido_confidencial": "Contenido reservado de la bóveda.",
        },
    )
    comprobar(boveda.status_code == 201, "Crear bóveda de doble fondo")
    boveda_id = boveda.json()["id"]
    comprobar(
        not ({"vistas", "salt", "nonce", "datos", "password"} & set(boveda.json())),
        "La bóveda no expone material cifrado ni credenciales",
    )

    vista_visible = cliente.post(
        f"/api/bovedas/{boveda_id}/desbloquear",
        headers=cabecera(token_abogado),
        json={"password": PW_VISIBLE},
    )
    vista_reservada = cliente.post(
        f"/api/bovedas/{boveda_id}/desbloquear",
        headers=cabecera(token_abogado),
        json={"password": PW_RESERVADA},
    )
    comprobar(vista_visible.status_code == 200, "Desbloquear la vista principal")
    comprobar(
        [e["contenido"] for e in vista_visible.json()["entradas"]]
        == ["Contenido principal de la bóveda."],
        "La vista principal devuelve su propio contenido",
    )
    comprobar(
        [e["contenido"] for e in vista_reservada.json()["entradas"]]
        == ["Contenido reservado de la bóveda."],
        "La vista reservada devuelve un contenido distinto (doble fondo)",
    )
    comprobar(
        cliente.post(
            f"/api/bovedas/{boveda_id}/desbloquear",
            headers=cabecera(token_abogado),
            json={"password": "clave incorrecta"},
        ).status_code
        == 401,
        "Contraseña incorrecta devuelve 401",
    )
    comprobar(
        cliente.post(
            f"/api/bovedas/{boveda_id}/desbloquear",
            headers=cabecera(token_asistente),
            json={"password": PW_VISIBLE},
        ).status_code
        == 200,
        "El asistente autorizado en el expediente puede desbloquear",
    )
    comprobar(
        cliente.post(
            "/api/bovedas",
            headers=cabecera(token_asistente),
            json={
                "nombre": "No permitida",
                "password_visible": PW_VISIBLE,
                "password_confidencial": PW_RESERVADA,
            },
        ).status_code
        == 403,
        "El asistente no puede crear bóvedas (403)",
    )
    comprobar(
        cliente.post(
            "/api/bovedas",
            headers=cabecera(token_abogado),
            json={
                "nombre": "Contraseñas repetidas",
                "password_visible": PW_VISIBLE,
                "password_confidencial": PW_VISIBLE,
            },
        ).status_code
        == 422,
        "Las dos contraseñas deben ser diferentes (422)",
    )

    # --- Módulo 7: bloqueo y alertas ---
    for _ in range(3):
        login("abogado.smoke", "mala")
    bloqueado = login("abogado.smoke", "Abogado123!")
    comprobar(bloqueado.status_code == 423, "La cuenta se bloquea tras 3 intentos fallidos (423)")

    resumen = cliente.get("/api/alertas/resumen", headers=cabecera(token_admin))
    comprobar(resumen.status_code == 200 and resumen.json()["total"] > 0, "Resumen de alertas disponible")

    alertas = cliente.get(
        "/api/alertas?tipo=cuenta_bloqueada", headers=cabecera(token_admin)
    ).json()
    comprobar(len(alertas) >= 1, "Se registra la alerta de cuenta bloqueada")
    comprobar(
        all("password" not in alerta["mensaje"].lower() for alerta in alertas),
        "Las alertas no contienen contraseñas",
    )
    comprobar(
        cliente.get("/api/alertas", headers=cabecera(token_asistente)).status_code == 403,
        "Un usuario no administrador no puede ver las alertas (403)",
    )

    desbloqueo = cliente.post(
        f"/api/usuarios/{abogado['id']}/desbloquear", headers=cabecera(token_admin)
    )
    comprobar(desbloqueo.status_code == 200, "El administrador desbloquea la cuenta")
    comprobar(login("abogado.smoke", "Abogado123!").status_code == 200, "La cuenta desbloqueada puede entrar")

    # --- Módulo 6: auditoría inalterable ---
    registros = cliente.get("/api/auditoria", headers=cabecera(token_admin))
    comprobar(registros.status_code == 200, "El administrador consulta la auditoría")
    acciones = {registro["accion"] for registro in registros.json()}
    comprobar("login" in acciones, "La auditoría registra los inicios de sesión")
    comprobar("boveda_creada" in acciones, "La auditoría registra las acciones de bóveda")
    comprobar(
        cliente.get("/api/auditoria", headers=cabecera(token_asistente)).status_code == 403,
        "Un usuario no administrador no puede ver la auditoría (403)",
    )
    comprobar(
        all(len(registro["hash_actual"]) == 64 for registro in registros.json()),
        "Cada registro de auditoría lleva su hash de encadenado",
    )
    verificacion = cliente.get("/api/auditoria/verificar", headers=cabecera(token_admin))
    comprobar(
        verificacion.status_code == 200 and verificacion.json()["integro"] is True,
        "La cadena de auditoría es íntegra",
    )
    resumen_auditoria = cliente.get(
        "/api/auditoria/resumen", headers=cabecera(token_admin)
    ).json()
    comprobar(
        set(resumen_auditoria["por_resultado"]) == {"ok", "denegado", "error"},
        "El resumen de auditoría clasifica por resultado",
    )

    # --- Cierre de sesión ---
    comprobar(
        cliente.post("/api/auth/logout", headers=cabecera(token_admin)).status_code == 204,
        "Cierre de sesión",
    )
    comprobar(
        cliente.get("/api/auth/me", headers=cabecera(token_admin)).status_code == 401,
        "El token revocado deja de ser válido",
    )

    print(f"\nResultado: {'TODAS LAS PRUEBAS OK' if _fallos == 0 else f'{_fallos} fallo(s)'}")
    return 1 if _fallos else 0


if __name__ == "__main__":
    raise SystemExit(main())
