"""Pruebas de la API de la bóveda cifrada de doble fondo (Módulo 4)."""

from __future__ import annotations

import json

import pytest

from app.core.container import boveda_repository

PW_VISIBLE = "VistaPublica123!"
PW_CONFIDENCIAL = "VistaReservada123!"
TEXTO_VISIBLE = "Contenido principal: agenda y contactos."
TEXTO_CONFIDENCIAL = "Contenido reservado: estrategia interna confidencial."


@pytest.fixture
def crear_boveda(client, abogado, expediente):
    """Fábrica que crea bóvedas para cada prueba que las necesite."""

    def _crear(**overrides):
        payload = {
            "nombre": "Bóveda de pruebas",
            "descripcion": "Bóveda ficticia para pruebas.",
            "expediente_id": expediente["id"],
            "password_visible": PW_VISIBLE,
            "password_confidencial": PW_CONFIDENCIAL,
            "contenido_visible": TEXTO_VISIBLE,
            "contenido_confidencial": TEXTO_CONFIDENCIAL,
        }
        payload.update(overrides)
        return client.post("/api/bovedas", headers=abogado["headers"], json=payload)

    return _crear


def _desbloquear(client, headers, boveda_id, password):
    return client.post(
        f"/api/bovedas/{boveda_id}/desbloquear", headers=headers, json={"password": password}
    )


# --- creación y metadatos ------------------------------------------------
def test_crear_boveda(client, crear_boveda):
    respuesta = crear_boveda()
    assert respuesta.status_code == 201, respuesta.text
    datos = respuesta.json()
    assert datos["nombre"] == "Bóveda de pruebas"
    assert datos["expediente_identificador"] == "EXP-TESTS-1"


def test_la_respuesta_no_expone_material_cifrado(crear_boveda):
    datos = crear_boveda().json()
    # No debe filtrarse ninguna vista cifrada ni credencial.
    prohibidos = {"vistas", "salt", "nonce", "datos", "password", "password_hash"}
    assert prohibidos.isdisjoint(datos)


def test_password_corta_rechazada(crear_boveda):
    assert crear_boveda(password_visible="corta").status_code == 422


def test_credenciales_iguales_rechazadas(crear_boveda):
    respuesta = crear_boveda(password_confidencial=PW_VISIBLE)
    assert respuesta.status_code == 422


def test_crear_requiere_rol_gestion(client, asistente, expediente):
    respuesta = client.post(
        "/api/bovedas",
        headers=asistente["headers"],
        json={
            "nombre": "No permitida",
            "expediente_id": expediente["id"],
            "password_visible": PW_VISIBLE,
            "password_confidencial": PW_CONFIDENCIAL,
        },
    )
    assert respuesta.status_code == 403


def test_listar_incluye_boveda(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    listado = client.get("/api/bovedas", headers=abogado["headers"]).json()
    assert boveda["id"] in {item["id"] for item in listado}


# --- doble fondo ---------------------------------------------------------
def test_dos_fondos_independientes(client, abogado, crear_boveda):
    boveda = crear_boveda().json()

    visible = _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE)
    reservada = _desbloquear(client, abogado["headers"], boveda["id"], PW_CONFIDENCIAL)

    assert visible.status_code == 200
    assert reservada.status_code == 200
    textos_visible = [e["contenido"] for e in visible.json()["entradas"]]
    textos_reservada = [e["contenido"] for e in reservada.json()["entradas"]]
    assert TEXTO_VISIBLE in textos_visible
    assert TEXTO_CONFIDENCIAL in textos_reservada
    assert textos_visible != textos_reservada


