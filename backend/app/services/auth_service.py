"""Servicio de autenticación (Módulos 1 y 7).

Concentra el flujo de inicio/cierre de sesión y la protección contra
intentos repetidos: contador de fallos y bloqueo temporal de la cuenta.
"""

from __future__ import annotations

from datetime import timedelta

import jwt

from app.core.config import settings
from app.core.constants import SeveridadAlerta, TipoAlerta
from app.core.exceptions import AccountLockedError, AuthenticationError, NotFoundError
from app.core.security import create_access_token, decode_access_token, revoke_token, verify_password
from app.models.base import utcnow
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.alerta_service import AlertaService

# Mensaje genérico: no revela si el usuario existe o si la contraseña es errónea.
_CREDENCIALES_INVALIDAS = "Usuario o contraseña incorrectos."


class AuthService:
    def __init__(self, repository: UserRepository, alertas: AlertaService) -> None:
        self._repo = repository
        self._alertas = alertas

    def autenticar(self, username: str, password: str, ip: str = "") -> tuple[User, str, object]:
        """Valida credenciales y devuelve ``(usuario, token, expira_en)``."""

        user = self._repo.get_by_username(username)

        if user is None:
            # Usuario inexistente: registramos el intento sin exponer detalles.
            self._alertas.registrar(
                TipoAlerta.LOGIN_FALLIDO,
                mensaje="Intento de inicio de sesión con un usuario inexistente.",
                usuario=(username or "").strip(),
                ip=ip,
            )
            raise AuthenticationError(_CREDENCIALES_INVALIDAS)

        # Bloqueo vigente -> no se evalúa la contraseña.
        if user.bloqueado_hasta is not None and user.bloqueado_hasta > utcnow():
            raise AccountLockedError(
                "La cuenta está bloqueada temporalmente por intentos fallidos. "
                "Inténtelo más tarde o contacte al administrador."
            )

        # Si el bloqueo ya expiró, se reinicia el contador.
        if user.bloqueado_hasta is not None:
            user.bloqueado_hasta = None
            user.intentos_fallidos = 0
            user.tocar()
            self._repo.update(user)

        if not user.activo:
            self._alertas.registrar(
                TipoAlerta.LOGIN_FALLIDO,
                mensaje=f"Intento de acceso con la cuenta desactivada '{user.username}'.",
                usuario=user.username,
                usuario_id=user.id,
                ip=ip,
            )
            raise AuthenticationError(_CREDENCIALES_INVALIDAS)

        if not verify_password(password, user.password_hash):
            self._registrar_fallo(user, ip)
            raise AuthenticationError(_CREDENCIALES_INVALIDAS)

        # Éxito: se limpian contadores y se actualiza el último acceso.
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        user.ultimo_acceso = utcnow()
        user.tocar()
        self._repo.update(user)

        token, expira_en = create_access_token(user.id, user.rol.value)
        self._alertas.registrar(
            TipoAlerta.LOGIN_EXITOSO,
            usuario=user.username,
            usuario_id=user.id,
            ip=ip,
        )
        return user, token, expira_en

    def cerrar_sesion(self, token: str, actor: User | None = None) -> None:
        """Invalida el token del lado servidor (lista de revocación)."""

        try:
            payload = decode_access_token(token)
        except jwt.InvalidTokenError:
            return
        jti = payload.get("jti")
        expires_at = payload.get("exp")
        if jti:
            revoke_token(jti, float(expires_at) if expires_at else None)

    def usuario_actual(self, token: str) -> User:
        try:
            payload = decode_access_token(token)
        except jwt.InvalidTokenError as exc:
            raise AuthenticationError("Sesión inválida o expirada.") from exc

        user = self._repo.get(payload.get("sub", ""))
        if user is None:
            raise NotFoundError("El usuario de la sesión ya no existe.")
        if not user.activo:
            raise AuthenticationError("La cuenta está desactivada.")
        if user.bloqueado_hasta is not None and user.bloqueado_hasta > utcnow():
            raise AccountLockedError("La cuenta está bloqueada temporalmente.")
        return user

    # --- utilidades internas -------------------------------------------
    def _registrar_fallo(self, user: User, ip: str) -> None:
        """Incrementa el contador y bloquea si se supera el límite."""

        user.intentos_fallidos += 1
        restantes = settings.max_intentos_fallidos - user.intentos_fallidos

        if user.intentos_fallidos >= settings.max_intentos_fallidos:
            user.bloqueado_hasta = utcnow() + timedelta(minutes=settings.minutos_bloqueo)
            user.tocar()
            self._repo.update(user)
            self._alertas.registrar(
                TipoAlerta.CUENTA_BLOQUEADA,
                severidad=SeveridadAlerta.CRITICA,
                mensaje=(
                    f"Cuenta '{user.username}' bloqueada durante "
                    f"{settings.minutos_bloqueo} minutos tras "
                    f"{user.intentos_fallidos} intentos fallidos."
                ),
                usuario=user.username,
                usuario_id=user.id,
                ip=ip,
            )
            raise AccountLockedError(
                "Se superó el número de intentos permitidos. "
                f"La cuenta quedó bloqueada durante {settings.minutos_bloqueo} minutos."
            )

        user.tocar()
        self._repo.update(user)
        self._alertas.registrar(
            TipoAlerta.LOGIN_FALLIDO,
            mensaje=(
                f"Contraseña incorrecta para '{user.username}'. "
                f"Intentos restantes antes del bloqueo: {restantes}."
            ),
            usuario=user.username,
            usuario_id=user.id,
            ip=ip,
        )
