from __future__ import annotations

from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

from shared.database import open_connection


class AuthRepository:
    def create_player(self, email: str, password_hash: str) -> UUID:
        player_id = uuid4()
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO players (player_id, email, password_hash)
                    VALUES (%s, %s, %s)
                    RETURNING player_id
                    """,
                    (player_id, email, password_hash),
                )
                created_player_id = cursor.fetchone()[0]
            connection.commit()
        return created_player_id

    def get_player_by_email(self, email: str) -> tuple[UUID, str] | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT player_id, password_hash FROM players WHERE email = %s",
                    (email,),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return row[0], row[1]

    def create_session(self, player_id: UUID, refresh_token_hash: str, device_label: str | None = None) -> UUID:
        session_id = uuid4()
        expires_at = datetime.now(UTC) + timedelta(days=30)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO auth_sessions (session_id, player_id, refresh_token_hash, device_label, expires_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (session_id, player_id, refresh_token_hash, device_label, expires_at),
                )
            connection.commit()
        return session_id

    def get_active_session_credentials(self, session_id: UUID) -> tuple[UUID, str] | None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT player_id, refresh_token_hash
                    FROM auth_sessions
                    WHERE session_id = %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                    LIMIT 1
                    """,
                    (session_id,),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return row[0], row[1]

    def rotate_session_refresh_token(self, session_id: UUID, refresh_token_hash: str) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auth_sessions
                    SET refresh_token_hash = %s,
                        expires_at = NOW() + INTERVAL '30 days'
                    WHERE session_id = %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                    """,
                    (refresh_token_hash, session_id),
                )
            connection.commit()

    def revoke_session(self, session_id: UUID) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auth_sessions
                    SET revoked_at = NOW()
                    WHERE session_id = %s
                      AND revoked_at IS NULL
                    """,
                    (session_id,),
                )
            connection.commit()

    def is_active_session_for_player(self, *, player_id: UUID, session_id: UUID) -> bool:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT 1
                    FROM auth_sessions
                    WHERE player_id = %s
                      AND session_id = %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                    LIMIT 1
                    """,
                    (player_id, session_id),
                )
                row = cursor.fetchone()
        return row is not None