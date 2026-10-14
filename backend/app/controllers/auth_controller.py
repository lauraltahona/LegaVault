"""Controlador de autenticación (Módulo 1)."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Request, status

from app.controllers.dependencies import get_bearer_token, get_current_user, obtener_ip
from app.core.container import auth_service
from app.models.user import User
from app.schemas.auth_schema import LoginRequest, TokenResponse
from app.schemas.user_schema import UserResponse

router = APIRouter(prefix="/auth", tags=["Autenticación"])


@router.post("/login", response_model=TokenResponse, summary="Iniciar sesión")
def login(payload: LoginRequest, request: Request) -> TokenResponse:
    usuario, token, expira_en = auth_service().autenticar(
        payload.username, payload.password, ip=obtener_ip(request)
    )
    return TokenResponse(
        access_token=token,
        expira_en=expira_en,
        usuario=UserResponse.model_validate(usuario),
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT, summary="Cerrar sesión")
def logout(
    token: str = Depends(get_bearer_token),
    usuario: User = Depends(get_current_user),
) -> None:
    auth_service().cerrar_sesion(token, usuario)


@router.get("/me", response_model=UserResponse, summary="Usuario autenticado")
def me(usuario: User = Depends(get_current_user)) -> UserResponse:
    return UserResponse.model_validate(usuario)
