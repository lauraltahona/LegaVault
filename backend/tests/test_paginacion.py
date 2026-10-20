"""Pruebas del contrato de paginación de listados (mejora #10 del plan).

Los cuatro listados que pueden crecer (auditoría, alertas, documentos y
expedientes) devuelven ahora ``{items, total, pagina, por_pagina, paginas}``
en lugar de un array plano. Estas pruebas fijan ese contrato, el alias
legacy ``limite`` y la validación de los parámetros.
"""

from __future__ import annotations

import pytest

from app.schemas.paginacion import RespuestaPaginada

CAMPOS = {"items", "total", "pagina", "por_pagina", "paginas"}


# --- esquema genérico -----------------------------------------------------
def test_respuesta_paginada_calcula_paginas() -> None:
    respuesta = RespuestaPaginada.crear([1, 2], total=5, pagina=2, por_pagina=2)
    assert respuesta.paginas == 3
    assert respuesta.total == 5
    assert respuesta.pagina == 2


def test_respuesta_paginada_sin_items() -> None:
    respuesta = RespuestaPaginada.crear([], total=0, pagina=1, por_pagina=20)
    assert respuesta.paginas == 0
    assert respuesta.items == []


# --- auditoría ------------------------------------------------------------
def test_auditoria_devuelve_metadatos_de_paginacion(client, admin_headers):
    datos = client.get("/api/auditoria", headers=admin_headers).json()
    assert CAMPOS.issubset(datos)
    assert datos["pagina"] == 1
    assert datos["por_pagina"] == 20
    assert isinstance(datos["items"], list)
    assert datos["total"] >= len(datos["items"]) >= 1
    assert datos["paginas"] >= 1


def test_auditoria_pagina_2_sin_solapamiento(client, admin_headers):
    # Garantiza al menos dos registros realizando un login (queda auditado).
    client.post("/api/auth/login", json={"username": "admin", "password": "Admin123!"})

    primera = client.get(
        "/api/auditoria", params={"por_pagina": 1, "pagina": 1}, headers=admin_headers
    ).json()
    segunda = client.get(
        "/api/auditoria", params={"por_pagina": 1, "pagina": 2}, headers=admin_headers
    ).json()
    assert primera["total"] == segunda["total"] >= 2
    assert len(primera["items"]) == 1
    assert len(segunda["items"]) == 1
    # Páginas distintas no deben repetir registros.
    assert primera["items"][0]["id"] != segunda["items"][0]["id"]


def test_auditoria_alias_limite(client, admin_headers):
    datos = client.get("/api/auditoria", params={"limite": 3}, headers=admin_headers).json()
    assert datos["por_pagina"] == 3
    assert datos["pagina"] == 1
    assert len(datos["items"]) <= 3


def test_pagina_invalida_rechazada(client, admin_headers):
    assert (
        client.get("/api/auditoria", params={"pagina": 0}, headers=admin_headers).status_code
        == 422
    )
    assert (
        client.get(
            "/api/auditoria", params={"por_pagina": 500}, headers=admin_headers
        ).status_code
        == 422
    )


# --- alertas --------------------------------------------------------------
def test_alertas_solo_admin(client, asistente):
    assert client.get("/api/alertas", headers=asistente["headers"]).status_code == 403


def test_alertas_devuelve_metadatos_de_paginacion(client, admin_headers):
    datos = client.get(
        "/api/alertas", params={"por_pagina": 5}, headers=admin_headers
    ).json()
    assert CAMPOS.issubset(datos)
    assert datos["por_pagina"] == 5
    assert len(datos["items"]) <= 5
    assert datos["total"] >= len(datos["items"])


def test_alertas_alias_limite(client, admin_headers):
    datos = client.get("/api/alertas", params={"limite": 2}, headers=admin_headers).json()
    assert datos["por_pagina"] == 2
    assert len(datos["items"]) <= 2


# --- documentos y expedientes ---------------------------------------------
def test_documentos_devuelve_metadatos_de_paginacion(client, abogado, expediente):
    datos = client.get(
        "/api/documentos", params={"por_pagina": 1}, headers=abogado["headers"]
    ).json()
    assert CAMPOS.issubset(datos)
    assert datos["por_pagina"] == 1
    assert len(datos["items"]) <= 1
    assert datos["total"] >= len(datos["items"])


def test_expedientes_devuelve_metadatos_de_paginacion(client, abogado, expediente):
    datos = client.get(
        "/api/expedientes", params={"por_pagina": 1}, headers=abogado["headers"]
    ).json()
    assert CAMPOS.issubset(datos)
    assert datos["por_pagina"] == 1
    assert datos["total"] >= 1
    assert datos["items"][0]["id"] == expediente["id"]


def test_expedientes_pagina_mas_alla_del_total_devuelve_vacio(client, abogado, expediente):
    datos = client.get(
        "/api/expedientes", params={"por_pagina": 1, "pagina": 99}, headers=abogado["headers"]
    ).json()
    assert datos["items"] == []
    assert datos["pagina"] == 99
    assert datos["total"] >= 1
