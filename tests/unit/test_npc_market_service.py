from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch
from uuid import uuid4


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.market.service import NpcMarketService


class NpcMarketServiceUnitTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = NpcMarketService()

    def test_calculate_purchase_total_multiplies_unit_price_by_quantity(self) -> None:
        total = self.service.calculate_purchase_total("starter_gpu_rig_mk1", 2)
        self.assertEqual(total, Decimal("500.000000"))

    @patch("domain.market.service.database_is_configured", return_value=True)
    @patch.object(NpcMarketService, "_get_player_credit_balance", return_value=Decimal("100.000000"))
    @patch("domain.market.service.open_connection")
    def test_execute_purchase_returns_insufficient_balance_error(
        self,
        mock_open_connection: object,
        _mock_balance: object,
        _mock_db_configured: object,
    ) -> None:
        player_id = str(uuid4())
        connection = mock_open_connection.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(player_id, 1, "starter_rusty_home_computer")]

        result = self.service.execute_purchase(player_id, "starter_gpu_rig_mk1", 1)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "insufficient_balance")

    @patch("domain.market.service.database_is_configured", return_value=True)
    @patch.object(NpcMarketService, "_lock_and_get_stock", return_value=0)
    @patch.object(NpcMarketService, "_get_player_credit_balance", return_value=Decimal("1000.000000"))
    @patch("domain.market.service.open_connection")
    def test_execute_purchase_returns_out_of_stock_error(
        self,
        mock_open_connection: object,
        _mock_balance: object,
        _mock_stock: object,
        _mock_db_configured: object,
    ) -> None:
        player_id = str(uuid4())
        connection = mock_open_connection.return_value.__enter__.return_value
        cursor = connection.cursor.return_value.__enter__.return_value
        cursor.fetchone.side_effect = [(player_id, 1, "starter_rusty_home_computer")]

        result = self.service.execute_purchase(player_id, "starter_gpu_rig_mk1", 1)

        self.assertFalse(result.success)
        self.assertEqual(result.error, "out_of_stock")


if __name__ == "__main__":
    unittest.main(verbosity=2)
