from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.economy.experiment import EconomyExperimentService


class EconomyExperimentServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime(2026, 8, 18, 13, 0, tzinfo=UTC)
        self.metrics = {
            "p1": {"balance": 1000, "tier": 2, "churned": False, "spending": 100},
            "p2": {"balance": 900, "tier": 2, "churned": False, "spending": 80},
            "p3": {"balance": 400, "tier": 1, "churned": True, "spending": 20},
            "p4": {"balance": 450, "tier": 1, "churned": True, "spending": 30},
        }
        self.service = EconomyExperimentService(
            metrics_provider=lambda player_id: self.metrics[player_id],
            now_provider=lambda: now,
        )
        self.experiment_id = self.service.create_experiment(
            "reward-test",
            {"reward_per_work_unit": "0.12"},
            {"reward_per_work_unit": "0.08"},
            duration_days=7,
        )

    def test_cohort_assignment_is_deterministic(self) -> None:
        first = self.service.assign_player_to_cohort("p1", self.experiment_id)
        second = self.service.assign_player_to_cohort("p1", self.experiment_id)
        self.assertEqual(first, second)

    def test_get_player_parameters_applies_experiment_override(self) -> None:
        cohort = self.service.assign_player_to_cohort("p2", self.experiment_id)
        params = self.service.get_player_parameters("p2")
        expected = "0.12" if cohort == "a" else "0.08"
        self.assertEqual(str(params["reward_per_work_unit"]), expected)

    def test_analyze_experiment_results_returns_stats_and_p_value(self) -> None:
        for player_id in self.metrics:
            self.service.assign_player_to_cohort(player_id, self.experiment_id)

        result = self.service.analyze_experiment_results(self.experiment_id)
        self.assertIn("cohort_a", result)
        self.assertIn("cohort_b", result)
        self.assertIn("p_value", result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
