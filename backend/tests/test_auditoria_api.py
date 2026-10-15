"""Pruebas de la API de auditoría (Módulo 6)."""

from __future__ import annotations

import json

from app.core.constants import AccionAuditoria, ResultadoAuditoria
from app.core.container import auditoria_repository, auditoria_service


def test_solo_el_admin_consulta_la_auditoria(client, admin_headers, abogado, asistente):
    assert client.get("/api/auditoria", headers=abogado["headers"]).status_code == 403
    assert client.get("/api/auditoria", headers=asistente["headers"]).status_code == 403
    assert client.get("/api/auditoria", headers=admin_headers).status_code == 200


def test_el_login_queda_registrado(client, admin_headers):
    registros = client.get(
        "/api/auditoria", params={"accion": "login"}, headers=admin_headers
    ).json()
    assert any(
        reg["accion"] == "login" and reg["resultado"] == "ok" for reg in registros
    )


def test_el_logout_queda_registrado(client, admin_headers):
    token = client.post(
        "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
    ).json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    assert client.post("/api/auth/logout", headers=headers).status_code == 204

    registros = client.get(
        "/api/auditoria", params={"accion": "logout"}, headers=admin_headers
    ).json()
    assert any(reg["resultado"] == "ok" for reg in registros)


def test_una_accion_denegada_queda_auditada(client, abogado, intruso, expediente):
    boveda = client.post(
        "/api/bovedas",
        headers=abogado["headers"],
        json={
            "nombre": "Bóveda para auditoría",
            "expediente_id": expediente["id"],
            "password_visible": "AuditoriaUno123!",
            "password_confidencial": "AuditoriaDos123!",
        },
    ).json()

    # El intruso no tiene acceso al expediente ni a la bóveda.
    assert (
        client.get(f"/api/bovedas/{boveda['id']}", headers=intruso["headers"]).status_code
        == 403
    )

    registros = auditoria_service().listar(
        accion=AccionAuditoria.ACCESO_DENEGADO, entidad="boveda"
    )
    assert any(
        reg.entidad_id == boveda["id"] and reg.resultado == ResultadoAuditoria.DENEGADO
        for reg in registros
    )


def test_intento_de_boveda_con_clave_erronea_queda_auditado(client, abogado, expediente):
    boveda = client.post(
        "/api/bovedas",
        headers=abogado["headers"],
        json={
            "nombre": "Bóveda clave errónea",
            "expediente_id": expediente["id"],
            "password_visible": "AuditoriaUno123!",
            "password_confidencial": "AuditoriaDos123!",
        },
    ).json()
    assert (
        client.post(
            f"/api/bovedas/{boveda['id']}/desbloquear",
            headers=abogado["headers"],
            json={"password": "clave incorrecta"},
        ).status_code
        == 401
    )
    registros = auditoria_service().listar(
        accion=AccionAuditoria.BOVEDA_ACCESO_FALLIDO, entidad="boveda"
    )
    assert any(
        reg.entidad_id == boveda["id"] and reg.resultado == ResultadoAuditoria.DENEGADO
        for reg in registros
    )


def test_verificar_integridad(client, admin_headers):
    datos = client.get("/api/auditoria/verificar", headers=admin_headers).json()
    assert datos["integro"] is True
    assert datos["indice_roto"] is None
    assert datos["total"] >= 1
    assert datos["verificado_en"]


def test_resumen_coincide_con_el_listado(client, admin_headers):
    registros = client.get("/api/auditoria", headers=admin_headers).json()
    resumen = client.get("/api/auditoria/resumen", headers=admin_headers).json()
    assert resumen["total"] == len(registros)
    assert set(resumen["por_resultado"]) == {"ok", "denegado", "error"}


def test_los_registros_incluyen_el_encadenado(client, admin_headers):
    registros = client.get("/api/auditoria", headers=admin_headers).json()
    assert registros
    for registro in registros:
        assert len(registro["hash_actual"]) == 64


def test_edicion_manual_detectada_via_api(client, admin_headers):
    repositorio = auditoria_repository()
    original = repositorio.path.read_text(encoding="utf-8")
    try:
        filas = json.loads(original)
        assert len(filas) >= 2
        filas[0]["detalle"] = "manipulado"
        repositorio.path.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")
        datos = client.get("/api/auditoria/verificar", headers=admin_headers).json()
        assert datos["integro"] is False
        assert datos["indice_roto"] == 0
    finally:
        repositorio.path.write_text(original, encoding="utf-8")

    # Restaurada la integridad, la verificación vuelve a ser correcta.
    assert (
        client.get("/api/auditoria/verificar", headers=admin_headers).json()["integro"]
        is True
    )
