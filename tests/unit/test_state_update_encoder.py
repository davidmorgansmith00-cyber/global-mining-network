from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.streaming.encoder import (
    ALL_SUBSCRIPTIONS,
    SUBSCRIPTION_FIELD_MAP,
    StateUpdateEncoder,
)


def _make_state(**overrides: object) -> dict:
    base: dict = {
        "player_id": "player_alpha",
        "effective_hashrate": 12.5,
        "power_consumed": 100.0,
        "power_capacity": 150.0,
        "power_throttle_multiplier": 1.0,
        "heat_generated": 50.2,
        "cooling_capacity": 100.0,
        "cooling_efficiency_multiplier": 1.0,
        "reward_balance": 1250.0,
        "player_tier": 1,
        "hardware_id": "starter_rusty_home_computer",
        "base_hashrate": 12.5,
        "offline_work_pending": False,
        "last_update_at": "2026-08-18T02:30:00Z",
    }
    base.update(overrides)
    return base


class TestStateUpdateEncoderFullState(unittest.TestCase):
    def setUp(self) -> None:
        self.encoder = StateUpdateEncoder()

    def test_full_state_type_is_full_state(self) -> None:
        msg = self.encoder.encode_full_state(_make_state())
        self.assertEqual(msg["type"], "full_state")

    def test_full_state_player_id_matches(self) -> None:
        msg = self.encoder.encode_full_state(_make_state(player_id="abc"))
        self.assertEqual(msg["player_id"], "abc")

    def test_full_state_contains_state_key_with_all_fields(self) -> None:
        state = _make_state()
        msg = self.encoder.encode_full_state(state)
        self.assertIn("state", msg)
        for field in ("effective_hashrate", "power_consumed", "reward_balance", "player_tier"):
            self.assertIn(field, msg["state"])

    def test_full_state_coerces_decimal_to_float(self) -> None:
        state = _make_state(reward_balance=Decimal("1250.50"))
        msg = self.encoder.encode_full_state(state)
        balance = msg["state"]["reward_balance"]
        self.assertIsInstance(balance, float)
        self.assertAlmostEqual(balance, 1250.50)

    def test_full_state_none_player_id_propagates(self) -> None:
        state = _make_state()
        state.pop("player_id")
        msg = self.encoder.encode_full_state(state)
        self.assertIsNone(msg["player_id"])


class TestStateUpdateEncoderDelta(unittest.TestCase):
    def setUp(self) -> None:
        self.encoder = StateUpdateEncoder()

    def test_delta_returns_none_when_nothing_changed(self) -> None:
        state = _make_state()
        result = self.encoder.encode_delta(state, state, "test")
        self.assertIsNone(result)

    def test_delta_type_is_state_delta(self) -> None:
        prev = _make_state()
        curr = _make_state(effective_hashrate=27.5)
        result = self.encoder.encode_delta(prev, curr, "hardware_upgrade")
        self.assertIsNotNone(result)
        assert result is not None
        self.assertEqual(result["type"], "state_delta")

    def test_delta_contains_only_changed_fields(self) -> None:
        prev = _make_state()
        curr = _make_state(effective_hashrate=27.5, reward_balance=1500.0)
        result = self.encoder.encode_delta(prev, curr, "hardware_upgrade")
        assert result is not None
        self.assertIn("effective_hashrate", result["changes"])
        self.assertIn("reward_balance", result["changes"])
        self.assertNotIn("power_consumed", result["changes"])
        self.assertNotIn("player_tier", result["changes"])

    def test_delta_reason_matches_event_type(self) -> None:
        prev = _make_state()
        curr = _make_state(effective_hashrate=27.5)
        result = self.encoder.encode_delta(prev, curr, "hardware_upgrade")
        assert result is not None
        self.assertEqual(result["reason"], "hardware_upgrade")

    def test_delta_excludes_player_id_from_changes(self) -> None:
        prev = _make_state(player_id="old")
        curr = _make_state(player_id="new")
        # player_id change alone should produce no changes (player_id excluded from diff)
        result = self.encoder.encode_delta(prev, curr, "test")
        self.assertIsNone(result)

    def test_delta_coerces_decimal_to_float(self) -> None:
        prev = _make_state(reward_balance=1000.0)
        curr = _make_state(reward_balance=Decimal("1500.50"))
        result = self.encoder.encode_delta(prev, curr, "balance_update")
        assert result is not None
        balance = result["changes"]["reward_balance"]
        self.assertIsInstance(balance, float)
        self.assertAlmostEqual(balance, 1500.50)

    def test_delta_no_false_positive_decimal_vs_float_equal_values(self) -> None:
        prev = _make_state(reward_balance=Decimal("1000.0"))
        curr = _make_state(reward_balance=1000.0)
        result = self.encoder.encode_delta(prev, curr, "test")
        # 1000.0 decimal == 1000.0 float after serialisation → no change
        self.assertIsNone(result)

    def test_delta_player_id_in_top_level_not_changes(self) -> None:
        prev = _make_state()
        curr = _make_state(effective_hashrate=20.0)
        result = self.encoder.encode_delta(prev, curr, "test")
        assert result is not None
        self.assertEqual(result["player_id"], "player_alpha")
        self.assertNotIn("player_id", result["changes"])


