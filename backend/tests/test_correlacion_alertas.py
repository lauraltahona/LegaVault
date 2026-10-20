"""Pruebas de las reglas de correlación de alertas (Módulo 7, mejora #13).

Cubre el servicio ``CorrelacionAlertasService`` de forma aislada (repositorio
en directorio temporal) y su integración de extremo a extremo con el flujo
real de autenticación a través de la API.

Garantías verificadas:

- Aditividad: las alertas existentes no se modifican ni eliminan; solo se
  agregan alertas ``patron_sospechoso``.
- Umbrales exactos (2 denegados no disparan, 3 sí; 9 descargas no disparan,
  10 sí), ventanas de tiempo, enfriamiento y sujección por usuario.
- Línea base para la regla de "IP nunca vista" y su enfriamiento.
- Ausencia de bucles: las alertas de correlación no se retroalimentan.
- Retrocompatibilidad: alertas antiguas sin el campo ``regla`` siguen cargando.
"""

from __future__ import annotations

import json
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.constants import SeveridadAlerta, TipoAlerta
from app.models.alerta import Alerta
from app.models.base import utcnow
from app.repositories.alerta_repository import AlertaRepository
from app.services.alerta_service import AlertaService
from app.services.correlacion_service import CorrelacionAlertasService
from conftest import crear_usuario

_AHORA = utcnow()


def _h(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


# --- utilidades de unit tests sobre repositorio aislado --------------------


@pytest.fixture()
def repo(tmp_path) -> AlertaRepository:
    return AlertaRepository(tmp_path / "alertas.json")


@pytest.fixture()
def correlacion(repo) -> CorrelacionAlertasService:
    return CorrelacionAlertasService(repo)


def _emitir(
    repo: AlertaRepository,
    correlacion: CorrelacionAlertasService,
    tipo: TipoAlerta,
    *,
    usuario: str = "juan",
    ip: str = "",
    minutos_atras: float = 0.0,
) -> list[Alerta]:
    """Simula el registro de una alerta real: agrega y evalúa (como hace
    ``AlertaService.registrar``)."""

    alerta = Alerta(
        tipo=tipo,
        severidad=SeveridadAlerta.ADVERTENCIA,
        usuario=usuario,
        ip=ip,
    )
    alerta.creado_en = _AHORA - timedelta(minutes=minutos_atras)
    alerta.actualizado_en = alerta.creado_en
    repo.add(alerta)
    return correlacion.evaluar(alerta)


def _patrones(repo: AlertaRepository) -> list[Alerta]:
    return [
        alerta
        for alerta in repo.list_all()
        if alerta.tipo == TipoAlerta.PATRON_SOSPECHOSO
    ]


# --- regla: denegados_rapidos ---------------------------------------------


def test_dos_denegados_no_disparan(repo, correlacion) -> None:
    """Con un umbral de 3, dos eventos denegados no generan correlación."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    assert generadas == []
    assert _patrones(repo) == []


def test_tres_denegados_disparan_patron_sospechoso(repo, correlacion) -> None:
    """Tres eventos denegados del mismo usuario en la ventana generan la alerta."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)

    assert len(generadas) == 1
    patron = generadas[0]
    assert patron.tipo == TipoAlerta.PATRON_SOSPECHOSO
    assert patron.severidad == SeveridadAlerta.CRITICA
    assert patron.regla == "denegados_rapidos"
    assert patron.usuario == "juan"
    assert "denegados_rapidos" in patron.mensaje
    assert len(_patrones(repo)) == 1


def test_denegados_de_tipos_distintos_se_correlacionan(repo, correlacion) -> None:
    """La ráfaga mezcla tipos de denegación (login, acceso, bóveda, bloqueo)."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    _emitir(repo, correlacion, TipoAlerta.ACCESO_DENEGADO)
    generadas = _emitir(repo, correlacion, TipoAlerta.BOVEDA_ACCESO_FALLIDO)
    assert len(generadas) == 1
    assert generadas[0].regla == "denegados_rapidos"


def test_eventos_fuera_de_la_ventana_no_disparan(repo, correlacion) -> None:
    """Si los eventos exceden la ventana de 5 minutos, no hay correlación."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, minutos_atras=10)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, minutos_atras=7)
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    assert generadas == []
    assert _patrones(repo) == []


def test_usuarios_distintos_no_se_suman(repo, correlacion) -> None:
    """Cada usuario tiene su propio contador (el sujeto es el usuario)."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, usuario="ana")
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, usuario="ana")
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, usuario="luis")
    assert generadas == []
    assert _patrones(repo) == []


def test_enfriamiento_no_repite_la_alerta(repo, correlacion) -> None:
    """Mientras siga la ráfaga dentro de la ventana solo se alerta una vez."""

    for _ in range(3):
        _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    assert len(_patrones(repo)) == 1

    # La ráfaga continúa: no debe repetirse la alerta dentro del enfriamiento.
    for _ in range(5):
        _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    assert len(_patrones(repo)) == 1


def test_enfriamiento_expirado_vuelve_a_alertar(repo, correlacion) -> None:
    """Pasado el enfriamiento, una ráfaga nueva genera una alerta nueva."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    assert len(_patrones(repo)) == 1

    # Nueva ráfaga "más tarde": la alerta previa queda fuera del enfriamiento.
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, minutos_atras=-10)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, minutos_atras=-10)
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, minutos_atras=-10)
    assert len(generadas) == 1
    assert len(_patrones(repo)) == 2


