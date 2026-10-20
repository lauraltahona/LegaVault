"""Pruebas de la validación de tipo por *magic bytes* (Módulo 3, mejora #4).

Cubre la mejora "Validación de tipo por magic bytes al subir": lista blanca de
extensiones (txt/png/jpg/pdf/zip/csv, para no romper la demo del ``seed``),
detección real del contenido por firma, rechazo de archivos que mienten con su
extensión, alerta ``documento_rechazado`` + auditoría con resultado
``denegado`` ante cada rechazo, y ausencia de regresiones en el flujo normal
de carga/descarga.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.exceptions import ValidationError
from app.core.magic_bytes import (
    EXTENSIONES_POR_DEFECTO,
    detectar_formato,
    es_texto_plano,
    validar_tipo_archivo,
)

# --- muestras de contenido -------------------------------------------------

PDF = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\nstartxref\n0\n%%EOF\n"
PNG = b"\x89PNG\r\n\x1a\n" + b"\x00\x00\x00\rIHDR" + b"\x00" * 24
JPG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00"
ZIP = b"PK\x03\x04\x14\x00\x00\x00\x08\x00" + b"\x00" * 16
EXE = b"MZ\x90\x00\x03\x00\x00\x00\x04\x00" + b"\x00" * 16
ELF = b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 16
TEXTO = "Contrato de demostracion (contenido ficticio).\n".encode("utf-8")
CSV = "fecha,concepto,importe\n2026-01-01, Honorarios, 1200.00\n".encode("utf-8")

_ADMITIDAS = settings.extensiones_archivo_permitidas


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _login(client: TestClient, username: str, password: str) -> str:
    r = client.post("/api/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return r.json()["access_token"]


def _subir(
    client: TestClient,
    token: str,
    expediente_id: str,
    nombre: str,
    contenido: bytes,
    mime: str = "application/octet-stream",
):
    return client.post(
        "/api/documentos",
        headers=_h(token),
        data={
            "expediente_id": expediente_id,
            "tipo": "contrato",
            "nivel_sensibilidad": "interno",
            "descripcion": "Prueba de magic bytes",
        },
        files={"archivo": (nombre, contenido, mime)},
    )


# --- unitarias: detección ---------------------------------------------------


def test_detectar_formato_por_firma() -> None:
    assert detectar_formato(PDF) == "pdf"
    assert detectar_formato(PNG) == "png"
    assert detectar_formato(JPG) == "jpg"
    assert detectar_formato(ZIP) == "zip"
    assert detectar_formato(TEXTO) == "texto"
    assert detectar_formato(CSV) == "texto"


def test_detectar_formato_zip_vacio() -> None:
    """El archive vacío legítimo (PK\\x05\\x06) también se reconoce como ZIP."""

    assert detectar_formato(b"PK\x05\x06" + b"\x00" * 18) == "zip"


def test_detectar_formato_rechaza_binarios_desconocidos() -> None:
    assert detectar_formato(EXE) is None
    assert detectar_formato(ELF) is None
    assert detectar_formato(b"\x00\x01\x02\x03" * 64) is None


def test_es_texto_plano_admite_utf8_y_bom() -> None:
    assert es_texto_plano(TEXTO)
    assert es_texto_plano("señorías, búfalo\n".encode("utf-8"))
    assert es_texto_plano(b"\xef\xbb\xbf" + CSV)  # BOM de Excel
    assert es_texto_plano(b"columna1\tcolumna2\r\n1\t2\r\n")  # tab y CRLF


def test_es_texto_plano_rechaza_utf16_y_latin1() -> None:
    """Solo UTF-8: UTF-16 lleva NULs y Latin-1 no es UTF-8 válido."""

    assert not es_texto_plano("hola".encode("utf-16-le"))
    assert not es_texto_plano("señor".encode("latin-1"))
    assert not es_texto_plano(b"")
    assert not es_texto_plano(b"\x00" * 8)


def test_es_texto_plano_tolera_caracter_multibyte_cortado() -> None:
    """Una 'ñ' (2 bytes) partida por el límite de muestra no invalida el texto."""

    muestra = ("a" * 100 + "ñ").encode("utf-8")  # último byte de la ñ fuera de la muestra
    assert es_texto_plano(muestra[:-1])


# --- unitarias: validación --------------------------------------------------


def test_validar_tipo_archivo_admite_la_lista_blanca() -> None:
    assert validar_tipo_archivo("contrato_demo.txt", TEXTO) == "texto"
    assert validar_tipo_archivo("registros.csv", CSV) == "texto"
    assert validar_tipo_archivo("plano.pdf", PDF, extensiones_permitidas=_ADMITIDAS) == "pdf"
    assert validar_tipo_archivo("foto.png", PNG) == "png"
    assert validar_tipo_archivo("foto.jpg", JPG) == "jpg"
    assert validar_tipo_archivo("foto.jpeg", JPG) == "jpg"  # .jpeg es alias de jpg
    assert validar_tipo_archivo("adjunto.zip", ZIP) == "zip"


def test_validar_tipo_archivo_no_distingue_mayusculas() -> None:
    assert validar_tipo_archivo("CONTRATO.PDF", PDF) == "pdf"
    assert validar_tipo_archivo("Notas.TXT", TEXTO) == "texto"


def test_extensiones_por_defecto_cubren_los_tipos_de_la_demo() -> None:
    """La lista blanca por defecto incluye lo que suben el seed y el smoke test."""

    assert {".txt", ".csv", ".png", ".jpg", ".jpeg", ".pdf", ".zip"} <= set(
        EXTENSIONES_POR_DEFECTO
    )


def test_rechaza_extension_fuera_de_la_lista_blanca() -> None:
    for nombre in ("malware.exe", "script.js", "pagina.html", "hoja.xlsx"):
        try:
            validar_tipo_archivo(nombre, TEXTO)
        except ValidationError as exc:
            assert "no permitido" in exc.message
            assert ".txt" in exc.message and ".zip" in exc.message  # lista las admitidas
        else:  # pragma: no cover
            raise AssertionError(f"{nombre} debió ser rechazado")


def test_rechaza_archivo_sin_extension() -> None:
    try:
        validar_tipo_archivo("sin_extension", TEXTO)
    except ValidationError as exc:
        assert "extensión" in exc.message.lower()
    else:  # pragma: no cover
        raise AssertionError("Un archivo sin extensión debe ser rechazado")


def test_rechaza_contenido_que_miente_sobre_su_extension() -> None:
    with pytest.raises(ValidationError):
        validar_tipo_archivo("contrato.pdf", EXE)  # ejecutable disfrazado de PDF
    with pytest.raises(ValidationError):
        validar_tipo_archivo("contrato.pdf", PNG)  # PNG con nombre de PDF
    with pytest.raises(ValidationError):
        validar_tipo_archivo("foto.png", EXE)
    with pytest.raises(ValidationError):
        validar_tipo_archivo("notas.txt", PDF)  # texto que en realidad es un PDF
    with pytest.raises(ValidationError):
        validar_tipo_archivo("registros.csv", EXE)
    with pytest.raises(ValidationError):
        validar_tipo_archivo("adjunto.zip", TEXTO)  # ZIP que en realidad es texto


def test_mensaje_explica_los_magic_bytes_sin_filtrar_contenido() -> None:
    marcador = b"SECRETO-QUE-NO-DEBE-FILTRARSE-9f3a"
    try:
        validar_tipo_archivo("malicioso.pdf", b"MZ\x90\x00" + marcador)
    except ValidationError as exc:
        assert "magic bytes" in exc.message.lower()
        assert "ejecutable" in exc.message.lower()
        assert marcador.decode() not in exc.message  # nunca el contenido
    else:  # pragma: no cover
        raise AssertionError("Debió ser rechazado")


def test_extension_habilitada_por_entorno_sin_regla_de_contenido() -> None:
    """Una extensión añadida por env (p. ej. .docx) solo exige formato conocido."""

    assert (
        validar_tipo_archivo("escrito.docx", ZIP, extensiones_permitidas=(".txt", ".docx"))
        == "zip"
    )
    with pytest.raises(ValidationError):
        validar_tipo_archivo("escrito.docx", EXE, extensiones_permitidas=(".txt", ".docx"))


# --- API: subidas válidas ---------------------------------------------------


def test_subida_txt_sigue_funcionando(client: TestClient, abogado: dict, expediente: dict) -> None:
    """Regresión: el flujo del seed (archivos .txt de texto) no se rompe."""

    r = _subir(
        client,
        abogado["headers"]["Authorization"].split()[1],
        expediente["id"],
        "integridad_ok.txt",
        b"Contrato de demostracion (contenido ficticio).\n",
        "text/plain",
    )
    assert r.status_code == 201, r.text
    assert r.json()["nombre_original"] == "integridad_ok.txt"


def test_subida_toda_la_lista_blanca(client: TestClient, abogado: dict, expediente: dict) -> None:
    """txt, csv, png, jpg, pdf y zip se aceptan con su contenido real."""

    token = abogado["headers"]["Authorization"].split()[1]
    muestras = {
        "escritura.txt": TEXTO,
        "registros.csv": CSV,
        "plano.png": PNG,
        "captura.jpg": JPG,
        "resolucion.pdf": PDF,
        "adjuntos.zip": ZIP,
    }
    for nombre, contenido in muestras.items():
        r = _subir(client, token, expediente["id"], nombre, contenido)
        assert r.status_code == 201, f"{nombre}: {r.text}"
        # Round-trip: la descarga devuelve exactamente los bytes subidos.
        d = client.get(f"/api/documentos/{r.json()['id']}/descargar", headers=_h(token))
        assert d.status_code == 200
        assert d.content == contenido


def test_subida_pdf_en_mayusculas(client: TestClient, abogado: dict, expediente: dict) -> None:
    """La extensión se compara sin distinguir mayúsculas."""

    token = abogado["headers"]["Authorization"].split()[1]
    r = _subir(client, token, expediente["id"], "RESOLUCION.PDF", PDF, "application/pdf")
    assert r.status_code == 201, r.text


# --- API: rechazos ----------------------------------------------------------


def test_ejecutable_disfrazado_de_pdf_rechazado(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """Un .exe renombrado a .pdf da 422 y queda en alertas + auditoría."""

    token = abogado["headers"]["Authorization"].split()[1]
    r = _subir(client, token, expediente["id"], "malicioso.pdf", EXE, "application/pdf")
    assert r.status_code == 422, r.text
    detalle = r.json()["detail"]
    assert "magic bytes" in detalle.lower()
    assert "malicioso.pdf" in detalle
    assert b"MZ" not in r.content  # los bytes del archivo no se reflejan

    admin = _h(_login(client, "admin", "Admin123!"))

    r = client.get("/api/alertas", params={"tipo": "documento_rechazado"}, headers=admin)
    assert r.status_code == 200
    rechazos = [a for a in r.json() if "malicioso.pdf" in a["mensaje"]]
    assert rechazos, "Debe existir la alerta DOCUMENTO_RECHAZADO"
    assert all(a["severidad"] == "advertencia" for a in rechazos)

    r = client.get(
        "/api/auditoria",
        params={"accion": "documento_rechazado", "resultado": "denegado"},
        headers=admin,
    )
    assert r.status_code == 200
    assert any("malicioso.pdf" in registro["detalle"] for registro in r.json()), (
        "El rechazo debe quedar en la auditoría como denegado"
    )


def test_binario_en_archivo_txt_rechazado(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """Un archivo .txt que contiene bytes binarios no pasa la heurística de texto."""

    token = abogado["headers"]["Authorization"].split()[1]
    r = _subir(client, token, expediente["id"], "inocente.txt", EXE, "text/plain")
    assert r.status_code == 422, r.text
    assert "magic bytes" in r.json()["detail"].lower()


def test_extension_no_admitida_rechazada(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """Una extensión fuera de la lista blanca da 422 con el listado de admitidas."""

    token = abogado["headers"]["Authorization"].split()[1]
    r = _subir(client, token, expediente["id"], "pagina.html", b"<html></html>", "text/html")
    assert r.status_code == 422, r.text
    assert "no permitido" in r.json()["detail"]
    assert ".txt" in r.json()["detail"] and ".zip" in r.json()["detail"]


def test_archivo_sin_extension_rechazado(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    token = abogado["headers"]["Authorization"].split()[1]
    r = _subir(client, token, expediente["id"], "documento", TEXTO)
    assert r.status_code == 422, r.text
    assert "extensión" in r.json()["detail"].lower()


def test_rechazo_no_crea_documento_ni_archivo(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """El rechazo es limpio: ni registro metadatos ni bytes en uploads/."""

    token = abogado["headers"]["Authorization"].split()[1]
    antes = {
        d["nombre_original"]
        for d in client.get("/api/documentos", headers=_h(token)).json()
    }
    r = _subir(client, token, expediente["id"], "fantasma.pdf", EXE)
    assert r.status_code == 422

    despues = {
        d["nombre_original"]
        for d in client.get("/api/documentos", headers=_h(token)).json()
    }
    assert despues == antes
    assert not list(settings.uploads_dir.glob("fantasma*"))


def test_rechazo_no_filtra_contenido_en_alertas_ni_auditoria(
    client: TestClient, abogado: dict, expediente: dict
) -> None:
    """Regla innegociable: los mensajes de rechazo no llevan el contenido."""

    token = abogado["headers"]["Authorization"].split()[1]
    marcador = "SECRETO-QUE-NO-DEBE-FILTRARSE-9f3a"
    r = _subir(
        client,
        token,
        expediente["id"],
        "disfrazado.pdf",
        b"MZ\x90\x00" + marcador.encode("utf-8"),
    )
    assert r.status_code == 422

    admin = _h(_login(client, "admin", "Admin123!"))
    alertas = client.get(
        "/api/alertas", params={"tipo": "documento_rechazado"}, headers=admin
    ).json()
    auditoria = client.get(
        "/api/auditoria", params={"accion": "documento_rechazado"}, headers=admin
    ).json()

    assert marcador not in r.text
    assert all(marcador not in a["mensaje"] for a in alertas)
    assert all(marcador not in registro["detalle"] for registro in auditoria)


def test_rechazo_respeta_permisos_previos(
    client: TestClient, abogado: dict, intruso: dict, expediente: dict
) -> None:
    """Los permisos se evalúan antes que el tipo: un ajeno sigue recibiendo 403."""

    token = intruso["headers"]["Authorization"].split()[1]
    r = _subir(client, token, expediente["id"], "malicioso.pdf", EXE)
    assert r.status_code == 403
    # Sin token → 401.
    r = client.post(
        "/api/documentos",
        data={"expediente_id": expediente["id"], "tipo": "contrato"},
        files={"archivo": ("malicioso.pdf", EXE, "application/pdf")},
    )
    assert r.status_code == 401
