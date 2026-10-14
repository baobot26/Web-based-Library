from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.schemas import LoginRequest, RegisterRequest, TokenResponse, UserResponse
from app.config import settings
from app.infrastructure.db import get_session
from app.infrastructure.repositories.user_repository import SqlUserRepository
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["auth"])


def get_auth_service(session: Annotated[Session, Depends(get_session)]) -> AuthService:
    return AuthService(SqlUserRepository(session))


AuthServiceDep = Annotated[AuthService, Depends(get_auth_service)]


@router.post("/register", response_model=UserResponse, status_code=201)
def register(body: RegisterRequest, service: AuthServiceDep) -> UserResponse:
    user = service.register(body.email, body.password, body.name)
    return UserResponse(id=user.id, email=user.email, name=user.name)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, service: AuthServiceDep) -> TokenResponse:
    token = service.login(body.email, body.password)
    return TokenResponse(access_token=token, expires_in=settings.jwt_expire_minutes * 60)
