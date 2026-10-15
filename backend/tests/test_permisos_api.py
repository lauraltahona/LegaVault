"""Pruebas de la matriz de permisos granular por expediente (Módulo 5)."""

from __future__ import annotations

from fastapi.testclient import TestClient


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _crear_usuario(client: TestClient, admin_token: str, username: str, rol: str) -> str:
    r = client.post(
        "/api/usuarios",
        headers=_h(admin_token),
        json={
            "username": username,
            "nombre_completo": username.title(),
            "email": f"{username}@legalvault.test",
            "rol": rol,
            "password": "Abogado123!",
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _crear_expediente(client: TestClient, token: str, autorizados: list[str], ident: str) -> dict:
    r = client.post(
        "/api/expedientes",
        headers=_h(token),
        json={
            "identificador": ident,
            "asunto": f"Asunto {ident}",
            "cliente": "Cliente",
            "tipo_proceso": "civil",
            "usuarios_autorizados": autorizados,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()


def test_matriz_concede_y_revoca_editar(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_resp = _login(client, "abogado.demo", "Abogado123!")
    usuario_id = _crear_usuario(client, tok_admin, "fase4.grant", "abogado")
    tok_user = _login(client, "fase4.grant", "Abogado123!")

    exp = _crear_expediente(client, tok_resp, [usuario_id], "EXP-PERM-01")

    # Por defecto el usuario autorizado puede leer pero no editar.
    r = client.get(f"/api/expedientes/{exp['id']}", headers=_h(tok_user))
    assert r.status_code == 200

    r = client.put(
        f"/api/expedientes/{exp['id']}", headers=_h(tok_user), json={"asunto": "X"}
    )
    assert r.status_code == 403

    # El responsable concede 'editar'.
    r = client.put(
        f"/api/expedientes/{exp['id']}/permisos",
        headers=_h(tok_resp),
        json={"permisos": {usuario_id: {"editar": True}}},
    )
    assert r.status_code == 200, r.text
    assert r.json()["permisos"][usuario_id]["editar"] is True

    r = client.put(
        f"/api/expedientes/{exp['id']}", headers=_h(tok_user), json={"asunto": "Permitido"}
    )
    assert r.status_code == 200

    # El responsable revoca 'leer': el usuario pierde el acceso.
    r = client.put(
        f"/api/expedientes/{exp['id']}/permisos",
        headers=_h(tok_resp),
        json={"permisos": {usuario_id: {"leer": False}}},
    )
    assert r.status_code == 200
    r = client.get(f"/api/expedientes/{exp['id']}", headers=_h(tok_user))
    assert r.status_code == 403


def test_matriz_solo_admin_o_responsable(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_resp = _login(client, "abogado.demo", "Abogado123!")
    usuario_id = _crear_usuario(client, tok_admin, "fase4.denegado", "abogado")
    tok_user = _login(client, "fase4.denegado", "Abogado123!")

    exp = _crear_expediente(client, tok_resp, [usuario_id], "EXP-PERM-02")

    # Un usuario autorizado (no responsable) no administra permisos.
    r = client.put(
        f"/api/expedientes/{exp['id']}/permisos",
        headers=_h(tok_user),
        json={"permisos": {usuario_id: {"editar": True}}},
    )
    assert r.status_code == 403

    # El administrador sí puede.
    r = client.put(
        f"/api/expedientes/{exp['id']}/permisos",
        headers=_h(tok_admin),
        json={"permisos": {usuario_id: {"editar": True}}},
    )
    assert r.status_code == 200


def test_matriz_rechaza_usuario_no_autorizado(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_resp = _login(client, "abogado.demo", "Abogado123!")
    ajeno_id = _crear_usuario(client, tok_admin, "fase4.ajeno", "abogado")

    exp = _crear_expediente(client, tok_resp, [], "EXP-PERM-03")

    # No se puede conceder permisos a un usuario no autorizado en el expediente.
    r = client.put(
        f"/api/expedientes/{exp['id']}/permisos",
        headers=_h(tok_resp),
        json={"permisos": {ajeno_id: {"leer": True}}},
    )
    assert r.status_code == 422


def test_matriz_se_audita(client: TestClient) -> None:
    tok_admin = _login(client, "admin", "Admin123!")
    tok_resp = _login(client, "abogado.demo", "Abogado123!")
    usuario_id = _crear_usuario(client, tok_admin, "fase4.audit", "abogado")

    exp = _crear_expediente(client, tok_resp, [usuario_id], "EXP-PERM-04")

    r = client.put(
        f"/api/expedientes/{exp['id']}/permisos",
        headers=_h(tok_resp),
        json={"permisos": {usuario_id: {"editar": True}}},
    )
    assert r.status_code == 200

    r = client.get(
        "/api/auditoria",
        params={"accion": "expediente_permisos"},
        headers=_h(tok_admin),
    )
    assert r.status_code == 200
    registros = r.json()
    assert any(
        reg["accion"] == "expediente_permisos" and reg["entidad_id"] == exp["id"]
        for reg in registros
    )
