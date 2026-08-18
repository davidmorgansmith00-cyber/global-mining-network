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

from domain.economy.read_models import project_player_reward_balances


class EconomyReadModelsTests(unittest.TestCase):
    @patch("domain.economy.read_models.database_is_configured", return_value=False)
    def test_reward_projection_returns_empty_when_database_not_configured(self, _mock_database_configured: object) -> None:
        projection = project_player_reward_balances()
        self.assertEqual(projection, [])

    @patch("domain.economy.read_models.database_is_configured", return_value=True)
    @patch("domain.economy.read_models.open_connection")
    def test_reward_projection_returns_player_balances_in_deterministic_order(
        self,
        mock_open_connection: object,
        _mock_database_configured: object,
    ) -> None:
        rows = [
            ("player_a", Decimal("80.000000")),
            ("player_b", Decimal("20.000000")),
        ]

        mock_cursor = mock_open_connection.return_value.__enter__.return_value.cursor.return_value.__enter__.return_value
        mock_cursor.fetchall.return_value = rows

        projection = project_player_reward_balances()

        self.assertEqual(len(projection), 2)
        self.assertEqual(projection[0].player_id, "player_a")
        self.assertEqual(projection[0].reward_balance, Decimal("80.000000"))
        self.assertEqual(projection[1].player_id, "player_b")
        self.assertEqual(projection[1].reward_balance, Decimal("20.000000"))
        executed_query = mock_cursor.execute.call_args.args[0]
        self.assertIn("block.finalized.player_reward.v1", executed_query)
        self.assertIn("market.purchase.v1", executed_query)


if __name__ == "__main__":
    unittest.main(verbosity=2)
