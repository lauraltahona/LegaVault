"""Pruebas de flujos API: módulos 1, 2, 3 y 7 (autenticación, expedientes, documentos, alertas)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _crear_usuario(
    client: TestClient, admin_token: str, username: str, rol: str, password: str
) -> dict:
    r = client.post(
        "/api/usuarios",
        headers=_h(admin_token),
        json={
            "username": username,
            "nombre_completo": username.title(),
            "email": f"{username}@legalvault.test",
            "rol": rol,
            "password": password,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_auth_login_me_y_401(client: TestClient) -> None:
    r = client.get("/api/auth/me")
    assert r.status_code == 401

    tok = _login(client, "admin", "Admin123!")
    r = client.get("/api/auth/me", headers=_h(tok))
    assert r.status_code == 200
    assert r.json()["rol"] == "admin"


def test_auth_logout_revoca_token(client: TestClient) -> None:
    tok = _login(client, "admin", "Admin123!")
    r = client.post("/api/auth/logout", headers=_h(tok))
    assert r.status_code == 204
    r = client.get("/api/auth/me", headers=_h(tok))
    assert r.status_code == 401


def test_login_fallido_registra_intento(client: TestClient) -> None:
    r = client.post(
        "/api/auth/login", json={"username": "admin", "password": "incorrecta"}
    )
    assert r.status_code == 401


def test_usuarios_solo_admin_y_duplicados(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    _crear_usuario(client, tok_admin, "fase1.basico", "abogado", "Abogado123!")

    tok = _login(client, "fase1.basico", "Abogado123!")
    # Un no admin no puede listar usuarios
    r = client.get("/api/usuarios", headers=_h(tok))
    assert r.status_code == 403

    # Email duplicado → 409
    r = client.post(
        "/api/usuarios",
        headers=_h(tok_admin),
        json={
            "username": "fase1.otro",
            "nombre_completo": "Otro",
            "email": "fase1.basico@legalvault.test",
            "rol": "abogado",
            "password": "Abogado123!",
        },
    )
    assert r.status_code == 409


def test_expedientes_crear_listar_filtrar(client: TestClient) -> None:
    tok_abogado = _login(client, "abogado.demo", "Abogado123!")
    r = client.post(
        "/api/expedientes",
        headers=_h(tok_abogado),
        json={
            "identificador": "EXP-FASE1-01",
            "asunto": "Asunto de prueba",
            "cliente": "Cliente Demo",
            "tipo_proceso": "civil",
        },
    )
    assert r.status_code == 201
    exp = r.json()

    r = client.get("/api/expedientes", headers=_h(tok_abogado))
    assert r.status_code == 200
    assert any(e["id"] == exp["id"] for e in r.json())

    r = client.get("/api/expedientes", params={"estado": "abierto"}, headers=_h(tok_abogado))
    assert r.status_code == 200

    r = client.get(f"/api/expedientes/{exp['id']}", headers=_h(tok_abogado))
    assert r.status_code == 200
    assert "responsable" in r.text or "abogado_responsable" in r.text


def test_editar_expediente_solo_responsable(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_resp = _login(client, "abogado.demo", "Abogado123!")
    _crear_usuario(client, tok_admin, "fase1.ajeno", "abogado", "Abogado123!")
    tok_ajeno = _login(client, "fase1.ajeno", "Abogado123!")

    r = client.post(
        "/api/expedientes",
        headers=_h(tok_resp),
        json={
            "identificador": "EXP-FASE1-02",
            "asunto": "Propiedad",
            "cliente": "Cliente",
            "tipo_proceso": "civil",
        },
    )
    exp = r.json()

    # El responsable edita
    r = client.put(
        f"/api/expedientes/{exp['id']}",
        headers=_h(tok_resp),
        json={"asunto": "Actualizado por responsable"},
    )
    assert r.status_code == 200

    # Otro abogado no es responsable ni está autorizado → no puede editar
    r = client.put(
        f"/api/expedientes/{exp['id']}",
        headers=_h(tok_ajeno),
        json={"asunto": "Intento ajeno"},
    )
    assert r.status_code == 403


def test_documentos_flujo_y_permisos(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_abogado = _login(client, "abogado.demo", "Abogado123!")
    tok_asistente = _login(client, "asistente.demo", "Asistente123!")

    r = client.get("/api/usuarios", headers=_h(tok_admin))
    usuarios = {u["username"]: u["id"] for u in r.json()}
    asistente_id = usuarios["asistente.demo"]

    # Un abogado autorizado sin permiso de eliminación.
    _crear_usuario(client, tok_admin, "fase4.lector", "abogado", "Abogado123!")
    tok_lector = _login(client, "fase4.lector", "Abogado123!")
    r = client.get("/api/usuarios", headers=_h(tok_admin))
    lector_id = next(u["id"] for u in r.json() if u["username"] == "fase4.lector")

    r = client.post(
        "/api/expedientes",
        headers=_h(tok_abogado),
        json={
            "identificador": "EXP-FASE1-03",
            "asunto": "Documentos",
            "cliente": "Cliente",
            "tipo_proceso": "civil",
            "usuarios_autorizados": [asistente_id, lector_id],
        },
    )
    assert r.status_code == 201
    exp = r.json()

    # El asistente carga un documento interno permitido
    r = client.post(
        "/api/documentos",
        headers=_h(tok_asistente),
        data={
            "expediente_id": exp["id"],
            "tipo": "contrato",
            "nivel_sensibilidad": "interno",
            "descripcion": "Cargado por asistente",
        },
        files={"archivo": ("asistente.txt", b"contenido asistente", "text/plain")},
    )
    assert r.status_code == 201, r.text
    doc = r.json()

    # El asistente puede descargar su documento interno
    r = client.get(f"/api/documentos/{doc['id']}/descargar", headers=_h(tok_asistente))
    assert r.status_code == 200

    # El asistente no puede cargar un documento confidencial
    r = client.post(
        "/api/documentos",
        headers=_h(tok_asistente),
        data={
            "expediente_id": exp["id"],
            "tipo": "contrato",
            "nivel_sensibilidad": "confidencial",
            "descripcion": "No permitido",
        },
        files={"archivo": ("secreto.txt", b"secreto", "text/plain")},
    )
    assert r.status_code == 403

    # Un abogado autorizado, ajeno al documento y sin permiso 'eliminar' → 403
    r = client.delete(f"/api/documentos/{doc['id']}", headers=_h(tok_lector))
    assert r.status_code == 403

    # El responsable (con acción 'eliminar' por defecto) sí puede eliminarlo
    r = client.delete(f"/api/documentos/{doc['id']}", headers=_h(tok_abogado))
    assert r.status_code == 204


def test_alertas_solo_admin_y_resumen(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_asistente = _login(client, "asistente.demo", "Asistente123!")

    r = client.get("/api/alertas", headers=_h(tok_admin))
    assert r.status_code == 200

    r = client.get("/api/alertas/resumen", headers=_h(tok_admin))
    assert r.status_code == 200
    assert "total" in r.json()

    r = client.get("/api/alertas", headers=_h(tok_asistente))
    assert r.status_code == 403
