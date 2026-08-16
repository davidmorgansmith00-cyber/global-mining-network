from fastapi import APIRouter, HTTPException, status

from domain.auth.schemas import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, SessionRevocationResponse, SessionResponse
from domain.auth.service import AuthService


router = APIRouter(prefix="/auth", tags=["auth"])
service = AuthService()


@router.post("/register", response_model=SessionResponse, status_code=status.HTTP_200_OK)
def register(payload: RegisterRequest) -> SessionResponse:
    try:
        return service.register(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/login", response_model=SessionResponse, status_code=status.HTTP_200_OK)
def login(payload: LoginRequest) -> SessionResponse:
    try:
        return service.login(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/refresh", response_model=SessionResponse, status_code=status.HTTP_200_OK)
def refresh(payload: RefreshRequest) -> SessionResponse:
    try:
        return service.refresh(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc


@router.post("/logout", response_model=SessionRevocationResponse, status_code=status.HTTP_200_OK)
def logout(payload: LogoutRequest) -> SessionRevocationResponse:
    try:
        return service.logout(payload)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)) from exc