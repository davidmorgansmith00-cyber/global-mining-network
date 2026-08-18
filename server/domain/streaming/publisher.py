from __future__ import annotations

import json
from typing import Any

from shared.logging import get_logger
from shared.settings import settings


logger = get_logger("gmn.streaming.publisher")

_pool: Any = None


def _get_pool() -> Any:
    """Return the module-level Redis connection pool, creating it on first use."""
    global _pool  # noqa: PLW0603
    if _pool is None and settings.redis_url:
        try:
            import redis  # type: ignore[import-untyped]

            _pool = redis.ConnectionPool.from_url(settings.redis_url)
        except Exception as exc:
            logger.warning("redis_pool_creation_failed", extra={"error": str(exc)})
    return _pool


def publish_player_state_change(player_id: str, delta: dict[str, Any]) -> None:
    """Publish a state-change delta to the player's Redis pub/sub channel.

    This is a synchronous, fire-and-forget call.  If Redis is not configured
    or is unreachable the error is logged and the call returns silently so
    that the rest of the request pipeline is unaffected.

    Subscribing WebSocket handlers (see ``api/v1/stream.py``) receive these
    events and forward them to the connected client after applying the
    client's subscription filters.
    """
    if not settings.redis_url:
        return

    pool = _get_pool()
    if pool is None:
        return

    try:
        import redis  # type: ignore[import-untyped]

        client: Any = redis.Redis(connection_pool=pool)
        channel = f"player:{player_id}:updates"
        client.publish(channel, json.dumps(delta))
    except Exception as exc:
        logger.warning(
            "publish_state_change_failed",
            extra={"player_id": player_id, "error": str(exc)},
        )

