from __future__ import annotations

from dataclasses import dataclass

from shared.database import database_is_configured, open_connection


@dataclass(frozen=True)
class CleanupResult:
    deleted_network_events_by_age: int
    deleted_network_events_by_count: int
    deleted_client_checkpoints: int


class BlockchainRetentionService:
    def cleanup(
        self,
        *,
        event_retention_seconds: int,
        checkpoint_retention_seconds: int,
        max_network_events: int,
    ) -> CleanupResult:
        if not database_is_configured():
            return CleanupResult(0, 0, 0)

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM network_events
                    WHERE occurred_at < NOW() - (%s * INTERVAL '1 second')
                    """,
                    (event_retention_seconds,),
                )
                deleted_by_age = cursor.rowcount

                cursor.execute(
                    """
                    WITH keep AS (
                        SELECT sequence
                        FROM network_events
                        ORDER BY sequence DESC
                        LIMIT %s
                    )
                    DELETE FROM network_events
                    WHERE sequence NOT IN (SELECT sequence FROM keep)
                    """,
                    (max_network_events,),
                )
                deleted_by_count = cursor.rowcount

                cursor.execute(
                    """
                    DELETE FROM client_event_checkpoints
                    WHERE updated_at < NOW() - (%s * INTERVAL '1 second')
                    """,
                    (checkpoint_retention_seconds,),
                )
                deleted_checkpoints = cursor.rowcount
            connection.commit()

        return CleanupResult(
            deleted_network_events_by_age=deleted_by_age,
            deleted_network_events_by_count=deleted_by_count,
            deleted_client_checkpoints=deleted_checkpoints,
        )
