"""Configuración común de las pruebas (pytest).

Aísla cada ejecución en un directorio de datos temporal para no tocar los datos
reales. La variable de entorno debe fijarse **antes** de importar la aplicación
porque la configuración se lee en el momento de la importación.
"""

from __future__ import annotations

import os
import tempfile

_TMP = tempfile.mkdtemp(prefix="legalvault_tests_")
os.environ["LEGALVAULT_DATA_DIR"] = _TMP
os.environ["LEGALVAULT_MAX_INTENTOS"] = "3"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client() -> TestClient:
    """Cliente HTTP de pruebas; el bloque ``with`` dispara el lifespan.

    Asegura que existan usuarios demo para los tests que los utilizan.
    """

    with TestClient(app) as test_client:
        # Asegurar usuarios demo si no existen (idempotente)
        try:
            r = test_client.post(
                "/api/auth/login", json={"username": "admin", "password": "Admin123!"}
            )
            if r.status_code == 200:
                admin_h = {"Authorization": f"Bearer {r.json()['access_token']}"}
                # Crear usuarios demo si faltan
                usuarios = test_client.get("/api/usuarios", headers=admin_h)
                usernames = {u["username"] for u in usuarios.json()}
                if "abogado.demo" not in usernames:
                    test_client.post(
                        "/api/usuarios",
                        headers=admin_h,
                        json={
                            "username": "abogado.demo",
                            "nombre_completo": "Abogado Demo",
                            "email": "abogado.demo@legalvault.local",
                            "password": "Abogado123!",
                            "rol": "abogado",
                        },
                    )
                if "asistente.demo" not in usernames:
                    test_client.post(
                        "/api/usuarios",
                        headers=admin_h,
                        json={
                            "username": "asistente.demo",
                            "nombre_completo": "Asistente Demo",
                            "email": "asistente.demo@legalvault.local",
                            "password": "Asistente123!",
                            "rol": "asistente",
                        },
                    )
                test_client.post("/api/auth/logout", headers=admin_h)
        except Exception:
            pass
        yield test_client


def _cabecera(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str, password: str) -> dict[str, str]:
    respuesta = client.post(
        "/api/auth/login", json={"username": username, "password": password}
    )
    assert respuesta.status_code == 200, respuesta.text
    return _cabecera(respuesta.json()["access_token"])


def crear_usuario(
    client: TestClient,
    admin_headers: dict[str, str],
    *,
    username: str,
    password: str,
    rol: str,
    nombre_completo: str = "",
) -> dict:
    respuesta = client.post(
        "/api/usuarios",
        headers=admin_headers,
        json={
            "username": username,
            "nombre_completo": nombre_completo or username,
            "email": f"{username}@legalvault.local",
            "password": password,
            "rol": rol,
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


@pytest.fixture(scope="session")
def admin_headers(client: TestClient) -> dict[str, str]:
    return login(client, "admin", "Admin123!")


@pytest.fixture(scope="session")
def abogado(client: TestClient, admin_headers: dict[str, str]) -> dict:
    usuario = crear_usuario(
        client,
        admin_headers,
        username="abogado.tests",
        password="Abogado123!",
        rol="abogado",
        nombre_completo="Abogada de Pruebas",
    )
    return {"usuario": usuario, "headers": login(client, "abogado.tests", "Abogado123!")}


@pytest.fixture(scope="session")
def asistente(client: TestClient, admin_headers: dict[str, str]) -> dict:
    usuario = crear_usuario(
        client,
        admin_headers,
        username="asistente.tests",
        password="Asistente123!",
        rol="asistente",
        nombre_completo="Asistente de Pruebas",
    )
    return {"usuario": usuario, "headers": login(client, "asistente.tests", "Asistente123!")}


@pytest.fixture(scope="session")
def expediente(client: TestClient, abogado: dict, asistente: dict) -> dict:
    respuesta = client.post(
        "/api/expedientes",
        headers=abogado["headers"],
        json={
            "identificador": "EXP-TESTS-1",
            "asunto": "Expediente para pruebas de bóveda",
            "cliente": "Cliente de Pruebas S.A.",
            "tipo_proceso": "civil",
            "abogado_responsable_id": abogado["usuario"]["id"],
            "usuarios_autorizados": [asistente["usuario"]["id"]],
        },
    )
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


@pytest.fixture(scope="session")
def intruso(client: TestClient, admin_headers: dict[str, str]) -> dict:
    """Abogado sin relación con el expediente ni con las bóvedas."""

    usuario = crear_usuario(
        client,
        admin_headers,
        username="intruso.tests",
        password="Intruso123!",
        rol="abogado",
        nombre_completo="Abogado Ajeno",
    )
    return {"usuario": usuario, "headers": login(client, "intruso.tests", "Intruso123!")}
