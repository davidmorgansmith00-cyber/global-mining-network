from __future__ import annotations

from uuid import uuid4

from domain.auth.repository import AuthRepository
from domain.auth.schemas import LoginRequest, RegisterRequest, SessionResponse
from domain.players.repository import PlayerRepository
from shared.database import database_is_configured
from shared.security import hash_secret, verify_secret


class AuthService:
    def __init__(self) -> None:
        self.auth_repository = AuthRepository()
        self.player_repository = PlayerRepository()

    def register(self, payload: RegisterRequest) -> SessionResponse:
        identifier = payload.email.strip().lower().replace("@", "_").replace(".", "_")
        if database_is_configured():
            password_hash = hash_secret(payload.password)
            player_id = self.auth_repository.create_player(payload.email.strip().lower(), password_hash)
            self.player_repository.create_profile(player_id)
            refresh_token = f"refresh_{uuid4()}"
            self.auth_repository.create_session(player_id, hash_secret(refresh_token))
            return SessionResponse(
                player_id=str(player_id),
                access_token=f"access_{uuid4()}",
                refresh_token=refresh_token,
            )

        return SessionResponse(
            player_id=f"player_{identifier}",
            access_token=f"stub_access_{uuid4()}",
            refresh_token=f"stub_refresh_{uuid4()}",
        )

    def login(self, payload: LoginRequest) -> SessionResponse:
        identifier = payload.email.strip().lower().replace("@", "_").replace(".", "_")
        if database_is_configured():
            player_record = self.auth_repository.get_player_by_email(payload.email.strip().lower())
            if player_record is None:
                raise ValueError("Unknown player")

            player_id, password_hash = player_record
            if not verify_secret(payload.password, password_hash):
                raise ValueError("Invalid credentials")

            refresh_token = f"refresh_{uuid4()}"
            self.auth_repository.create_session(player_id, hash_secret(refresh_token))
            return SessionResponse(
                player_id=str(player_id),
                access_token=f"access_{uuid4()}",
                refresh_token=refresh_token,
            )

        return SessionResponse(
            player_id=f"player_{identifier}",
            access_token=f"stub_access_{uuid4()}",
            refresh_token=f"stub_refresh_{uuid4()}",
        )