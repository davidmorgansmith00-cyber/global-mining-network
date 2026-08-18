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

from domain.leaderboards.service import LeaderboardService


class LeaderboardServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = LeaderboardService()

    @patch("domain.leaderboards.service.database_is_configured", return_value=False)
    def test_noop_mode_returns_empty_leaderboards(self, _mock_database_configured: object) -> None:
        self.assertEqual(self.service.get_hashrate_leaderboard(), [])
        self.assertEqual(self.service.get_pool_leaderboard(), [])
        self.assertEqual(self.service.get_weekly_earnings_leaderboard(), [])
        self.assertEqual(self.service.get_wealth_leaderboard(), [])

    @patch("domain.leaderboards.service.database_is_configured", return_value=False)
    def test_player_position_returns_none_ranks_without_database(self, _mock_database_configured: object) -> None:
        position = self.service.get_player_leaderboard_position("player-id")
        self.assertIsNone(position.hashrate_rank)
        self.assertIsNone(position.weekly_earnings_rank)
        self.assertIsNone(position.wealth_rank)
        self.assertEqual(position.total_players, 0)
        self.assertIsNone(position.percentile)


if __name__ == "__main__":
    unittest.main(verbosity=2)
