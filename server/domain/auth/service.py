from __future__ import annotations

from uuid import UUID, uuid4

from domain.auth.repository import AuthRepository
from domain.auth.schemas import LoginRequest, LogoutRequest, RefreshRequest, RegisterRequest, SessionRevocationResponse, SessionResponse
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
            session_id = self.auth_repository.create_session(player_id, hash_secret(refresh_token))
            return SessionResponse(
                player_id=str(player_id),
                session_id=str(session_id),
                access_token=f"access_{uuid4()}",
                refresh_token=refresh_token,
            )

        return SessionResponse(
            player_id=f"player_{identifier}",
            session_id=f"session_{uuid4()}",
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
            session_id = self.auth_repository.create_session(player_id, hash_secret(refresh_token))
            return SessionResponse(
                player_id=str(player_id),
                session_id=str(session_id),
                access_token=f"access_{uuid4()}",
                refresh_token=refresh_token,
            )

        return SessionResponse(
            player_id=f"player_{identifier}",
            session_id=f"session_{uuid4()}",
            access_token=f"stub_access_{uuid4()}",
            refresh_token=f"stub_refresh_{uuid4()}",
        )

    def refresh(self, payload: RefreshRequest) -> SessionResponse:
        identifier = payload.session_id.strip()
        if database_is_configured():
            session_id = UUID(identifier)
            session_credentials = self.auth_repository.get_active_session_credentials(session_id)
            if session_credentials is None:
                raise ValueError("Invalid session")

            player_id, refresh_token_hash = session_credentials
            if not verify_secret(payload.refresh_token, refresh_token_hash):
                raise ValueError("Invalid session")

            refresh_token = f"refresh_{uuid4()}"
            self.auth_repository.rotate_session_refresh_token(session_id, hash_secret(refresh_token))
            return SessionResponse(
                player_id=str(player_id),
                session_id=str(session_id),
                access_token=f"access_{uuid4()}",
                refresh_token=refresh_token,
            )

        return SessionResponse(
            player_id="player_stub",
            session_id=identifier,
            access_token=f"stub_access_{uuid4()}",
            refresh_token=f"stub_refresh_{uuid4()}",
        )

    def logout(self, payload: LogoutRequest) -> SessionRevocationResponse:
        identifier = payload.session_id.strip()
        if database_is_configured():
            session_id = UUID(identifier)
            session_credentials = self.auth_repository.get_session_credentials_including_revoked(session_id)
            if session_credentials is None:
                raise ValueError("Invalid session")

            _, refresh_token_hash = session_credentials
            if not verify_secret(payload.refresh_token, refresh_token_hash):
                raise ValueError("Invalid session")

            self.auth_repository.revoke_session(session_id)
            return SessionRevocationResponse(session_id=str(session_id), revoked=True)

        return SessionRevocationResponse(session_id=identifier, revoked=True)