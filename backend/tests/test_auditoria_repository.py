"""Pruebas unitarias de la cadena de integridad de la auditoría (Módulo 6)."""

from __future__ import annotations

import json

from app.core.constants import AccionAuditoria, ResultadoAuditoria
from app.models.registro_auditoria import HASH_GENESIS, RegistroAuditoria
from app.repositories.auditoria_repository import AuditoriaRepository


def _repo(tmp_path) -> AuditoriaRepository:
    return AuditoriaRepository(tmp_path / "auditoria.json")


def _append(repo: AuditoriaRepository, accion: AccionAuditoria, detalle: str) -> RegistroAuditoria:
    return repo.append(
        RegistroAuditoria(accion=accion, usuario="tester", detalle=detalle)
    )


def test_cadena_vacia_es_integra(tmp_path) -> None:
    assert _repo(tmp_path).verificar_cadena() == (True, None)


def test_encadena_hash_anterior_y_actual(tmp_path) -> None:
    repo = _repo(tmp_path)
    primero = _append(repo, AccionAuditoria.LOGIN, "uno")
    segundo = _append(repo, AccionAuditoria.LOGOUT, "dos")

    assert primero.hash_anterior == HASH_GENESIS
    assert segundo.hash_anterior == primero.hash_actual
    assert primero.hash_actual != segundo.hash_actual
    assert repo.verificar_cadena() == (True, None)


def test_edicion_manual_rompe_la_cadena(tmp_path) -> None:
    repo = _repo(tmp_path)
    _append(repo, AccionAuditoria.LOGIN, "uno")
    _append(repo, AccionAuditoria.LOGOUT, "dos")
    _append(repo, AccionAuditoria.ACCESO_DENEGADO, "tres")

    filas = json.loads(repo.path.read_text(encoding="utf-8"))
    filas[1]["detalle"] = "texto manipulado a mano"
    repo.path.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")

    integro, indice = repo.verificar_cadena()
    assert integro is False
    assert indice == 1


def test_reordenar_registros_rompe_la_cadena(tmp_path) -> None:
    repo = _repo(tmp_path)
    _append(repo, AccionAuditoria.LOGIN, "uno")
    _append(repo, AccionAuditoria.LOGOUT, "dos")

    filas = json.loads(repo.path.read_text(encoding="utf-8"))
    filas.reverse()
    repo.path.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")

    integro, _ = repo.verificar_cadena()
    assert integro is False


def test_eliminar_un_registro_intermedio_rompe_la_cadena(tmp_path) -> None:
    repo = _repo(tmp_path)
    _append(repo, AccionAuditoria.LOGIN, "uno")
    _append(repo, AccionAuditoria.LOGOUT, "dos")
    _append(repo, AccionAuditoria.ACCESO_DENEGADO, "tres")

    filas = json.loads(repo.path.read_text(encoding="utf-8"))
    del filas[1]
    repo.path.write_text(json.dumps(filas, ensure_ascii=False), encoding="utf-8")

    integro, indice = repo.verificar_cadena()
    assert integro is False
    assert indice == 1


def test_el_registro_serializa_enums_por_valor(tmp_path) -> None:
    repo = _repo(tmp_path)
    registro = RegistroAuditoria(
        accion=AccionAuditoria.BOVEDA_ABIERTA,
        resultado=ResultadoAuditoria.DENEGADO,
        usuario="x",
    )
    datos = registro.to_dict()
    assert datos["accion"] == "boveda_abierta"
    assert datos["resultado"] == "denegado"
