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

from domain.mining.contracts import EVENT_OPERATION_PAUSE, SCHEMA_VERSION_V1, SimulationBoundaryEvent
from domain.mining.interval_slicer import IntervalBoundaryState, slice_progression_intervals


class MiningIntervalSlicerTests(unittest.TestCase):
    def test_piecewise_boundaries_split_intervals_and_apply_modifiers(self) -> None:
        start = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
        end = start + timedelta(minutes=20)

        slices = slice_progression_intervals(
            window_started_at=start,
            window_ended_at=end,
            base_hashrate_hps=Decimal("10"),
            boundary_states=[
                IntervalBoundaryState(occurred_at=start + timedelta(minutes=5), hashrate_multiplier=Decimal("2")),
                IntervalBoundaryState(
                    occurred_at=start + timedelta(minutes=12),
                    hashrate_multiplier=Decimal("2"),
                    paused=True,
                ),
                IntervalBoundaryState(occurred_at=start + timedelta(minutes=17), hashrate_multiplier=Decimal("1.5")),
            ],
        )

        self.assertEqual(len(slices), 4)

        self.assertEqual(slices[0].elapsed_seconds, 300)
        self.assertEqual(slices[0].effective_hashrate_hps, Decimal("10.000000"))
        self.assertEqual(slices[0].contribution_hashes, Decimal("3000.000000"))

        self.assertEqual(slices[1].elapsed_seconds, 420)
        self.assertEqual(slices[1].effective_hashrate_hps, Decimal("20.000000"))
        self.assertEqual(slices[1].contribution_hashes, Decimal("8400.000000"))

        self.assertEqual(slices[2].elapsed_seconds, 300)
        self.assertEqual(slices[2].effective_hashrate_hps, Decimal("0.000000"))
        self.assertEqual(slices[2].contribution_hashes, Decimal("0.000000"))

        self.assertEqual(slices[3].elapsed_seconds, 180)
        self.assertEqual(slices[3].effective_hashrate_hps, Decimal("15.000000"))
        self.assertEqual(slices[3].contribution_hashes, Decimal("2700.000000"))

    def test_deterministic_replay_returns_identical_slices(self) -> None:
        start = datetime(2026, 8, 15, 12, 0, tzinfo=UTC)
        end = start + timedelta(minutes=10)
        boundaries = [
            IntervalBoundaryState(occurred_at=start + timedelta(minutes=3), hashrate_multiplier=Decimal("1.2")),
            IntervalBoundaryState(occurred_at=start + timedelta(minutes=7), hashrate_multiplier=Decimal("0.8")),
        ]

        first_run = slice_progression_intervals(
            window_started_at=start,
            window_ended_at=end,
            base_hashrate_hps=Decimal("11"),
            boundary_states=boundaries,
        )
        second_run = slice_progression_intervals(
            window_started_at=start,
            window_ended_at=end,
            base_hashrate_hps=Decimal("11"),
            boundary_states=boundaries,
        )

        self.assertEqual(first_run, second_run)
        self.assertEqual(sum(item.elapsed_seconds for item in first_run), 600)

    def test_boundary_event_contract_defaults_to_v1_schema(self) -> None:
        event = SimulationBoundaryEvent(
            event_type=EVENT_OPERATION_PAUSE,
            player_id="player_123",
            operation_id="starter_operation",
            payload={"reason": "manual_pause"},
        )

        self.assertEqual(event.schema_version, SCHEMA_VERSION_V1)
        self.assertEqual(event.event_type, EVENT_OPERATION_PAUSE)
        self.assertEqual(event.player_id, "player_123")
        self.assertEqual(event.operation_id, "starter_operation")


if __name__ == "__main__":
    unittest.main(verbosity=2)