class TestStateUpdateEncoderSubscriptionFiltering(unittest.TestCase):
    def setUp(self) -> None:
        self.encoder = StateUpdateEncoder()
        self._base_delta: dict = {
            "type": "state_delta",
            "player_id": "player_alpha",
            "changes": {
                "effective_hashrate": 27.5,
                "reward_balance": 1500.0,
                "player_tier": 2,
                "hardware_id": "improved_workstation",
                "power_consumed": 180.0,
            },
            "reason": "hardware_upgrade",
            "timestamp": "2026-08-18T02:35:00Z",
        }

    def test_empty_subscriptions_returns_full_delta(self) -> None:
        result = self.encoder.get_fields_for_subscription([], self._base_delta)
        self.assertEqual(result, self._base_delta)

    def test_hashrate_subscription_includes_effective_hashrate(self) -> None:
        result = self.encoder.get_fields_for_subscription(["hashrate_updates"], self._base_delta)
        self.assertIn("effective_hashrate", result["changes"])

    def test_hashrate_subscription_excludes_balance_fields(self) -> None:
        result = self.encoder.get_fields_for_subscription(["hashrate_updates"], self._base_delta)
        self.assertNotIn("reward_balance", result["changes"])

    def test_balance_subscription_includes_reward_balance(self) -> None:
        result = self.encoder.get_fields_for_subscription(["balance_updates"], self._base_delta)
        self.assertIn("reward_balance", result["changes"])

    def test_balance_subscription_excludes_hashrate_fields(self) -> None:
        result = self.encoder.get_fields_for_subscription(["balance_updates"], self._base_delta)
        self.assertNotIn("effective_hashrate", result["changes"])

    def test_tier_subscription_includes_player_tier(self) -> None:
        result = self.encoder.get_fields_for_subscription(["tier_updates"], self._base_delta)
        self.assertIn("player_tier", result["changes"])

    def test_hardware_subscription_includes_hardware_id(self) -> None:
        result = self.encoder.get_fields_for_subscription(["hardware_updates"], self._base_delta)
        self.assertIn("hardware_id", result["changes"])

    def test_all_subscriptions_returns_all_known_fields(self) -> None:
        result = self.encoder.get_fields_for_subscription(ALL_SUBSCRIPTIONS, self._base_delta)
        for field in ("effective_hashrate", "reward_balance", "player_tier", "hardware_id", "power_consumed"):
            self.assertIn(field, result["changes"])

    def test_no_matching_fields_returns_empty_dict(self) -> None:
        delta = {
            "type": "state_delta",
            "player_id": "player_alpha",
            "changes": {"some_unknown_field": 42},
            "reason": "unknown",
            "timestamp": "2026-08-18T02:35:00Z",
        }
        result = self.encoder.get_fields_for_subscription(["hashrate_updates"], delta)
        self.assertEqual(result, {})

    def test_multiple_subscriptions_union_fields(self) -> None:
        result = self.encoder.get_fields_for_subscription(
            ["hashrate_updates", "balance_updates"],
            self._base_delta,
        )
        self.assertIn("effective_hashrate", result["changes"])
        self.assertIn("reward_balance", result["changes"])


class TestStateUpdateEncoderOfflineReconciliation(unittest.TestCase):
    def setUp(self) -> None:
        self.encoder = StateUpdateEncoder()

    def test_offline_reconciliation_type(self) -> None:
        msg = self.encoder.encode_offline_reconciliation(
            player_id="player_alpha",
            offline_duration_seconds=3600,
            offline_work_credited=Decimal("36000"),
            offline_cap_applied=True,
            offline_cap_tier=1,
            changes={"reward_balance": 2500.0},
        )
        self.assertEqual(msg["type"], "offline_reconciliation")

    def test_offline_reconciliation_fields_present(self) -> None:
        msg = self.encoder.encode_offline_reconciliation(
            player_id="player_alpha",
            offline_duration_seconds=3600,
            offline_work_credited=Decimal("36000"),
            offline_cap_applied=True,
            offline_cap_tier=1,
            changes={"reward_balance": 2500.0},
        )
        self.assertEqual(msg["player_id"], "player_alpha")
        self.assertEqual(msg["offline_duration_seconds"], 3600)
        self.assertTrue(msg["offline_cap_applied"])
        self.assertEqual(msg["offline_cap_tier"], 1)
        self.assertIn("reward_balance", msg["changes"])

    def test_offline_reconciliation_coerces_decimal(self) -> None:
        msg = self.encoder.encode_offline_reconciliation(
            player_id="player_alpha",
            offline_duration_seconds=1800,
            offline_work_credited=Decimal("500.25"),
            offline_cap_applied=False,
            offline_cap_tier=2,
            changes={"reward_balance": Decimal("3000")},
        )
        self.assertIsInstance(msg["offline_work_credited"], float)
        self.assertAlmostEqual(msg["offline_work_credited"], 500.25)
        self.assertIsInstance(msg["changes"]["reward_balance"], float)


class TestSubscriptionFieldMapCompleteness(unittest.TestCase):
    def test_all_subscriptions_in_field_map(self) -> None:
        for sub in ALL_SUBSCRIPTIONS:
            self.assertIn(sub, SUBSCRIPTION_FIELD_MAP)
            self.assertGreater(len(SUBSCRIPTION_FIELD_MAP[sub]), 0)

    def test_known_subscription_names(self) -> None:
        expected = {"hashrate_updates", "balance_updates", "hardware_updates", "market_updates", "tier_updates"}
        self.assertEqual(set(ALL_SUBSCRIPTIONS), expected)


if __name__ == "__main__":
    unittest.main(verbosity=2)
