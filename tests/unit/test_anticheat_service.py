from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.anticheat.service import (
    ACTION_MONITOR,
    ACTION_MUTE_24H,
    ACTION_SUSPEND,
    ACTION_WARNING,
    AntiCheatService,
)


class AntiCheatServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = AntiCheatService()

    @patch("domain.anticheat.service.database_is_configured", return_value=False)
    def test_noop_mode_returns_clean_result(self, _mock_database_configured: object) -> None:
        result = self.service.calculate_anomaly_score("player-id", "general", {})
        self.assertEqual(result.total_score, 0)
        self.assertEqual(result.action, ACTION_MONITOR)
        self.assertEqual(result.reasons, [])

    @patch("domain.anticheat.service.database_is_configured", return_value=True)
    @patch("domain.anticheat.service.open_connection")
    def test_score_calculation_combines_rate_state_and_wealth_signals(
        self,
        mock_open_connection: object,
        _mock_database_configured: object,
    ) -> None:
        cursor = mock_open_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [
            (25,),
            (120,),
            ("-1.000000",),
            ("10.000000",),
            ("60.000000",),
        ]

        result = self.service.calculate_anomaly_score("player-id", "purchase", {})

        self.assertEqual(result.rate_score, 80)
        self.assertEqual(result.state_score, 100)
        self.assertEqual(result.wealth_score, 40)
        self.assertEqual(result.total_score, 220)
        self.assertEqual(result.action, ACTION_SUSPEND)
        self.assertIn("negative_balance", result.reasons)
        self.assertTrue(any(reason.startswith("purchases_per_hour:") for reason in result.reasons))
        self.assertTrue(any(reason.startswith("wealth_spike:") for reason in result.reasons))

    def test_action_thresholds_match_policy(self) -> None:
        self.assertEqual(self.service.determine_action(0), ACTION_MONITOR)
        self.assertEqual(self.service.determine_action(20), ACTION_WARNING)
        self.assertEqual(self.service.determine_action(50), ACTION_MUTE_24H)
        self.assertEqual(self.service.determine_action(100), ACTION_SUSPEND)


if __name__ == "__main__":
    unittest.main(verbosity=2)
