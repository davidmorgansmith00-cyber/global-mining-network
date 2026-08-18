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

from domain.marketplace.service import PlayerMarketplaceService


class PlayerMarketplaceServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PlayerMarketplaceService()

    def test_list_equipment_rejects_non_positive_quantity(self) -> None:
        with self.assertRaises(ValueError):
            self.service.list_equipment("player", "hardware", 0, Decimal("1.000000"))

    def test_list_equipment_rejects_non_positive_price(self) -> None:
        with self.assertRaises(ValueError):
            self.service.list_equipment("player", "hardware", 1, Decimal("0"))

    @patch("domain.marketplace.service.database_is_configured", return_value=False)
    def test_database_noop_paths_return_defaults(self, _mock_database_configured: object) -> None:
        self.assertEqual(self.service.browse_listings(), [])
        self.assertIsNone(self.service.get_listing("listing-id"))
        self.assertEqual(
            self.service.purchase_equipment("buyer", "listing-id", 1).error,
            "database_unavailable",
        )
        reputation = self.service.get_player_reputation("player-id")
        self.assertEqual(reputation.successful_sales, 0)
        self.assertEqual(reputation.successful_purchases, 0)
        self.assertEqual(reputation.reputation_score, Decimal("0"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
