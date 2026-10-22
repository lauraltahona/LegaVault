"""Pruebas de los adjuntos de la bóveda cifrada de doble fondo (Fase 6).

Este archivo cubre los 19 casos del §8 del spec ``FASE6_SPEC_ADJUNTOS_BOVEDA.md``
y, con ellos, las dos garantías centrales del módulo:

1. **Negación plausible estricta**: dos fondos con contenidos distintos
   ocupan **exactamente los mismos bytes en disco**.
2. **Integridad**: el contenido que se descarga es byte a byte el que se
   subió, y cualquier alteración del blob se detecta (409 + alerta crítica).
"""

from __future__ import annotations

import json
import shutil

import pytest

from app.core import boveda_adjuntos
from app.core.boveda_crypto import cifrar, descifrar
from app.core.config import settings
from app.core.container import alerta_repository, auditoria_repository, boveda_repository
from app.core.constants import AccionAuditoria, TipoAlerta

PW_VISIBLE = "VistaPublica123!"
PW_CONFIDENCIAL = "VistaReservada123!"
TEXTO_VISIBLE = "Contenido principal: agenda y contactos."
TEXTO_CONFIDENCIAL = "Contenido reservado: estrategia interna confidencial."

# PDF mínimo pero **real** (firma %PDF-): lo que se sube y lo que se descarga
# debe ser idéntico byte a byte.
PDF_MINIMO = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n"
    b"%%EOF\n"
)

# Texto plano con un marcador reconocible: sirve para buscar filtraciones.
SECRETO = "MARCADOR-SECRETO-LOCAL-V-QUE-NO-DEBE-APARECER-EN-DISCO-1234567890"


# --- utilidades -----------------------------------------------------------
def _boveda(client, abogado, expediente, **overrides) -> dict:
    payload = {
        "nombre": "Bóveda con adjuntos",
        "descripcion": "Bóveda ficticia para pruebas de adjuntos.",
        "expediente_id": expediente["id"],
        "password_visible": PW_VISIBLE,
        "password_confidencial": PW_CONFIDENCIAL,
        "contenido_visible": TEXTO_VISIBLE,
        "contenido_confidencial": TEXTO_CONFIDENCIAL,
    }
    payload.update(overrides)
    respuesta = client.post("/api/bovedas", headers=abogado["headers"], json=payload)
    assert respuesta.status_code == 201, respuesta.text
    return respuesta.json()


def _subir(client, headers, boveda_id, password, contenido, nombre="contrato.pdf", titulo=""):
    return client.post(
        f"/api/bovedas/{boveda_id}/adjuntos",
        headers=headers,
        files={"archivo": (nombre, contenido, "application/octet-stream")},
        data={"password": password, "titulo": titulo},
    )


def _descargar(client, headers, boveda_id, adjunto_id, password):
    return client.post(
        f"/api/bovedas/{boveda_id}/adjuntos/{adjunto_id}/descargar",
        headers=headers,
        json={"password": password},
    )


def _verificar(client, headers, boveda_id, adjunto_id, password):
    return client.post(
        f"/api/bovedas/{boveda_id}/adjuntos/{adjunto_id}/verificar-integridad",
        headers=headers,
        json={"password": password},
    )


def _eliminar(client, headers, boveda_id, adjunto_id, password):
    return client.request(
        "DELETE",
        f"/api/bovedas/{boveda_id}/adjuntos/{adjunto_id}",
        headers=headers,
        json={"password": password},
    )


def _ruta_blob(boveda_id: str):
    return boveda_adjuntos.ruta_blob(settings.bovedas_dir, boveda_id)


def _degradar_a_v1(boveda_id: str) -> None:
    """Convierte una bóveda v2 en una bóveda **heredada (v1)**.

    Reproduce exactamente lo que hay en disco con las bóvedas creadas antes de
    la Fase 6: dos vistas cifradas sin bloque ``adjuntos`` y sin blob.
    """

    repo = boveda_repository()
    boveda = repo.get(boveda_id)
    assert boveda is not None
    for indice, password in enumerate((PW_VISIBLE, PW_CONFIDENCIAL)):
        # Se busca la vista que abre esta contraseña.
        for posicion, vista in enumerate(boveda.vistas):
            contenido = descifrar(vista, password)
            if contenido is None:
                continue
            contenido.pop("adjuntos", None)
            contenido.pop("version", None)
            boveda.vistas[posicion] = cifrar(contenido, password, bucket_mb=0)
            break
    boveda.bucket_mb = 0
    boveda.formato = 1
    boveda.adjuntos_mb = 0
    repo.update(boveda)
    directorio = settings.bovedas_dir / boveda_id
    if directorio.exists():
        shutil.rmtree(directorio, ignore_errors=True)


