from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect

from domain.auth.repository import AuthRepository
from domain.market.service import NpcMarketService
from domain.players.service import PlayerProfileService
from domain.players.schemas import PlayerProfileResponse
from domain.streaming.encoder import ALL_SUBSCRIPTIONS, StateUpdateEncoder
from shared.database import database_is_configured
from shared.logging import get_logger
from shared.settings import settings


router = APIRouter(prefix="/players", tags=["stream"])

logger = get_logger("gmn.stream")
encoder = StateUpdateEncoder()
auth_repository = AuthRepository()
profile_service = PlayerProfileService()
market_service = NpcMarketService()

HEARTBEAT_INTERVAL_SECONDS = 30


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _profile_to_state_dict(profile: PlayerProfileResponse, reward_balance: Decimal | None = None) -> dict[str, Any]:
    """Convert a PlayerProfileResponse to the canonical WebSocket state dict."""
    last_update: str = datetime.now(tz=timezone.utc).isoformat()
    return {
        "player_id": profile.player_id,
        "effective_hashrate": profile.effective_hashrate,
        "power_consumed": profile.power_consumed,
        "power_capacity": profile.power_capacity,
        "power_throttle_multiplier": profile.power_throttle_multiplier,
        "heat_generated": profile.heat_generated,
        "cooling_capacity": profile.cooling_capacity,
        "cooling_efficiency_multiplier": profile.cooling_efficiency_multiplier,
        "reward_balance": float(reward_balance) if reward_balance is not None else None,
        "player_tier": profile.player_tier,
        "hardware_id": profile.hardware_id,
        "base_hashrate": profile.base_hashrate,
        "offline_work_pending": False,
        "last_update_at": last_update,
    }


def _get_reward_balance(player_id: str) -> Decimal | None:
    """Return the player's current reward balance, or None if unavailable."""
    if not database_is_configured():
        return None
    try:
        return market_service.get_player_reward_balance(player_id)
    except Exception:
        return None


# ---------------------------------------------------------------------------
# Heartbeat background task
# ---------------------------------------------------------------------------


async def _send_heartbeats(websocket: WebSocket) -> None:
    """Continuously send ping frames every HEARTBEAT_INTERVAL_SECONDS."""
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        try:
            await websocket.send_text(json.dumps({"type": "ping"}))
        except Exception:
            break


# ---------------------------------------------------------------------------
# Redis subscriber background task
# ---------------------------------------------------------------------------


async def _redis_listener(
    websocket: WebSocket,
    player_id: str,
    subscriptions_ref: list[list[str]],
) -> None:
    """Subscribe to the player's Redis channel and forward filtered deltas."""
    if not settings.redis_url:
        return

    client: Any = None
    try:
        import redis.asyncio as aioredis  # type: ignore[import-untyped]

        client = aioredis.from_url(settings.redis_url)
        pubsub = client.pubsub()
        channel = f"player:{player_id}:updates"
        await pubsub.subscribe(channel)
        async for message in pubsub.listen():  # type: ignore[union-attr]
            if message["type"] == "message":
                data: Any = json.loads(message["data"])
                # Read current subscriptions from the shared mutable container
                filtered = encoder.get_fields_for_subscription(subscriptions_ref[0], data)
                if filtered:
                    await websocket.send_text(json.dumps(filtered))
    except asyncio.CancelledError:
        pass
    except Exception as exc:
        logger.warning("redis_listener_error", extra={"player_id": player_id, "error": str(exc)})
    finally:
        if client is not None:
            try:
                await client.aclose()
            except Exception:
                pass


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------


@router.websocket("/stream/{player_id}")
async def player_stream(
    websocket: WebSocket,
    player_id: str,
    session_id: str = Query(..., description="Active session id for authentication"),
) -> None:
    """Real-time player state stream.

    Protocol
    --------
    1. Client connects with ``?session_id=<uuid>``.
    2. Server authenticates and sends a ``full_state`` message.
    3. If offline work was processed during reconnect an additional
       ``offline_reconciliation`` message is sent.
    4. Client may send ``{"action": "subscribe", "subscriptions": [...]}``
       to narrow the event stream.
    5. Server sends ``state_delta`` messages whenever player state changes.
    6. Server sends ``{"type": "ping"}`` every 30 seconds as a keep-alive.
    7. On disconnect the client should reconnect with exponential back-off
       (1 s → 2 s → 4 s … capped at 30 s) and re-request full state.

    Fallback
    --------
    If WebSockets are unavailable the client may poll
    ``GET /api/v1/players/profile?player_id=<id>`` every 5 seconds and
    compare ``last_update_at`` to detect changes.

    Error codes
    -----------
    4001 – authentication failed (invalid or expired session_id)
    4003 – player_id does not match authenticated session
    """
    # ---- authentication -----------------------------------------------
    try:
        session_uuid = UUID(session_id)
    except ValueError:
        await websocket.close(code=4001, reason="auth_failed")
        return

    session_credentials = auth_repository.get_active_session_credentials(session_uuid)
    if session_credentials is None:
        await websocket.close(code=4001, reason="session_expired")
        return

    authenticated_player_id = str(session_credentials[0])
    if authenticated_player_id != player_id:
        await websocket.close(code=4003, reason="auth_failed")
        return

    await websocket.accept()
    logger.info("websocket_connected", extra={"player_id": player_id})

    # ---- send initial full state --------------------------------------
    profile = profile_service.get_profile(player_id=player_id)
    reward_balance = _get_reward_balance(player_id)
    state_dict = _profile_to_state_dict(profile, reward_balance)
    await websocket.send_text(json.dumps(encoder.encode_full_state(state_dict)))

    # ---- offline reconciliation on connect ---------------------------
    offline_credited = profile.offline_work_earned
    if offline_credited > Decimal("0"):
        recon_msg = encoder.encode_offline_reconciliation(
            player_id=player_id,
            offline_duration_seconds=0,  # duration already collapsed into credited_work
            offline_work_credited=offline_credited,
            offline_cap_applied=profile.offline_cap_applied,
            offline_cap_tier=profile.player_tier,
            changes={
                "reward_balance": float(reward_balance) if reward_balance is not None else None,
                "last_update_at": state_dict["last_update_at"],
            },
        )
        await websocket.send_text(json.dumps(recon_msg))

    # ---- default subscriptions: all event types ----------------------
    subscriptions: list[str] = list(ALL_SUBSCRIPTIONS)
    # Mutable single-element container so the Redis listener always sees
    # the current subscription list even after client updates.
    subscriptions_ref: list[list[str]] = [subscriptions]

    # ---- start background tasks --------------------------------------
    heartbeat_task = asyncio.create_task(_send_heartbeats(websocket))
    redis_task = asyncio.create_task(_redis_listener(websocket, player_id, subscriptions_ref))

    # ---- main receive loop -------------------------------------------
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg: dict[str, Any] = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = msg.get("action")
            if action == "subscribe":
                subscriptions = msg.get("subscriptions", list(ALL_SUBSCRIPTIONS))
                subscriptions_ref[0] = subscriptions
            elif action == "unsubscribe":
                to_remove: set[str] = set(msg.get("subscriptions", []))
                subscriptions = [s for s in subscriptions if s not in to_remove]
                subscriptions_ref[0] = subscriptions
            elif action == "pong":
                pass  # client acknowledging our ping
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", extra={"player_id": player_id})
    finally:
        heartbeat_task.cancel()
        redis_task.cancel()
        try:
            await asyncio.gather(heartbeat_task, redis_task, return_exceptions=True)
        except Exception:
            pass
