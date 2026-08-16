from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID, uuid4

from domain.auth.repository import AuthRepository
from shared.database import database_is_configured, open_connection


@dataclass(frozen=True)
class ClientCheckpoint:
    player_id: str
    session_id: str
    channel: str
    reconnect_cursor: int


class ClientSessionService:
    def __init__(self) -> None:
        self.auth_repository = AuthRepository()
        self._memory_checkpoints: dict[tuple[str, str, str], int] = {}

    def validate_session_binding(self, *, player_id: str, session_id: str) -> bool:
        try:
            player_uuid = UUID(player_id)
            session_uuid = UUID(session_id)
        except ValueError:
            return False

        if not database_is_configured():
            return True
        return self.auth_repository.is_active_session_for_player(player_id=player_uuid, session_id=session_uuid)

    def resolve_player_id_from_session(self, *, session_id: str) -> str | None:
        try:
            session_uuid = UUID(session_id)
        except ValueError:
            return None

        if not database_is_configured():
            return None

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT player_id
                    FROM auth_sessions
                    WHERE session_id = %s
                      AND revoked_at IS NULL
                      AND expires_at > NOW()
                    LIMIT 1
                    """,
                    (session_uuid,),
                )
                row = cursor.fetchone()

        if row is None:
            return None
        return str(row[0])

    def get_checkpoint(self, *, player_id: str, session_id: str, channel: str) -> ClientCheckpoint | None:
        if not database_is_configured():
            key = (player_id, session_id, channel)
            cursor = self._memory_checkpoints.get(key)
            if cursor is None:
                return None
            return ClientCheckpoint(player_id=player_id, session_id=session_id, channel=channel, reconnect_cursor=cursor)

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT reconnect_cursor
                    FROM client_event_checkpoints
                    WHERE player_id = %s
                      AND session_id = %s
                      AND channel = %s
                    """,
                    (UUID(player_id), UUID(session_id), channel),
                )
                row = cursor.fetchone()
        if row is None:
            return None
        return ClientCheckpoint(player_id=player_id, session_id=session_id, channel=channel, reconnect_cursor=row[0])

    def upsert_checkpoint(self, *, player_id: str, session_id: str, channel: str, reconnect_cursor: int) -> None:
        if not database_is_configured():
            self._memory_checkpoints[(player_id, session_id, channel)] = reconnect_cursor
            return

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO client_event_checkpoints (checkpoint_id, player_id, session_id, channel, reconnect_cursor)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (player_id, session_id, channel)
                    DO UPDATE SET reconnect_cursor = EXCLUDED.reconnect_cursor, updated_at = NOW()
                    """,
                    (uuid4(), UUID(player_id), UUID(session_id), channel, reconnect_cursor),
                )
            connection.commit()
