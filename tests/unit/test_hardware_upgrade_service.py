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

from domain.hardware.upgrade_service import HardwareUpgradeService


class HardwareUpgradeServiceEtaCalculationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = HardwareUpgradeService()

    def test_eta_zero_when_cost_is_zero(self) -> None:
        eta = self.service.calculate_eta_to_upgrade(
            effective_hashrate=12.0,
            upgrade_cost=Decimal("0"),
            offline_cap_per_day=Decimal("1000"),
        )
        self.assertEqual(eta, 0)

    def test_eta_zero_when_cost_is_negative(self) -> None:
        eta = self.service.calculate_eta_to_upgrade(
            effective_hashrate=12.0,
            upgrade_cost=Decimal("-100"),
            offline_cap_per_day=Decimal("1000"),
        )
        self.assertEqual(eta, 0)

    def test_eta_calculation_typical_case(self) -> None:
        # upgrade_cost=2500, cap=1000/day → 2.5 days → 216000 seconds
        eta = self.service.calculate_eta_to_upgrade(
            effective_hashrate=12.0,
            upgrade_cost=Decimal("2500"),
            offline_cap_per_day=Decimal("1000"),
        )
        self.assertEqual(eta, 2500 * 86400 // 1000)

    def test_eta_is_large_when_cap_is_zero(self) -> None:
        eta = self.service.calculate_eta_to_upgrade(
            effective_hashrate=12.0,
            upgrade_cost=Decimal("2500"),
            offline_cap_per_day=Decimal("0"),
        )
        self.assertGreater(eta, 10**8)

    def test_eta_uses_remaining_cost_conservatively(self) -> None:
        # cap=5000/day, cost=8000 → 1.6 days → 138240 seconds
        eta = self.service.calculate_eta_to_upgrade(
            effective_hashrate=60.0,
            upgrade_cost=Decimal("8000"),
            offline_cap_per_day=Decimal("5000"),
        )
        expected = int(Decimal("8000") / Decimal("5000") * Decimal("86400"))
        self.assertEqual(eta, expected)


class HardwareTierProgressionValidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = HardwareUpgradeService()

    def test_three_tiers_defined(self) -> None:
        defs = self.service.get_all_tier_definitions()
        self.assertGreaterEqual(len(defs), 3)

    def test_tiers_are_ordered(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tiers = [d.tier for d in defs]
        self.assertEqual(tiers, sorted(tiers))

    def test_tier_one_starter_has_zero_price(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier1 = next((d for d in defs if d.tier == 1), None)
        self.assertIsNotNone(tier1)
        assert tier1 is not None
        self.assertEqual(tier1.market_price, Decimal("0"))

    def test_tier_two_has_positive_price(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier2 = next((d for d in defs if d.tier == 2), None)
        self.assertIsNotNone(tier2)
        assert tier2 is not None
        self.assertGreater(tier2.market_price, Decimal("0"))

    def test_tier_two_has_higher_hashrate_than_tier_one(self) -> None:
        defs = {d.tier: d for d in self.service.get_all_tier_definitions()}
        self.assertGreater(defs[2].base_hashrate, defs[1].base_hashrate)

    def test_tier_three_has_higher_hashrate_than_tier_two(self) -> None:
        defs = {d.tier: d for d in self.service.get_all_tier_definitions()}
        self.assertGreater(defs[3].base_hashrate, defs[2].base_hashrate)

    def test_all_tiers_have_positive_power_and_heat(self) -> None:
        for d in self.service.get_all_tier_definitions():
            self.assertGreater(d.base_power_consumption, 0, msg=d.hardware_id)
            self.assertGreater(d.base_heat_generation, 0, msg=d.hardware_id)

    def test_previous_and_next_tier_links_form_chain(self) -> None:
        defs = self.service.get_all_tier_definitions()
        by_id = {d.hardware_id: d for d in defs}
        for d in defs:
            if d.previous_tier is not None:
                self.assertIn(d.previous_tier, by_id, msg=f"{d.hardware_id}.previous_tier")
            if d.next_tier is not None:
                self.assertIn(d.next_tier, by_id, msg=f"{d.hardware_id}.next_tier")

    def test_is_hardware_tier_upgrade_returns_false_for_tier1(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier1 = next(d for d in defs if d.tier == 1)
        self.assertFalse(self.service.is_hardware_tier_upgrade(tier1.hardware_id))

    def test_is_hardware_tier_upgrade_returns_true_for_tier2(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier2 = next(d for d in defs if d.tier == 2)
        self.assertTrue(self.service.is_hardware_tier_upgrade(tier2.hardware_id))


class HardwareUpgradeUnlockConditionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = HardwareUpgradeService()

    def test_tier1_is_always_unlocked(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier1 = next(d for d in defs if d.tier == 1)
        self.assertIsNone(tier1.unlock_condition)

    def test_tier2_has_no_unlock_condition(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier2 = next(d for d in defs if d.tier == 2)
        self.assertIsNone(tier2.unlock_condition)

    def test_tier3_requires_player_tier_2(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier3 = next(d for d in defs if d.tier == 3)
        self.assertIsNotNone(tier3.unlock_condition)

    def test_upgrade_recommendation_for_tier1_player_tier1_not_blocked(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier1 = next(d for d in defs if d.tier == 1)
        rec = self.service.get_next_upgrade_recommendation(
            current_hardware_id=tier1.hardware_id,
            effective_hashrate=tier1.base_hashrate,
            offline_cap_per_day=Decimal("1000"),
            player_tier=1,
            current_balance=Decimal("0"),
        )
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertFalse(rec.unlock_blocked)

    def test_tier3_upgrade_blocked_for_player_tier1(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier2 = next(d for d in defs if d.tier == 2)
        rec = self.service.get_next_upgrade_recommendation(
            current_hardware_id=tier2.hardware_id,
            effective_hashrate=tier2.base_hashrate,
            offline_cap_per_day=Decimal("5000"),
            player_tier=1,
            current_balance=Decimal("0"),
        )
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertTrue(rec.unlock_blocked)

    def test_tier3_upgrade_not_blocked_for_player_tier2(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier2 = next(d for d in defs if d.tier == 2)
        rec = self.service.get_next_upgrade_recommendation(
            current_hardware_id=tier2.hardware_id,
            effective_hashrate=tier2.base_hashrate,
            offline_cap_per_day=Decimal("5000"),
            player_tier=2,
            current_balance=Decimal("0"),
        )
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertFalse(rec.unlock_blocked)

    def test_no_upgrade_recommendation_at_max_tier(self) -> None:
        defs = self.service.get_all_tier_definitions()
        max_tier_def = max(defs, key=lambda d: d.tier)
        rec = self.service.get_next_upgrade_recommendation(
            current_hardware_id=max_tier_def.hardware_id,
            effective_hashrate=max_tier_def.base_hashrate,
            offline_cap_per_day=Decimal("10000"),
            player_tier=3,
            current_balance=Decimal("0"),
        )
        self.assertIsNone(rec)

    def test_eta_zero_when_player_can_already_afford(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier1 = next(d for d in defs if d.tier == 1)
        tier2 = next(d for d in defs if d.tier == 2)
        rec = self.service.get_next_upgrade_recommendation(
            current_hardware_id=tier1.hardware_id,
            effective_hashrate=tier1.base_hashrate,
            offline_cap_per_day=Decimal("1000"),
            player_tier=1,
            current_balance=tier2.market_price,
        )
        self.assertIsNotNone(rec)
        assert rec is not None
        self.assertEqual(rec.eta_seconds, 0)

    def test_upgrade_progression_shows_all_tiers(self) -> None:
        defs = self.service.get_all_tier_definitions()
        tier1 = next(d for d in defs if d.tier == 1)
        progression = self.service.get_upgrade_progression(
            current_hardware_id=tier1.hardware_id,
            owned_hardware_ids=set(),
            player_tier=1,
        )
        self.assertGreaterEqual(len(progression), 3)
        current = next((e for e in progression if e.is_current), None)
        self.assertIsNotNone(current)
        assert current is not None
        self.assertEqual(current.hardware_id, tier1.hardware_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
