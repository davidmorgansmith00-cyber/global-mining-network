from __future__ import annotations

import sys
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.economy.analyzer import EconomyAnalyzer


class EconomyAnalyzerTests(unittest.TestCase):
    def setUp(self) -> None:
        now = datetime(2026, 8, 18, 12, 0, tzinfo=UTC)
        self.analyzer = EconomyAnalyzer(
            now_provider=lambda: now,
            player_tiers={"a": 1, "b": 2, "c": 3, "d": 2},
            player_last_active={
                "a": now - timedelta(days=1),
                "b": now - timedelta(days=9),
                "c": now - timedelta(days=10),
                "d": now - timedelta(days=2),
            },
            ledger_entries=[
                {
                    "player_id": "a",
                    "entry_type": "market.purchase.v1",
                    "amount": Decimal("-50"),
                    "currency": "credits",
                    "created_at": now - timedelta(hours=2),
                    "item_id": "skin1",
                    "quantity": 1,
                    "total_cost": Decimal("50"),
                },
                {
                    "player_id": "b",
                    "entry_type": "market.purchase.v1",
                    "amount": Decimal("-150"),
                    "currency": "credits",
                    "created_at": now - timedelta(hours=3),
                    "item_id": "skin1",
                    "quantity": 3,
                    "total_cost": Decimal("150"),
                },
                {
                    "player_id": "c",
                    "entry_type": "block.finalized.player_reward.v1",
                    "amount": Decimal("500"),
                    "currency": "credits",
                    "created_at": now - timedelta(hours=1),
                    "item_id": None,
                    "quantity": None,
                    "total_cost": None,
                },
                {
                    "player_id": "d",
                    "entry_type": "block.finalized.player_reward.v1",
                    "amount": Decimal("200"),
                    "currency": "credits",
                    "created_at": now - timedelta(days=1, hours=2),
                    "item_id": None,
                    "quantity": None,
                    "total_cost": None,
                },
            ],
        )

    def test_progression_distribution_returns_histogram_and_percentiles(self) -> None:
        result = self.analyzer.analyze_progression_distribution()
        self.assertEqual(result["histogram"]["tier_2"], 2)
        self.assertEqual(result["median_tier"], 2)
        self.assertEqual(result["total_players"], 4)

    def test_churn_rate_counts_inactive_players(self) -> None:
        churn = self.analyzer.calculate_churn_rate(days=7)
        self.assertEqual(churn["inactive_players"], 2)
        self.assertEqual(churn["total_players"], 4)

    def test_inflation_rate_uses_recent_window_deltas(self) -> None:
        inflation = self.analyzer.calculate_inflation_rate(days=1)
        self.assertIn("inflation_rate_percent", inflation)
        self.assertEqual(inflation["current_window_delta"], "300.000000")

    def test_price_trends_calculates_average_and_volatility(self) -> None:
        trends = self.analyzer.analyze_price_trends("skin1", days=30)
        self.assertEqual(trends["average_price"], "50.000000")
        self.assertEqual(trends["samples"], 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
