"""Pruebas de la re-verificación de integridad SHA-256 de documentos (Módulo 3).

Cubre la mejora "Re-verificar SHA-256 al descargar + botón Verificar
integridad": comprobación bajo demanda, bloqueo de descarga con 409 ante
corrupción, alerta crítica ``documento_corrupto``, registro en auditoría y
ausencia de regresiones en el flujo normal de descarga.
"""

from __future__ import annotations

import hashlib

from fastapi.testclient import TestClient

from app.core.config import settings
from app.services.documento_service import DocumentoService

_CONTENIDO = b"contenido verificable para la prueba de integridad"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _subir(client: TestClient, token: str, expediente_id: str, nombre: str) -> dict:
    r = client.post(
        "/api/documentos",
        headers=_h(token),
        data={
            "expediente_id": expediente_id,
            "tipo": "contrato",
            "nivel_sensibilidad": "interno",
            "descripcion": "Prueba de integridad",
        },
        files={"archivo": (nombre, _CONTENIDO, "text/plain")},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _ruta_archivo(documento_id: str):
    candidatos = sorted(settings.uploads_dir.glob(f"{documento_id}*"))
    assert candidatos, f"No se encontró el archivo físico de {documento_id}"
    return candidatos[0]


def test_verificar_integridad_correcta(client: TestClient, abogado: dict, expediente: dict) -> None:
    """Un documento recién cargado verifica correctamente y queda auditado."""

    token = abogado["headers"]["Authorization"].split()[1]
    doc = _subir(client, token, expediente["id"], "integridad_ok.txt")

    r = client.get(
        f"/api/documentos/{doc['id']}/verificar-integridad", headers=abogado["headers"]
    )
    assert r.status_code == 200, r.text
    datos = r.json()

    assert datos["integro"] is True
    assert datos["documento_id"] == doc["id"]
    assert datos["checksum_esperado"] == doc["checksum_sha256"]
    assert datos["checksum_calculado"] == hashlib.sha256(_CONTENIDO).hexdigest()
    assert datos["checksum_calculado"] == datos["checksum_esperado"]
    assert datos["tamano_esperado"] == datos["tamano_calculado"] == len(_CONTENIDO)
    assert len(datos["checksum_calculado"]) == 64
    assert datos["mensaje"]

    # Auditoría: evento documento_verificado con resultado ok.
    r = client.get(
        "/api/auditoria",
        params={"accion": "documento_verificado", "entidad": "documento"},
        headers=_h(_login(client, "admin", "Admin123!")),
    )
    assert r.status_code == 200
    assert any(
        registro["entidad_id"] == doc["id"] and registro["resultado"] == "ok"
        for registro in r.json()["items"]
    )

    # No se genera ninguna alerta de corrupción.
    r = client.get(
        "/api/alertas", params={"tipo": "documento_corrupto"}, headers=_h(_login(client, "admin", "Admin123!"))
    )
    assert r.status_code == 200
    assert not any("integridad_ok.txt" in alerta["mensaje"] for alerta in r.json()["items"])


def test_verificar_integridad_corrupta_genera_alerta_y_auditoria(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """Alterar el archivo en disco se detecta: 200 con integro=false + alerta crítica."""

    token = abogado["headers"]["Authorization"].split()[1]
    doc = _subir(client, token, expediente["id"], "integridad_rota.txt")
    _ruta_archivo(doc["id"]).write_bytes(b"contenido alterado por un atacante")

    r = client.get(
        f"/api/documentos/{doc['id']}/verificar-integridad", headers=abogado["headers"]
    )
    assert r.status_code == 200, r.text
    datos = r.json()

    assert datos["integro"] is False
    assert datos["checksum_calculado"] != datos["checksum_esperado"]
    assert datos["checksum_esperado"] == doc["checksum_sha256"]
    assert datos["checksum_calculado"] == hashlib.sha256(b"contenido alterado por un atacante").hexdigest()
    assert datos["tamano_calculado"] != datos["tamano_esperado"]
    assert "alerta" in datos["mensaje"].lower()

    admin = _h(_login(client, "admin", "Admin123!"))
    r = client.get("/api/alertas", params={"tipo": "documento_corrupto"}, headers=admin)
    assert r.status_code == 200
    corrupcion = [a for a in r.json()["items"] if "integridad_rota.txt" in a["mensaje"]]
    assert corrupcion, "Debe existir la alerta DOCUMENTO_CORRUPO"
    assert all(alerta["severidad"] == "critica" for alerta in corrupcion)

    r = client.get(
        "/api/auditoria",
        params={"accion": "documento_corrupto", "entidad": "documento"},
        headers=admin,
    )
    assert r.status_code == 200
    assert any(
        registro["entidad_id"] == doc["id"] and registro["resultado"] == "error"
        for registro in r.json()["items"]
    ), "La corrupción debe quedar en la auditoría con resultado error"


def test_descarga_bloqueada_si_integridad_rota(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """La descarga re-verifica el hash: si no coincide devuelve 409 y alerta."""

    token = abogado["headers"]["Authorization"].split()[1]
    doc = _subir(client, token, expediente["id"], "descarga_bloqueada.txt")
    _ruta_archivo(doc["id"]).write_bytes(b"bytes distintos a los originales")

    r = client.get(f"/api/documentos/{doc['id']}/descargar", headers=abogado["headers"])
    assert r.status_code == 409, r.text
    assert "integridad" in r.json()["detail"].lower()
    assert "sha-256" in r.json()["detail"].lower()

    r = client.get(
        "/api/alertas", params={"tipo": "documento_corrupto"}, headers=_h(_login(client, "admin", "Admin123!"))
    )
    assert any("descarga_bloqueada.txt" in alerta["mensaje"] for alerta in r.json()["items"])


def test_descarga_normal_sigue_funcionando(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """Regresión: con el archivo intacto la descarga devuelve 200 y los bytes originales."""

    token = abogado["headers"]["Authorization"].split()[1]
    doc = _subir(client, token, expediente["id"], "descarga_normal.txt")

    r = client.get(f"/api/documentos/{doc['id']}/descargar", headers=abogado["headers"])
    assert r.status_code == 200
    assert r.content == _CONTENIDO


def test_verificar_integridad_respeta_permisos(
    client: TestClient, abogado: dict, intruso: dict, expediente: dict
) -> None:
    """La verificación exige acceso al expediente (permisos siempre en servidor)."""

    token = abogado["headers"]["Authorization"].split()[1]
    doc = _subir(client, token, expediente["id"], "integridad_privado.txt")

    # Sin token → 401.
    r = client.get(f"/api/documentos/{doc['id']}/verificar-integridad")
    assert r.status_code == 401

    # Abogado ajeno al expediente → 403.
    r = client.get(
        f"/api/documentos/{doc['id']}/verificar-integridad", headers=intruso["headers"]
    )
    assert r.status_code == 403


def test_archivo_fisico_ausente(client: TestClient, abogado: dict, expediente: dict) -> None:
    """Si el archivo desaparece, verificar y descargar devuelven 404 sin romper nada."""

    token = abogado["headers"]["Authorization"].split()[1]
    doc = _subir(client, token, expediente["id"], "archivo_ausente.txt")
    _ruta_archivo(doc["id"]).unlink()

    r = client.get(f"/api/documentos/{doc['id']}/verificar-integridad", headers=abogado["headers"])
    assert r.status_code == 404

    r = client.get(f"/api/documentos/{doc['id']}/descargar", headers=abogado["headers"])
    assert r.status_code == 404


def test_hash_sha256_streaming_supera_un_bloque(tmp_path) -> None:
    """El hash por bloques (1 MB) es idéntico al de hashlib sobre los bytes completos."""

    datos = (b"LegalVault-integridad-" * 100_000)[: 2_500_000]  # 2.5 MB > 1 bloque
    archivo = tmp_path / "grande.bin"
    archivo.write_bytes(datos)

    assert DocumentoService._hash_sha256(archivo) == hashlib.sha256(datos).hexdigest()
    # Bloque pequeño forzado: la frontera entre bloques no altera el resultado.
    assert DocumentoService._hash_sha256(archivo, tamano_bloque=7) == hashlib.sha256(
        datos
    ).hexdigest()