@pytest.fixture
def boveda_v2(client, abogado, expediente) -> dict:
    return _boveda(client, abogado, expediente)


@pytest.fixture
def boveda_v1(client, abogado, expediente) -> dict:
    datos = _boveda(client, abogado, expediente)
    _degradar_a_v1(datos["id"])
    return datos


# --- caso 1: subir y descargar devuelve los mismos bytes -----------------
def test_caso_01_subir_un_pdf_y_descargarlo_devuelve_los_mismos_bytes(
    client, abogado, boveda_v2
):
    respuesta = _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO)
    assert respuesta.status_code == 201, respuesta.text
    adjunto = respuesta.json()
    assert adjunto["nombre"] == "contrato.pdf"
    assert adjunto["mime"] == "application/pdf"
    assert adjunto["tamano_bytes"] == len(PDF_MINIMO)
    assert len(adjunto["sha256"]) == 64

    descarga = _descargar(client, abogado["headers"], boveda_v2["id"], adjunto["id"], PW_VISIBLE)
    assert descarga.status_code == 200
    assert descarga.content == PDF_MINIMO


# --- caso 2: el nombre no aparece en claro en bovedas.json ----------------
def test_caso_02_el_nombre_del_archivo_no_aparece_en_bovedas_json(
    client, abogado, boveda_v2
):
    _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO, "secreto.pdf")
    contenido = boveda_repository().path.read_text(encoding="utf-8")
    assert "secreto.pdf" not in contenido
    assert "contrato" not in contenido


# --- caso 3: el contenido no aparece en claro en adjuntos.bin -------------
def test_caso_03_el_contenido_del_archivo_no_aparece_en_el_blob(
    client, abogado, boveda_v2
):
    _subir(
        client,
        abogado["headers"],
        boveda_v2["id"],
        PW_VISIBLE,
        f"{SECRETO}\n".encode("utf-8"),
        "notas.txt",
    )
    blob = _ruta_blob(boveda_v2["id"]).read_bytes()
    assert SECRETO.encode("utf-8") not in blob
    assert b"notas.txt" not in blob


# --- caso 4: el blob mide siempre 2 x segmento_bytes ----------------------
def test_caso_04_el_blob_mide_siempre_dos_segmentos(client, abogado, boveda_v2):
    ruta = _ruta_blob(boveda_v2["id"])
    segmento = boveda_adjuntos.bytes_segmento(5 * 1024 * 1024, settings.boveda_chunk_kb)
    assert ruta.stat().st_size == 2 * segmento

    _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO)
    assert ruta.stat().st_size == 2 * segmento

    _subir(
        client,
        abogado["headers"],
        boveda_v2["id"],
        PW_VISIBLE,
        b"%PDF-1.4\n" + b"A" * 500_000,
        "grande.pdf",
    )
    assert ruta.stat().st_size == 2 * segmento


# --- caso 5: los dos segmentos miden lo mismo ------------------------------
def test_caso_05_los_dos_segmentos_miden_lo_mismo(client, abogado, boveda_v2):
    _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO)
    segmento = boveda_adjuntos.bytes_segmento(5 * 1024 * 1024, settings.boveda_chunk_kb)
    blob = _ruta_blob(boveda_v2["id"]).read_bytes()
    assert len(blob) == 2 * segmento
    assert len(blob[:segmento]) == len(blob[segmento:])


