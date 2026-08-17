from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from api.v1.blockchain import get_player_reward_balances
from domain.economy.read_models import PlayerRewardBalance


class BlockchainRewardBalancesApiTests(unittest.TestCase):
    @patch("api.v1.blockchain.project_player_reward_balances", return_value=[])
    def test_reward_balances_returns_zero_total_when_projection_is_empty(self, _mock_projection: object) -> None:
        response = get_player_reward_balances()
        self.assertEqual(response.total_reward_balance, Decimal("0"))
        self.assertEqual(response.entries, [])

    @patch("api.v1.blockchain.project_player_reward_balances")
    def test_reward_balances_sums_projected_entries_deterministically(self, mock_projection: object) -> None:
        mock_projection.return_value = [
            PlayerRewardBalance(player_id="player_a", reward_balance=Decimal("80.000000")),
            PlayerRewardBalance(player_id="player_b", reward_balance=Decimal("20.000000")),
        ]

        response = get_player_reward_balances()

        self.assertEqual(response.total_reward_balance, Decimal("100.000000"))
        self.assertEqual(len(response.entries), 2)
        self.assertEqual(response.entries[0].player_id, "player_a")
        self.assertEqual(response.entries[0].reward_balance, Decimal("80.000000"))
        self.assertEqual(response.entries[1].player_id, "player_b")
        self.assertEqual(response.entries[1].reward_balance, Decimal("20.000000"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
