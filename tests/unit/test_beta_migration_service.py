from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.genesis.migration import BetaMigrationService


class BetaMigrationServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = BetaMigrationService(
            beta_profiles={
                "beta-1": {
                    "balance": Decimal("1000"),
                    "tier": 3,
                    "progress_to_next_tier": 0.4,
                    "inventory": [{"item_id": "cosmetic-a", "category": "cosmetic"}],
                    "blocks_mined": 20,
                    "total_rewards_earned": Decimal("3500"),
                }
            },
            production_profiles={},
        )

    def test_calculate_migration_loss_tax(self) -> None:
        self.assertEqual(self.service.calculate_migration_loss_tax(Decimal("1000")), Decimal("100.000000"))

    def test_migrate_beta_player_transfers_90_percent_balance(self) -> None:
        result = self.service.migrate_beta_player("beta-1", "prod-1")
        self.assertTrue(result["success"])
        self.assertEqual(result["transferred_balance"], "900.000000")
        self.assertEqual(result["loss_tax"], "100.000000")

    def test_verify_migration_data_rejects_duplicate_pair(self) -> None:
        self.service.migrate_beta_player("beta-1", "prod-1")
        verify = self.service.verify_migration_data("beta-1", "prod-1")
        self.assertFalse(verify["valid"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