# --- caso 6: dos fondos con contenidos distintos, mismo tamaño en disco ---
def test_caso_06_los_dos_fondos_ocupan_exactamente_el_mismo_tamano(client, abogado, expediente):
    vacia = _boveda(client, abogado, expediente, nombre="Bóveda con fondo vacío")
    llena = _boveda(client, abogado, expediente, nombre="Bóveda con fondo lleno")

    _subir(client, abogado["headers"], llena["id"], PW_VISIBLE, b"%PDF-1.4\n" + b"B" * 100_000)

    vacia_bytes = _ruta_blob(vacia["id"]).stat().st_size
    llena_bytes = _ruta_blob(llena["id"]).stat().st_size
    assert vacia_bytes == llena_bytes

    # Y el JSON con las vistas cifradas también ocupa lo mismo (cubeta).
    filas = json.loads(boveda_repository().path.read_text(encoding="utf-8"))
    por_id = {fila["id"]: fila for fila in filas}
    assert len(por_id[vacia["id"]]["vistas"][0]["datos"]) == len(
        por_id[llena["id"]]["vistas"][0]["datos"]
    )


# --- caso 7: alterar un byte del blob rompe la descarga -------------------
def test_caso_07_alterar_un_byte_del_blob_hace_fallar_la_descarga(client, abogado, boveda_v2):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()

    ruta = _ruta_blob(boveda_v2["id"])
    segmento = boveda_adjuntos.bytes_segmento(5 * 1024 * 1024, settings.boveda_chunk_kb)
    datos = bytearray(ruta.read_bytes())
    # Se altera el primer byte del primer slot de **ambos** segmentos: el
    # archivo puede estar en cualquiera de los dos fondos (el orden de las
    # vistas se aleatoriza al crear la bóveda).
    datos[0] ^= 0xFF
    datos[segmento] ^= 0xFF
    ruta.write_bytes(bytes(datos))

    descarga = _descargar(client, abogado["headers"], boveda_v2["id"], adjunto["id"], PW_VISIBLE)
    assert descarga.status_code == 409
    assert "integridad" in descarga.json()["detail"].lower()

    # Alerta crítica + auditoría.
    alertas = [a for a in alerta_repository().list_all() if a.tipo == TipoAlerta.BOVEDA_ADJUNTO_CORRUPTO]
    assert alertas, "Debe generarse una alerta crítica de corrupción."
    assert alertas[-1].severidad.value == "critica"

    registros = [
        r
        for r in auditoria_repository().list_all()
        if r.accion == AccionAuditoria.BOVEDA_ADJUNTO_CORRUPTO
    ]
    assert registros, "Debe registrarse el evento de corrupción en la auditoría."


# --- caso 8: contraseña incorrecta al descargar ---------------------------
def test_caso_08_contrasena_incorrecta_al_descargar_devuelve_401(client, abogado, boveda_v2):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()

    descarga = _descargar(
        client, abogado["headers"], boveda_v2["id"], adjunto["id"], "NoEsLaClave123"
    )
    assert descarga.status_code == 401
    assert PDF_MINIMO not in descarga.content
    assert "incorrecta" in descarga.json()["detail"].lower()


