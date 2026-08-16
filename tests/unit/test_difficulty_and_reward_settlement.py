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

from domain.blockchain.store import FinalizedBlockRecord
from domain.difficulty.service import DifficultyAdjustmentService, DifficultyConfig
from domain.economy.reward_settlement import RewardSettlementConfig, RewardSettlementService


class DifficultyAndRewardSettlementTests(unittest.TestCase):
    def test_difficulty_increases_when_blocks_are_too_fast(self) -> None:
        service = DifficultyAdjustmentService(
            DifficultyConfig(
                target_block_seconds=10,
                history_window_size=5,
                max_upward_adjustment_pct=Decimal("0.20"),
                max_downward_adjustment_pct=Decimal("0.20"),
            )
        )
        started = datetime(2026, 8, 15, 18, 0, tzinfo=UTC)
        history = [
            FinalizedBlockRecord(1, Decimal("100"), Decimal("100"), started),
            FinalizedBlockRecord(2, Decimal("100"), Decimal("100"), started + timedelta(seconds=5)),
            FinalizedBlockRecord(3, Decimal("100"), Decimal("100"), started + timedelta(seconds=10)),
        ]

        next_required = service.compute_next_required_work(
            current_required_work=Decimal("100"),
            finalized_blocks=history,
        )
        self.assertEqual(next_required, Decimal("120.000000"))

    def test_difficulty_decreases_when_blocks_are_too_slow(self) -> None:
        service = DifficultyAdjustmentService(
            DifficultyConfig(
                target_block_seconds=10,
                history_window_size=5,
                max_upward_adjustment_pct=Decimal("0.20"),
                max_downward_adjustment_pct=Decimal("0.20"),
            )
        )
        started = datetime(2026, 8, 15, 18, 0, tzinfo=UTC)
        history = [
            FinalizedBlockRecord(1, Decimal("100"), Decimal("100"), started),
            FinalizedBlockRecord(2, Decimal("100"), Decimal("100"), started + timedelta(seconds=20)),
            FinalizedBlockRecord(3, Decimal("100"), Decimal("100"), started + timedelta(seconds=40)),
        ]

        next_required = service.compute_next_required_work(
            current_required_work=Decimal("100"),
            finalized_blocks=history,
        )
        self.assertEqual(next_required, Decimal("80.000000"))

    def test_reward_scales_with_required_work(self) -> None:
        service = RewardSettlementService(
            RewardSettlementConfig(
                base_block_reward=Decimal("100"),
                target_required_work=Decimal("100"),
            )
        )

        reward_low = service.compute_block_reward(required_work=Decimal("80"), total_work=Decimal("80"))
        reward_high = service.compute_block_reward(required_work=Decimal("120"), total_work=Decimal("120"))

        self.assertEqual(reward_low, Decimal("80.000000"))
        self.assertEqual(reward_high, Decimal("120.000000"))

    def test_player_reward_allocation_is_conservative(self) -> None:
        service = RewardSettlementService()
        allocation = service.allocate_player_rewards(
            total_reward=Decimal("100.000000"),
            contributions_by_player={
                "a": Decimal("5"),
                "b": Decimal("3"),
                "c": Decimal("2"),
            },
        )

        self.assertEqual(allocation["a"], Decimal("50.000000"))
        self.assertEqual(allocation["b"], Decimal("30.000000"))
        self.assertEqual(allocation["c"], Decimal("20.000000"))
        self.assertEqual(sum(allocation.values(), Decimal("0")), Decimal("100.000000"))


if __name__ == "__main__":
    unittest.main(verbosity=2)