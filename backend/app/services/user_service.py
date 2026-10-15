"""Servicio de usuarios (Módulo 1).

Reglas destacadas:
- Las contraseñas solo se persisten como hash scrypt.
- No se permite desactivar/degradar al último administrador activo.
- Un usuario no puede desactivarse a sí mismo.
"""

from __future__ import annotations

from app.core.constants import AccionAuditoria, Rol, SeveridadAlerta, TipoAlerta
from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError, ValidationError
from app.core.security import hash_password
from app.core.validators import (
    validar_email,
    validar_password,
    validar_texto_obligatorio,
    validar_username,
)
from app.models.user import User
from app.repositories.user_repository import UserRepository
from app.services.alerta_service import AlertaService
from app.services.auditoria_service import AuditoriaService

_ROLES_VALIDOS = {rol.value for rol in Rol}


class UserService:
    def __init__(
        self,
        repository: UserRepository,
        alertas: AlertaService,
        auditoria: AuditoriaService,
    ) -> None:
        self._repo = repository
        self._alertas = alertas
        self._auditoria = auditoria

    def listar(self, *, q: str | None = None, rol: Rol | None = None, activo: bool | None = None) -> list[User]:
        objetivo = (q or "").strip().lower()

        def coincide(user: User) -> bool:
            if rol is not None and user.rol != rol:
                return False
            if activo is not None and user.activo != activo:
                return False
            if objetivo:
                campos = f"{user.username} {user.nombre_completo} {user.email}".lower()
                if objetivo not in campos:
                    return False
            return True

        return sorted(self._repo.find(coincide), key=lambda user: user.username.lower())

    def obtener(self, user_id: str) -> User:
        user = self._repo.get(user_id)
        if user is None:
            raise NotFoundError("El usuario no existe.")
        return user

    def crear(self, datos: dict, actor: User) -> User:
        username = validar_username(datos.get("username", ""))
        email = validar_email(datos.get("email", ""))
        nombre = validar_texto_obligatorio(datos.get("nombre_completo", ""), "nombre_completo", 120)
        password = validar_password(datos.get("password", ""))
        rol = self._normalizar_rol(datos.get("rol"))

        if self._repo.username_exists(username):
            raise ConflictError("Ya existe un usuario con ese nombre de usuario.")
        if self._repo.email_exists(email):
            raise ConflictError("Ya existe un usuario con ese correo electrónico.")

        user = User(
            username=username,
            nombre_completo=nombre,
            email=email,
            password_hash=hash_password(password),
            rol=rol,
            activo=True,
        )
        self._repo.add(user)
        self._alertas.registrar(
            TipoAlerta.USUARIO_CREADO,
            mensaje=f"Usuario '{user.username}' creado con rol {user.rol.value}.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.USUARIO_CREADO,
            actor=actor,
            entidad="usuario",
            entidad_id=user.id,
            detalle=f"Usuario '{user.username}' creado con rol {user.rol.value}.",
        )
        return user

    def actualizar(self, user_id: str, datos: dict, actor: User) -> User:
        user = self.obtener(user_id)

        if "nombre_completo" in datos and datos["nombre_completo"] is not None:
            user.nombre_completo = validar_texto_obligatorio(
                datos["nombre_completo"], "nombre_completo", 120
            )
        if "email" in datos and datos["email"] is not None:
            email = validar_email(datos["email"])
            if self._repo.email_exists(email, exclude_id=user.id):
                raise ConflictError("Ya existe otro usuario con ese correo electrónico.")
            user.email = email
        if "rol" in datos and datos["rol"] is not None:
            nuevo_rol = self._normalizar_rol(datos["rol"])
            if user.rol == Rol.ADMIN and nuevo_rol != Rol.ADMIN:
                self._asegurar_no_ultimo_admin(user)
            user.rol = nuevo_rol

        user.tocar()
        self._repo.update(user)
        self._alertas.registrar(
            TipoAlerta.USUARIO_EDITADO,
            mensaje=f"Datos del usuario '{user.username}' actualizados.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.USUARIO_EDITADO,
            actor=actor,
            entidad="usuario",
            entidad_id=user.id,
            detalle=f"Datos del usuario '{user.username}' actualizados.",
        )
        return user

    def cambiar_estado(self, user_id: str, activo: bool, actor: User) -> User:
        user = self.obtener(user_id)
        if user.id == actor.id and not activo:
            raise PermissionDeniedError("No puede desactivar su propia cuenta.")
        if not activo:
            self._asegurar_no_ultimo_admin(user)
        user.activo = activo
        if activo:
            # Al reactivar, se limpian los contadores de bloqueo.
            user.intentos_fallidos = 0
            user.bloqueado_hasta = None
        else:
            # Desactivar la cuenta revoca cualquier bloqueo pendiente.
            user.bloqueado_hasta = None
        user.tocar()
        self._repo.update(user)

        if activo:
            self._alertas.registrar(
                TipoAlerta.CUENTA_DESBLOQUEADA,
                mensaje=f"Usuario '{user.username}' reactivado.",
                usuario=actor.username,
                usuario_id=actor.id,
            )
        else:
            self._alertas.registrar(
                TipoAlerta.USUARIO_DESACTIVADO,
                mensaje=f"Usuario '{user.username}' desactivado.",
                usuario=actor.username,
                usuario_id=actor.id,
            )
        self._auditoria.registrar(
            AccionAuditoria.USUARIO_ESTADO,
            actor=actor,
            entidad="usuario",
            entidad_id=user.id,
            detalle=(
                f"Usuario '{user.username}' "
                f"{'reactivado' if activo else 'desactivado'}."
            ),
        )
        return user

    def restablecer_password(self, user_id: str, nueva_password: str, actor: User) -> None:
        user = self.obtener(user_id)
        user.password_hash = hash_password(validar_password(nueva_password))
        user.intentos_fallidos = 0
        user.bloqueado_hasta = None
        user.tocar()
        self._repo.update(user)
        # Nunca se registra la contraseña ni su hash en la alerta.
        self._alertas.registrar(
            TipoAlerta.USUARIO_EDITADO,
            mensaje=f"Contraseña restablecida para '{user.username}'.",
            usuario=actor.username,
            usuario_id=actor.id,
            severidad=SeveridadAlerta.ADVERTENCIA,
        )
        self._auditoria.registrar(
            AccionAuditoria.USUARIO_PASSWORD,
            actor=actor,
            entidad="usuario",
            entidad_id=user.id,
            detalle=f"Contraseña restablecida para '{user.username}'.",
        )

    def desbloquear(self, user_id: str, actor: User) -> User:
        """Levanta manualmente un bloqueo temporal (Módulo 7)."""

        user = self.obtener(user_id)
        if user.bloqueado_hasta is None:
            raise ValidationError("El usuario no está bloqueado.")
        user.bloqueado_hasta = None
        user.intentos_fallidos = 0
        user.tocar()
        self._repo.update(user)
        self._alertas.registrar(
            TipoAlerta.CUENTA_DESBLOQUEADA,
            mensaje=f"Bloqueo levantado manualmente para '{user.username}'.",
            usuario=actor.username,
            usuario_id=actor.id,
        )
        self._auditoria.registrar(
            AccionAuditoria.USUARIO_DESBLOQUEADO,
            actor=actor,
            entidad="usuario",
            entidad_id=user.id,
            detalle=f"Bloqueo levantado manualmente para '{user.username}'.",
        )
        return user

    # --- utilidades internas -------------------------------------------
    def _normalizar_rol(self, valor: object) -> Rol:
        if isinstance(valor, Rol):
            return valor
        texto = str(valor or "").strip().lower()
        if texto not in _ROLES_VALIDOS:
            raise ValidationError("El rol indicado no es válido.")
        return Rol(texto)

    def _asegurar_no_ultimo_admin(self, user: User) -> None:
        """Impide quedarse sin administradores activos."""

        if user.rol != Rol.ADMIN or not user.activo:
            return
        if self._repo.count_admins_activos() <= 1:
            raise ConflictError("Debe existir al menos un administrador activo en el sistema.")