# --- caso 9: usuario ajeno a la bóveda ------------------------------------
def test_caso_09_usuario_ajeno_no_puede_adjuntar_ni_descargar(
    client, abogado, intruso, boveda_v2
):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()

    subida = _subir(client, intruso["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO)
    assert subida.status_code == 403

    descarga = _descargar(
        client, intruso["headers"], boveda_v2["id"], adjunto["id"], PW_VISIBLE
    )
    assert descarga.status_code == 403
    assert PDF_MINIMO not in descarga.content


# --- caso 10: .exe renombrado a .pdf --------------------------------------
def test_caso_10_ejecutable_renombrado_a_pdf_se_rechaza(client, abogado, boveda_v2):
    ruta = _ruta_blob(boveda_v2["id"])
    tamano_inicial = ruta.stat().st_size
    hash_inicial = ruta.read_bytes()

    respuesta = _subir(
        client,
        abogado["headers"],
        boveda_v2["id"],
        PW_VISIBLE,
        b"MZ\x90\x00\x03\x00\x00\x00" + b"\x00" * 200,
        "contrato.pdf",
    )
    assert respuesta.status_code == 422
    # Nada se escribe en disco.
    assert ruta.stat().st_size == tamano_inicial
    assert ruta.read_bytes() == hash_inicial

    alertas = [
        a for a in alerta_repository().list_all() if a.tipo == TipoAlerta.BOVEDA_ADJUNTO_RECHAZADO
    ]
    assert alertas, "Debe generarse la alerta de adjunto rechazado."


# --- caso 11: archivo mayor que la capacidad ------------------------------
def test_caso_11_archivo_mayor_que_la_capacidad_se_rechaza(client, abogado, boveda_v2):
    ruta = _ruta_blob(boveda_v2["id"])
    tamano_inicial = ruta.stat().st_size

    # Capacidad de 5 MB -> 4 MiB útiles: un archivo de 6 MiB no cabe.
    respuesta = _subir(
        client,
        abogado["headers"],
        boveda_v2["id"],
        PW_VISIBLE,
        b"%PDF-1.4\n" + b"C" * (6 * 1024 * 1024),
        "enorme.pdf",
    )
    assert respuesta.status_code == 422
    detalle = respuesta.json()["detail"].lower()
    assert "mb" in detalle
    # El blob no cambia de tamaño.
    assert ruta.stat().st_size == tamano_inicial


# --- caso 12: bóveda v1 no acepta adjuntos --------------------------------
def test_caso_12_boveda_v1_no_acepta_adjuntos(client, abogado, boveda_v1):
    respuesta = _subir(
        client, abogado["headers"], boveda_v1["id"], PW_VISIBLE, PDF_MINIMO
    )
    assert respuesta.status_code == 409
    assert "modernizar" in respuesta.json()["detail"].lower()


# --- caso 13: modernizar con las dos contraseñas --------------------------
def test_caso_13_modernizar_con_las_dos_contrasenas(client, abogado, boveda_v1):
    modernizar = client.post(
        f"/api/bovedas/{boveda_v1['id']}/modernizar",
        headers=abogado["headers"],
        json={
            "password_visible": PW_VISIBLE,
            "password_confidencial": PW_CONFIDENCIAL,
        },
    )
    assert modernizar.status_code == 200, modernizar.text
    assert modernizar.json()["formato"] == 2

    # Tras modernizar ya se puede adjuntar.
    subida = _subir(client, abogado["headers"], boveda_v1["id"], PW_VISIBLE, PDF_MINIMO)
    assert subida.status_code == 201, subida.text

    # Los dos segmentos miden lo mismo.
    segmento = boveda_adjuntos.bytes_segmento(5 * 1024 * 1024, settings.boveda_chunk_kb)
    blob = _ruta_blob(boveda_v1["id"]).read_bytes()
    assert len(blob) == 2 * segmento

    # Y el contenido de los dos fondos sigue intacto.
    for password, texto in ((PW_VISIBLE, TEXTO_VISIBLE), (PW_CONFIDENCIAL, TEXTO_CONFIDENCIAL)):
        apertura = client.post(
            f"/api/bovedas/{boveda_v1['id']}/desbloquear",
            headers=abogado["headers"],
            json={"password": password},
        )
        assert apertura.status_code == 200
        assert texto in [e["contenido"] for e in apertura.json()["entradas"]]


# --- caso 14: modernizar con la misma contraseña dos veces ----------------
def test_caso_14_modernizar_con_la_misma_contrasena_dos_veces(client, abogado, boveda_v1):
    respuesta = client.post(
        f"/api/bovedas/{boveda_v1['id']}/modernizar",
        headers=abogado["headers"],
        json={
            "password_visible": PW_VISIBLE,
            "password_confidencial": PW_VISIBLE,
        },
    )
    assert respuesta.status_code == 422


# --- caso 15: borrar un adjunto no encoge el blob ni libera el contador ---
def test_caso_15_borrar_un_adjunto_no_cambia_el_tamano_del_blob(client, abogado, boveda_v2):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()

    ruta = _ruta_blob(boveda_v2["id"])
    tamano_inicial = ruta.stat().st_size

    borrado = _eliminar(
        client, abogado["headers"], boveda_v2["id"], adjunto["id"], PW_VISIBLE
    )
    assert borrado.status_code == 204
    assert ruta.stat().st_size == tamano_inicial

    # El contador NO se libera: el siguiente archivo empieza más arriba.
    nuevo = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO, "otro.pdf"
    ).json()
    assert nuevo["chunk_inicio"] > adjunto["chunk_inicio"]


# --- caso 16: tras borrar y volver a subir, los nonces difieren -----------
def test_caso_16_los_nonces_difieren_tras_borrar_y_volver_a_subir(client, abogado, boveda_v2):
    primero = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO, "uno.pdf"
    ).json()
    _eliminar(client, abogado["headers"], boveda_v2["id"], primero["id"], PW_VISIBLE)
    segundo = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO, "dos.pdf"
    ).json()
    assert segundo["chunk_inicio"] != primero["chunk_inicio"]
    assert segundo["chunk_inicio"] >= primero["chunk_inicio"] + primero["chunks"]


