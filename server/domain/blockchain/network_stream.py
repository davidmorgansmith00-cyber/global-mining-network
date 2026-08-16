from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import json
from threading import Lock
from typing import Protocol

from shared.database import database_is_configured, open_connection


@dataclass(frozen=True)
class NetworkEvent:
    sequence: int
    event_type: str
    occurred_at: datetime
    payload: dict[str, object]


class NetworkEventStream(Protocol):
    def publish(self, *, event_type: str, payload: dict[str, object]) -> NetworkEvent: ...

    def list_after(self, *, after_sequence: int | None, limit: int) -> list[NetworkEvent]: ...

    def latest_sequence(self) -> int: ...

    def reset(self) -> None: ...


class InMemoryNetworkEventStream:
    def __init__(self) -> None:
        self._lock = Lock()
        self._sequence = 0
        self._events: list[NetworkEvent] = []

    def publish(self, *, event_type: str, payload: dict[str, object]) -> NetworkEvent:
        with self._lock:
            self._sequence += 1
            event = NetworkEvent(
                sequence=self._sequence,
                event_type=event_type,
                occurred_at=datetime.now(UTC),
                payload=payload,
            )
            self._events.append(event)
            return event

    def list_after(self, *, after_sequence: int | None, limit: int) -> list[NetworkEvent]:
        with self._lock:
            floor = after_sequence or 0
            filtered = [item for item in self._events if item.sequence > floor]
            return filtered[:limit]

    def latest_sequence(self) -> int:
        with self._lock:
            return self._sequence

    def reset(self) -> None:
        with self._lock:
            self._sequence = 0
            self._events.clear()


class PostgresNetworkEventStream:
    def publish(self, *, event_type: str, payload: dict[str, object]) -> NetworkEvent:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO network_events (event_type, payload)
                    VALUES (%s, %s::jsonb)
                    RETURNING sequence, event_type, occurred_at, payload
                    """,
                    (event_type, json.dumps(payload)),
                )
                row = cursor.fetchone()
            connection.commit()
        return NetworkEvent(
            sequence=row[0],
            event_type=row[1],
            occurred_at=row[2].astimezone(UTC),
            payload=row[3],
        )

    def list_after(self, *, after_sequence: int | None, limit: int) -> list[NetworkEvent]:
        floor = after_sequence or 0
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT sequence, event_type, occurred_at, payload
                    FROM network_events
                    WHERE sequence > %s
                    ORDER BY sequence ASC
                    LIMIT %s
                    """,
                    (floor, limit),
                )
                rows = cursor.fetchall()
        return [
            NetworkEvent(
                sequence=row[0],
                event_type=row[1],
                occurred_at=row[2].astimezone(UTC),
                payload=row[3],
            )
            for row in rows
        ]

    def latest_sequence(self) -> int:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COALESCE(MAX(sequence), 0) FROM network_events")
                return cursor.fetchone()[0]

    def reset(self) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("TRUNCATE TABLE network_events RESTART IDENTITY")
            connection.commit()


_GLOBAL_NETWORK_EVENT_STREAM: NetworkEventStream | None = None


def get_network_event_stream() -> NetworkEventStream:
    global _GLOBAL_NETWORK_EVENT_STREAM
    if _GLOBAL_NETWORK_EVENT_STREAM is None:
        if database_is_configured():
            _GLOBAL_NETWORK_EVENT_STREAM = PostgresNetworkEventStream()
        else:
            _GLOBAL_NETWORK_EVENT_STREAM = InMemoryNetworkEventStream()
    return _GLOBAL_NETWORK_EVENT_STREAM


def reset_network_event_stream() -> None:
    stream = get_network_event_stream()
    stream.reset()