# --- regla: descargas_masivas ---------------------------------------------


def test_nueve_descargas_no_disparan(repo, correlacion) -> None:
    for indice in range(9):
        _emitir(repo, correlacion, TipoAlerta.DOCUMENTO_DESCARGADO, minutos_atras=indice / 120)
    assert _patrones(repo) == []


def test_diez_descargas_disparan(repo, correlacion) -> None:
    for indice in range(9):
        _emitir(
            repo,
            correlacion,
            TipoAlerta.DOCUMENTO_DESCARGADO,
            minutos_atras=indice / 120,  # todas dentro del minuto
        )
    generadas = _emitir(
        repo, correlacion, TipoAlerta.DOCUMENTO_DESCARGADO, minutos_atras=0.0
    )
    assert len(generadas) == 1
    assert generadas[0].regla == "descargas_masivas"
    assert generadas[0].severidad == SeveridadAlerta.ADVERTENCIA
    assert "10" in generadas[0].mensaje


# --- regla: ip_nunca_vista -------------------------------------------------


def test_primer_login_nunca_dispara(repo, correlacion) -> None:
    """Sin línea base (ningún login previo) no hay referencia de IP."""

    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    assert generadas == []
    assert _patrones(repo) == []


def test_login_con_ip_repetida_no_dispara(repo, correlacion) -> None:
    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    assert generadas == []
    assert _patrones(repo) == []


def test_login_con_ip_nueva_dispara(repo, correlacion) -> None:
    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="203.0.113.7")

    assert len(generadas) == 1
    patron = generadas[0]
    assert patron.regla == "ip_nunca_vista"
    assert patron.severidad == SeveridadAlerta.ADVERTENCIA
    assert patron.ip == "203.0.113.7"
    assert "203.0.113.7" in patron.mensaje