# --- caso 17: cada archivo va a su fondo ----------------------------------
def test_caso_17_cada_archivo_va_a_su_fondo(client, abogado, boveda_v2):
    visible = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO, "visible.pdf"
    ).json()
    reservado = _subir(
        client,
        abogado["headers"],
        boveda_v2["id"],
        PW_CONFIDENCIAL,
        b"%PDF-1.4\n" + b"D" * 1000,
        "reservado.pdf",
    ).json()

    assert visible["id"] != reservado["id"]

    # Cada fondo solo ve lo suyo.
    apertura_visible = client.post(
        f"/api/bovedas/{boveda_v2['id']}/desbloquear",
        headers=abogado["headers"],
        json={"password": PW_VISIBLE},
    ).json()
    apertura_reservada = client.post(
        f"/api/bovedas/{boveda_v2['id']}/desbloquear",
        headers=abogado["headers"],
        json={"password": PW_CONFIDENCIAL},
    ).json()

    assert [a["id"] for a in apertura_visible["adjuntos"]] == [visible["id"]]
    assert [a["id"] for a in apertura_reservada["adjuntos"]] == [reservado["id"]]


# --- caso 18: el JSON sigue sin exponer material criptográfico ------------
def test_caso_18_el_json_sigue_sin_exponer_material_criptografico(client, abogado, boveda_v2):
    _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO)
    filas = json.loads(boveda_repository().path.read_text(encoding="utf-8"))
    for fila in filas:
        assert len(fila["vistas"]) == 2
        for vista in fila["vistas"]:
            assert set(vista) == {"salt", "nonce", "datos"}


# --- caso 19: regresión, las bóvedas v1 siguen abriéndose y editándose ----
def test_caso_19_regresion_las_bovedas_v1_siguen_abriendose(client, abogado, boveda_v1):
    apertura = client.post(
        f"/api/bovedas/{boveda_v1['id']}/desbloquear",
        headers=abogado["headers"],
        json={"password": PW_VISIBLE},
    )
    assert apertura.status_code == 200
    cuerpo = apertura.json()
    assert cuerpo["adjuntos"] == []
    assert cuerpo["version"] == 1
    assert TEXTO_VISIBLE in [e["contenido"] for e in cuerpo["entradas"]]

    # Y se siguen editando igual que antes.
    entrada = client.post(
        f"/api/bovedas/{boveda_v1['id']}/entradas",
        headers=abogado["headers"],
        json={"titulo": "Nota", "contenido": "Más texto.", "password": PW_VISIBLE},
    )
    assert entrada.status_code == 201


# --- extras: contrato de la respuesta --------------------------------------
def test_desbloquear_de_una_v2_devuelve_la_version_y_los_metadatos(client, abogado, boveda_v2):
    _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO, "contrato.pdf")
    apertura = client.post(
        f"/api/bovedas/{boveda_v2['id']}/desbloquear",
        headers=abogado["headers"],
        json={"password": PW_VISIBLE},
    ).json()
    assert apertura["version"] == 2
    assert len(apertura["adjuntos"]) == 1
    adjunto = apertura["adjuntos"][0]
    assert adjunto["nombre"] == "contrato.pdf"
    assert adjunto["mime"] == "application/pdf"
    assert set(adjunto) == {
        "id",
        "nombre",
        "mime",
        "tamano_bytes",
        "sha256",
        "chunk_inicio",
        "chunks",
        "titulo",
    }
    # Nunca se expone la clave de los chunks.
    assert "clave" not in adjunto and "iv_base" not in adjunto


