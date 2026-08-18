from __future__ import annotations

from decimal import Decimal
from typing import Any


# Maps subscription names to the state fields they cover.
SUBSCRIPTION_FIELD_MAP: dict[str, set[str]] = {
    "hashrate_updates": {
        "effective_hashrate",
        "power_throttle_multiplier",
        "cooling_efficiency_multiplier",
        "base_hashrate",
    },
    "balance_updates": {
        "reward_balance",
        "offline_work_credited",
        "offline_cap_applied",
    },
    "hardware_updates": {
        "hardware_id",
        "power_consumed",
        "heat_generated",
        "base_hashrate",
        "cooling_capacity",
        "power_capacity",
    },
    "market_updates": {
        "market_stock_changed",
    },
    "tier_updates": {
        "player_tier",
    },
}

ALL_SUBSCRIPTIONS: list[str] = list(SUBSCRIPTION_FIELD_MAP.keys())


def _serialise(value: Any) -> Any:
    """Coerce Decimal values to float so they are JSON-serialisable."""
    if isinstance(value, Decimal):
        return float(value)
    return value


class StateUpdateEncoder:
    """Encodes player state into WebSocket-ready delta messages.

    All methods are pure / deterministic — same input always produces the
    same output.  No I/O is performed here.
    """

    def encode_full_state(self, player_state: dict[str, Any]) -> dict[str, Any]:
        """Return a ``full_state`` message containing the entire player state.

        This is the first message sent after a WebSocket connection is
        established.  Clients use it as the baseline for subsequent deltas.
        """
        serialised = {k: _serialise(v) for k, v in player_state.items()}
        return {
            "type": "full_state",
            "player_id": player_state.get("player_id"),
            "state": serialised,
        }

    def encode_delta(
        self,
        prev_state: dict[str, Any],
        curr_state: dict[str, Any],
        event_type: str,
    ) -> dict[str, Any] | None:
        """Return a ``state_delta`` message containing only changed fields.

        Returns ``None`` when nothing has changed so callers can skip sending.
        """
        changes: dict[str, Any] = {}
        for key, value in curr_state.items():
            if key == "player_id":
                continue
            prev = prev_state.get(key)
            # Compare after normalising Decimal → float to avoid false positives
            normalised_curr = _serialise(value)
            normalised_prev = _serialise(prev) if prev is not None else None
            if normalised_curr != normalised_prev:
                changes[key] = normalised_curr

        if not changes:
            return None

        return {
            "type": "state_delta",
            "player_id": curr_state.get("player_id"),
            "changes": changes,
            "reason": event_type,
            "timestamp": curr_state.get("last_update_at"),
        }

    def get_fields_for_subscription(
        self,
        subscriptions: list[str],
        delta: dict[str, Any],
    ) -> dict[str, Any]:
        """Filter a delta message to include only fields relevant to the
        given subscription list.

        If *subscriptions* is empty the full delta is returned unchanged.
        Returns an empty dict when the filtered delta would carry no changes.
        """
        if not subscriptions:
            return delta

        allowed: set[str] = set()
        for sub in subscriptions:
            allowed |= SUBSCRIPTION_FIELD_MAP.get(sub, set())

        changes = delta.get("changes", {})
        filtered = {k: v for k, v in changes.items() if k in allowed}
        if not filtered:
            return {}

        return {**delta, "changes": filtered}

    def encode_offline_reconciliation(
        self,
        *,
        player_id: str,
        offline_duration_seconds: int,
        offline_work_credited: Any,
        offline_cap_applied: bool,
        offline_cap_tier: int,
        changes: dict[str, Any],
    ) -> dict[str, Any]:
        """Return an ``offline_reconciliation`` message for reconnecting players.

        This is sent once on reconnect when the server detects that offline
        work has been processed while the player was disconnected.
        """
        return {
            "type": "offline_reconciliation",
            "player_id": player_id,
            "offline_duration_seconds": offline_duration_seconds,
            "offline_work_credited": _serialise(offline_work_credited),
            "offline_cap_applied": offline_cap_applied,
            "offline_cap_tier": offline_cap_tier,
            "changes": {k: _serialise(v) for k, v in changes.items()},
        }