def test_ip_nueva_tiene_enfriamiento(repo, correlacion) -> None:
    """Una detección previa enfría la regla para el mismo usuario."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="203.0.113.7")
    assert len(_patrones(repo)) == 1

    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="198.51.100.9")
    assert generadas == []
    assert len(_patrones(repo)) == 1


def test_login_sin_ip_no_evalua_la_regla(repo, correlacion) -> None:
    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    generadas = _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="")
    assert generadas == []


# --- propiedades transversales ---------------------------------------------


def test_alertas_de_correlacion_no_se_retroalimentan(repo, correlacion) -> None:
    """Evaluar una alerta PATRON_SOSPECHOSO no genera nuevas alertas."""

    alerta_patron = Alerta(
        tipo=TipoAlerta.PATRON_SOSPECHOSO,
        severidad=SeveridadAlerta.CRITICA,
        usuario="juan",
        regla="denegados_rapidos",
    )
    assert correlacion.evaluar(alerta_patron) == []


def test_alertas_sin_usuario_no_se_correlacionan(repo, correlacion) -> None:
    """Un nombre de usuario desconocido/no informado no forma ráfaga."""

    for _ in range(5):
        _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO, usuario="")
    assert _patrones(repo) == []


def test_servicio_sin_alerta_service_no_altera_las_existentes(repo, correlacion) -> None:
    """La correlación solo agrega: el histórico previo queda intacto."""

    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    _emitir(repo, correlacion, TipoAlerta.LOGIN_EXITOSO, ip="10.0.0.1")
    tipos_antes = [a.tipo for a in repo.list_all()]
    ids_antes = [a.id for a in repo.list_all()]

    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)
    _emitir(repo, correlacion, TipoAlerta.LOGIN_FALLIDO)

    alertas_despues = repo.list_all()
    # Las alertas originales siguen ahí, con los mismos id y orden.
    assert [a.tipo for a in alertas_despues][:2] == tipos_antes
    assert [a.id for a in alertas_despues][:2] == ids_antes
    assert [a.tipo for a in alertas_despues][2:] == [
        TipoAlerta.LOGIN_FALLIDO,
        TipoAlerta.LOGIN_FALLIDO,
        TipoAlerta.LOGIN_FALLIDO,
        TipoAlerta.PATRON_SOSPECHOSO,
    ]


def test_alertas_antiguas_sin_regla_siguen_cargando(tmp_path) -> None:
    """JSON previo a la mejora (sin campo ``regla``) se carga sin errores."""

    ruta = tmp_path / "alertas.json"
    ruta.write_text(
        json.dumps(
            [
                {
                    "id": "abc123",
                    "creado_en": "2026-01-01T10:00:00+00:00",
                    "actualizado_en": "2026-01-01T10:00:00+00:00",
                    "tipo": "login_exitoso",
                    "severidad": "info",
                    "mensaje": "Inicio de sesión exitoso.",
                    "usuario": "admin",
                    "usuario_id": "u1",
                    "ip": "127.0.0.1",
                    "leida": False,
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    alertas = AlertaRepository(ruta).list_all()
    assert len(alertas) == 1
    assert alertas[0].regla == ""
    assert alertas[0].tipo == TipoAlerta.LOGIN_EXITOSO


def test_reglas_expuestas_describen_los_umbrales(correlacion) -> None:
    reglas = correlacion.reglas()
    assert {regla.id for regla in reglas} == {
        "denegados_rapidos",
        "descargas_masivas",
        "ip_nunca_vista",
    }
    denegados = next(regla for regla in reglas if regla.id == "denegados_rapidos")
    assert denegados.umbral == settings.corr_denegados_umbral
    assert denegados.ventana_segundos == settings.corr_denegados_minutos * 60
    assert TipoAlerta.LOGIN_FALLIDO in denegados.tipos_vigilados


def test_alerta_service_con_correlacion_integrada(repo) -> None:
    """Integración del enganche: registrar muchas veces no genera bucles."""

    servicio = AlertaService(repo, correlacion=CorrelacionAlertasService(repo))
    for _ in range(10):
        servicio.registrar(TipoAlerta.LOGIN_FALLIDO, usuario="maria", ip="10.0.0.2")

    patrones = _patrones(repo)
    assert len(patrones) == 1
    assert patrones[0].regla == "denegados_rapidos"
    # Las 10 alertas originales siguen intactas.
    assert len(repo.list_all()) == 11


def test_alerta_service_sin_correlacion_sigue_funcionando(repo) -> None:
    """Sin el servicio opcional, el registro de alertas no cambia."""

    servicio = AlertaService(repo)
    alerta = servicio.registrar(TipoAlerta.LOGIN_FALLIDO, usuario="ana")
    assert alerta.tipo == TipoAlerta.LOGIN_FALLIDO
    assert alerta.regla == ""
    assert len(repo.list_all()) == 1


# --- integración de extremo a extremo con la API ---------------------------


def test_api_tres_logins_fallidos_generan_patron(client: TestClient, admin_headers: dict) -> None:
    """Flujo real:3 fallos de login (el 3º bloquea la cuenta) → correlación."""

    username = "corr.fallo.demo"
    crear_usuario(
        client,
        admin_headers,
        username=username,
        password="Correccion123!",
        rol="abogado",
        nombre_completo="Usuario de Correlación",
    )

    def _fallos() -> list[dict]:
        r = client.get(
            "/api/alertas",
            params={"tipo": "patron_sospechoso", "usuario": username, "por_pagina": 50},
            headers=admin_headers,
        )
        assert r.status_code == 200, r.text
        return r.json()["items"]

    for _ in range(2):
        r = client.post(
            "/api/auth/login", json={"username": username, "password": "incorrecta"}
        )
        assert r.status_code == 401
    # Con LEGALVAULT_MAX_INTENTOS=3 el tercer fallo bloquea la cuenta (423)
    # y su alerta ``cuenta_bloqueada`` completa la ráfaga de denegaciones.
    r = client.post("/api/auth/login", json={"username": username, "password": "incorrecta"})
    assert r.status_code == 423

    patrones = _fallos()
    assert len(patrones) >= 1
    assert patrones[0]["regla"] == "denegados_rapidos"
    assert patrones[0]["severidad"] == "critica"
    assert patrones[0]["tipo"] == "patron_sospechoso"

    # El resumen del panel cuenta el nuevo tipo sin romper el resto.
    resumen = client.get("/api/alertas/resumen", headers=admin_headers).json()
    assert resumen["por_tipo"].get("patron_sospechoso", 0) >= 1


def test_api_dos_logins_fallidos_no_generan_patron(client: TestClient, admin_headers: dict) -> None:
    username = "corr.parcial.demo"
    crear_usuario(
        client,
        admin_headers,
        username=username,
        password="Correccion123!",
        rol="abogado",
    )
    for _ in range(2):
        client.post("/api/auth/login", json={"username": username, "password": "incorrecta"})

    r = client.get(
        "/api/alertas",
        params={"tipo": "patron_sospechoso", "usuario": username},
        headers=admin_headers,
    )
    assert r.status_code == 200
    assert r.json()["total"] == 0


def test_api_reglas_de_correlacion_solo_admin(client: TestClient, admin_headers: dict) -> None:
    r = client.get("/api/alertas/reglas", headers=admin_headers)
    assert r.status_code == 200, r.text
    reglas = r.json()
    assert {regla["id"] for regla in reglas} == {
        "denegados_rapidos",
        "descargas_masivas",
        "ip_nunca_vista",
    }
    for regla in reglas:
        assert regla["descripcion"]
        assert regla["tipos_vigilados"]

    # Un asistente no puede consultar el panel de alertas ni sus reglas.
    token = _login(client, "asistente.demo", "Asistente123!")
    assert client.get("/api/alertas/reglas", headers=_h(token)).status_code == 403
    # Sin autenticación: rechazado.
    assert client.get("/api/alertas/reglas").status_code in (401, 403)


def test_api_respuestas_incluyen_el_campo_regla(client: TestClient, admin_headers: dict) -> None:
    r = client.get("/api/alertas", params={"por_pagina": 5}, headers=admin_headers)
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert "regla" in item