def test_la_respuesta_de_subida_no_expone_material_cifrado(client, abogado, boveda_v2):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()
    assert not {"clave", "iv_base", "contador", "slots", "chunk_bytes"} & set(adjunto)


def test_verificar_integridad_confirma_un_adjunto_sano(client, abogado, boveda_v2):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()
    respuesta = _verificar(
        client, abogado["headers"], boveda_v2["id"], adjunto["id"], PW_VISIBLE
    )
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["integro"] is True
    assert cuerpo["checksum_esperado"] == cuerpo["checksum_calculado"] == adjunto["sha256"]
    assert cuerpo["tamano_esperado"] == cuerpo["tamano_calculado"] == len(PDF_MINIMO)


def test_verificar_integridad_detecta_el_blob_alterado(client, abogado, boveda_v2):
    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()
    ruta = _ruta_blob(boveda_v2["id"])
    segmento = boveda_adjuntos.bytes_segmento(5 * 1024 * 1024, settings.boveda_chunk_kb)
    datos = bytearray(ruta.read_bytes())
    datos[10] ^= 0x01
    datos[segmento + 10] ^= 0x01
    ruta.write_bytes(bytes(datos))

    respuesta = _verificar(
        client, abogado["headers"], boveda_v2["id"], adjunto["id"], PW_VISIBLE
    )
    assert respuesta.status_code == 200
    assert respuesta.json()["integro"] is False


def test_descargar_un_adjunto_inexistente_devuelve_404(client, abogado, boveda_v2):
    respuesta = _descargar(
        client, abogado["headers"], boveda_v2["id"], "no-existe", PW_VISIBLE
    )
    assert respuesta.status_code == 404


def test_la_descarga_no_va_en_la_query_string(client, abogado, boveda_v2):
    """La contraseña viaja en el cuerpo, nunca en la URL (decisión D7)."""

    adjunto = _subir(
        client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO
    ).json()
    respuesta = client.post(
        f"/api/bovedas/{boveda_v2['id']}/adjuntos/{adjunto['id']}/descargar?password={PW_VISIBLE}",
        headers=abogado["headers"],
        json={},
    )
    # Sin contraseña en el cuerpo: la petición no debe servir el archivo.
    assert respuesta.status_code == 422


def test_el_archivo_no_filtral_nada_en_alertas_ni_auditoria(client, abogado, boveda_v2):
    _subir(
        client,
        abogado["headers"],
        boveda_v2["id"],
        PW_VISIBLE,
        f"{SECRETO}\n".encode("utf-8"),
        "notas.txt",
    )
    alertas = alerta_repository().list_all()
    auditoria = auditoria_repository().list_all()
    for registro in alertas:
        assert SECRETO not in registro.mensaje
        assert PW_VISIBLE not in registro.mensaje
    for registro in auditoria:
        assert SECRETO not in registro.detalle
        assert PW_VISIBLE not in registro.detalle


def test_la_capacidad_de_adjuntos_se_puede_elegir_al_crear(client, abogado, expediente):
    boveda = _boveda(client, abogado, expediente, nombre="Bóveda de 1 MB", adjuntos_mb=1)
    segmento = boveda_adjuntos.bytes_segmento(1 * 1024 * 1024, settings.boveda_chunk_kb)
    assert _ruta_blob(boveda["id"]).stat().st_size == 2 * segmento


def test_una_capacidad_fuera_de_la_escalera_se_rechaza(client, abogado, expediente):
    respuesta = client.post(
        "/api/bovedas",
        headers=abogado["headers"],
        json={
            "nombre": "Bóveda con capacidad inválida",
            "expediente_id": expediente["id"],
            "password_visible": PW_VISIBLE,
            "password_confidencial": PW_CONFIDENCIAL,
            "adjuntos_mb": 7,
        },
    )
    assert respuesta.status_code == 422


def test_eliminarla_boveda_borra_el_blob(client, abogado, boveda_v2):
    _subir(client, abogado["headers"], boveda_v2["id"], PW_VISIBLE, PDF_MINIMO)
    ruta = _ruta_blob(boveda_v2["id"])
    assert ruta.exists()
    borrado = client.delete(f"/api/bovedas/{boveda_v2['id']}", headers=abogado["headers"])
    assert borrado.status_code == 204
    assert not ruta.exists()
