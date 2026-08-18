from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.mining.service import MiningSimulationService
from domain.players.service import PlayerProfileService


class PlayerProgressionCapTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile_service = PlayerProfileService()

    def test_calculate_player_tier_uses_finalized_block_thresholds(self) -> None:
        self.assertEqual(self.profile_service.calculate_player_tier(0), 1)
        self.assertEqual(self.profile_service.calculate_player_tier(4), 1)
        self.assertEqual(self.profile_service.calculate_player_tier(5), 2)
        self.assertEqual(self.profile_service.calculate_player_tier(19), 2)
        self.assertEqual(self.profile_service.calculate_player_tier(20), 3)

    def test_get_offline_cap_for_tier_scales_by_progression_tier(self) -> None:
        self.assertEqual(self.profile_service.get_offline_cap_for_tier(1), Decimal("1000"))
        self.assertEqual(self.profile_service.get_offline_cap_for_tier(2), Decimal("5000"))
        self.assertEqual(self.profile_service.get_offline_cap_for_tier(3), Decimal("10000"))
        self.assertEqual(self.profile_service.get_offline_cap_for_tier(4), Decimal("20000"))

    def test_simulate_offline_progress_caps_work_above_tier_limit(self) -> None:
        started_at = datetime(2026, 8, 18, 0, 0, tzinfo=UTC)
        ended_at = started_at + timedelta(minutes=2)

        result = MiningSimulationService.simulate_offline_progress(
            window_started_at=started_at,
            window_ended_at=ended_at,
            effective_hashrate_hps=Decimal("12"),
            cap_limit=Decimal("1000"),
            offline_cap_tier=1,
        )

        self.assertEqual(result.simulated_work, Decimal("1440.000000"))
        self.assertEqual(result.credited_work, Decimal("1000"))
        self.assertTrue(result.cap_applied)
        self.assertEqual(result.cap_amount, Decimal("440.000000"))
        self.assertEqual(result.offline_cap_tier, 1)

    def test_simulate_offline_progress_leaves_in_cap_work_uncapped(self) -> None:
        started_at = datetime(2026, 8, 18, 0, 0, tzinfo=UTC)
        ended_at = started_at + timedelta(seconds=30)

        result = MiningSimulationService.simulate_offline_progress(
            window_started_at=started_at,
            window_ended_at=ended_at,
            effective_hashrate_hps=Decimal("12"),
            cap_limit=Decimal("1000"),
            offline_cap_tier=1,
        )

        self.assertEqual(result.simulated_work, Decimal("360.000000"))
        self.assertEqual(result.credited_work, Decimal("360.000000"))
        self.assertFalse(result.cap_applied)
        self.assertEqual(result.cap_amount, Decimal("0.000000"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
