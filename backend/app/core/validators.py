"""Validaciones de entrada reutilizables (Módulos 1, 2 y 3)."""

from __future__ import annotations

import re

from app.core.exceptions import ValidationError

_USERNAME_RE = re.compile(r"^[A-Za-z0-9._-]{3,50}$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def validar_username(username: str) -> str:
    username = (username or "").strip()
    if not _USERNAME_RE.match(username):
        raise ValidationError(
            "El usuario debe tener entre 3 y 50 caracteres (letras, números, '.', '_' o '-')."
        )
    return username


def validar_email(email: str) -> str:
    email = (email or "").strip().lower()
    if not _EMAIL_RE.match(email):
        raise ValidationError("El correo electrónico no tiene un formato válido.")
    return email


def validar_password(password: str) -> str:
    """Política mínima: 8 caracteres, al menos una letra y un dígito."""

    if not password or len(password) < 8:
        raise ValidationError("La contraseña debe tener al menos 8 caracteres.")
    if not re.search(r"[A-Za-z]", password) or not re.search(r"\d", password):
        raise ValidationError("La contraseña debe incluir al menos una letra y un número.")
    return password


def validar_texto_obligatorio(valor: str, campo: str, maximo: int = 200) -> str:
    valor = (valor or "").strip()
    if not valor:
        raise ValidationError(f"El campo '{campo}' es obligatorio.")
    if len(valor) > maximo:
        raise ValidationError(f"El campo '{campo}' no puede superar {maximo} caracteres.")
    return valor


def validar_password_boveda(password: str, campo: str = "contraseña de la bóveda") -> str:
    """Política de las contraseñas de la bóveda (Módulo 4).

    Se exige una longitud mínima pero **no** se obligan dígitos: se admiten
    frases de paso largas, que son más seguras para este uso.
    """

    if not password or len(password) < 8:
        raise ValidationError(f"La {campo} debe tener al menos 8 caracteres.")
    if len(password) > 256:
        raise ValidationError(f"La {campo} no puede superar 256 caracteres.")
    return password