def test_password_incorrecta_devuelve_401(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    respuesta = _desbloquear(client, abogado["headers"], boveda["id"], "NoEsLaClave123")
    assert respuesta.status_code == 401


def test_password_incorrecta_no_revela_cual_vista(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    visible = _desbloquear(client, abogado["headers"], boveda["id"], "NoEsLaClave123")
    # El mensaje debe ser genérico para no filtrar información.
    assert "incorrecta" in visible.json()["detail"].lower()


# --- acceso por expediente y aislamiento --------------------------------
def test_asistente_autorizado_puede_desbloquear(client, asistente, crear_boveda):
    boveda = crear_boveda().json()
    assert _desbloquear(
        client, asistente["headers"], boveda["id"], PW_VISIBLE
    ).status_code == 200


def test_usuario_ajeno_no_ve_ni_abre_boveda(client, intruso, crear_boveda):
    boveda = crear_boveda().json()
    listado = client.get("/api/bovedas", headers=intruso["headers"]).json()
    assert boveda["id"] not in {item["id"] for item in listado}
    assert (
        client.get(f"/api/bovedas/{boveda['id']}", headers=intruso["headers"]).status_code
        == 403
    )
    assert _desbloquear(
        client, intruso["headers"], boveda["id"], PW_VISIBLE
    ).status_code == 403


def test_admin_ve_todas_las_bovedas(client, admin_headers, crear_boveda):
    boveda = crear_boveda().json()
    listado = client.get("/api/bovedas", headers=admin_headers).json()
    assert boveda["id"] in {item["id"] for item in listado}


# --- edición -------------------------------------------------------------
def test_agregar_entrada(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    nueva = client.post(
        f"/api/bovedas/{boveda['id']}/entradas",
        headers=abogado["headers"],
        json={"titulo": "Nueva nota", "contenido": "Texto añadido.", "password": PW_VISIBLE},
    )
    assert nueva.status_code == 201

    contenido = _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE).json()
    titulos = [entrada["titulo"] for entrada in contenido["entradas"]]
    assert "Nueva nota" in titulos


def test_agregar_entrada_password_incorrecta(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    respuesta = client.post(
        f"/api/bovedas/{boveda['id']}/entradas",
        headers=abogado["headers"],
        json={"titulo": "X", "contenido": "Y", "password": "Malísima123"},
    )
    assert respuesta.status_code == 401


# --- cambio de credenciales ---------------------------------------------
def test_cambiar_credenciales(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    nueva = "NuevaVistaVisible456!"

    assert _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE).status_code == 200

    cambio = client.put(
        f"/api/bovedas/{boveda['id']}/credenciales",
        headers=abogado["headers"],
        json={"password_actual": PW_VISIBLE, "password_nueva": nueva},
    )
    assert cambio.status_code == 204

    # La contraseña antigua deja de abrir esa vista...
    assert _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE).status_code == 401
    # ...y la nueva sí abre, conservando el contenido original.
    resultado = _desbloquear(client, abogado["headers"], boveda["id"], nueva)
    assert resultado.status_code == 200
    assert TEXTO_VISIBLE in [e["contenido"] for e in resultado.json()["entradas"]]
    # La otra vista sigue intacta.
    assert _desbloquear(
        client, abogado["headers"], boveda["id"], PW_CONFIDENCIAL
    ).status_code == 200


def test_cambiar_credenciales_password_actual_incorrecta(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    respuesta = client.put(
        f"/api/bovedas/{boveda['id']}/credenciales",
        headers=abogado["headers"],
        json={"password_actual": "NoEsLaClave123", "password_nueva": "OtraClave1234!"},
    )
    assert respuesta.status_code == 401


def test_no_se_puede_repetir_la_password_de_la_otra_vista(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    respuesta = client.put(
        f"/api/bovedas/{boveda['id']}/credenciales",
        headers=abogado["headers"],
        json={"password_actual": PW_VISIBLE, "password_nueva": PW_CONFIDENCIAL},
    )
    assert respuesta.status_code == 422


# --- eliminación ---------------------------------------------------------
def test_eliminar_solo_creador_o_admin(client, abogado, asistente, admin_headers, crear_boveda):
    boveda = crear_boveda().json()

    # El asistente no es creador ni administrador.
    assert (
        client.delete(f"/api/bovedas/{boveda['id']}", headers=asistente["headers"]).status_code
        == 403
    )
    # El administrador sí puede.
    assert (
        client.delete(f"/api/bovedas/{boveda['id']}", headers=admin_headers).status_code == 204
    )
    assert client.get(
        f"/api/bovedas/{boveda['id']}", headers=abogado["headers"]
    ).status_code == 404


def test_creador_puede_eliminar(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    assert (
        client.delete(f"/api/bovedas/{boveda['id']}", headers=abogado["headers"]).status_code
        == 204
    )


# --- persistencia local --------------------------------------------------
def test_el_archivo_no_contiene_el_texto_en_claro(crear_boveda):
    crear_boveda()
    contenido = boveda_repository().path.read_text(encoding="utf-8")
    assert TEXTO_VISIBLE not in contenido
    assert TEXTO_CONFIDENCIAL not in contenido


def test_cada_boveda_tiene_dos_vistas_y_ningun_secreto(crear_boveda):
    crear_boveda()
    filas = json.loads(boveda_repository().path.read_text(encoding="utf-8"))
    assert filas, "Debe existir al menos una bóveda persistida."
    for fila in filas:
        assert len(fila["vistas"]) == 2
        for vista in fila["vistas"]:
            assert set(vista) == {"salt", "nonce", "datos"}


# --- no regresión: adjuntos (Fase 6) --------------------------------------
def test_desbloquear_siempre_devuelve_adjuntos_y_version(client, abogado, crear_boveda):
    """La respuesta ampliada mantiene el contrato y añade los adjuntos."""

    boveda = crear_boveda().json()
    respuesta = _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE)
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["adjuntos"] == []
    assert cuerpo["version"] == 2


def test_la_respuesta_no_expone_la_clave_de_los_adjuntos(client, abogado, crear_boveda):
    boveda = crear_boveda().json()
    cuerpo = _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE).json()
    # El bloque interno de adjuntos (clave, nonce base, contador) no sale.
    assert "clave" not in cuerpo
    assert "iv_base" not in cuerpo
    assert "contador" not in cuerpo


def test_crear_boveda_admite_capacidad_de_adjuntos(client, abogado, crear_boveda):
    assert crear_boveda(adjuntos_mb=1).status_code == 201
    assert crear_boveda(adjuntos_mb=7).status_code == 422


# --- padding por cubetas (mejora #15) ------------------------------------
def test_ambas_vistas_ocupan_exactamente_lo_mismo(crear_boveda):
    crear_boveda(contenido_visible="Corto.", contenido_confidencial="X" * 5000)
    filas = json.loads(boveda_repository().path.read_text(encoding="utf-8"))
    vista_a, vista_b = filas[0]["vistas"]
    assert len(vista_a["datos"]) == len(vista_b["datos"])


def test_la_boveda_persiste_su_bucket(crear_boveda):
    crear_boveda()
    filas = json.loads(boveda_repository().path.read_text(encoding="utf-8"))
    assert filas[0]["bucket_mb"] == 1


def test_bucket_mb_no_se_expone_en_la_api(crear_boveda):
    datos = crear_boveda(bucket_mb=5).json()
    assert "bucket_mb" not in datos


def test_la_respuesta_no_expone_el_bucket_en_el_listado(client, abogado, crear_boveda):
    crear_boveda()
    listado = client.get("/api/bovedas", headers=abogado["headers"]).json()
    assert all("bucket_mb" not in item for item in listado)


def test_bucket_invalido_rechazado(crear_boveda):
    assert crear_boveda(bucket_mb=-1).status_code == 422


def test_las_bovedas_antiguas_siguen_abriendo(client, abogado, crear_boveda):
    """Una bóveda creada sin padding (formato heredado) sigue abriéndose."""

    boveda = crear_boveda(bucket_mb=0).json()
    resultado = _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE)
    assert resultado.status_code == 200
    assert TEXTO_VISIBLE in [e["contenido"] for e in resultado.json()["entradas"]]
    # Y se sigue editando sin perder contenido.
    assert (
        client.post(
            f"/api/bovedas/{boveda['id']}/entradas",
            headers=abogado["headers"],
            json={"titulo": "Nota", "contenido": "Más texto.", "password": PW_VISIBLE},
        ).status_code
        == 201
    )
    contenido = _desbloquear(client, abogado["headers"], boveda["id"], PW_VISIBLE).json()
    assert "Más texto." in [e["contenido"] for e in contenido["entradas"]]
