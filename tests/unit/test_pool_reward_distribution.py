from __future__ import annotations

import sys
import unittest
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.pools.service import PoolService


class PoolRewardDistributionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = PoolService()

    def test_distribution_is_deterministic_for_same_inputs(self) -> None:
        inputs = {
            "alpha": Decimal("10"),
            "beta": Decimal("20"),
            "gamma": Decimal("30"),
        }

        first = self.service.calculate_reward_shares(Decimal("120.000000"), Decimal("5"), inputs)
        second = self.service.calculate_reward_shares(Decimal("120.000000"), Decimal("5"), inputs)

        self.assertEqual(first, second)

    def test_rounding_preserves_full_reward_after_fee(self) -> None:
        owner_fee, shares = self.service.calculate_reward_shares(
            Decimal("1.000001"),
            Decimal("0"),
            {"alpha": Decimal("1"), "beta": Decimal("1")},
        )

        self.assertEqual(owner_fee, Decimal("0.000000"))
        self.assertEqual(sum((share.final_share for share in shares), Decimal("0")), Decimal("1.000001"))

    def test_remainder_bonus_is_given_to_lowest_member_id(self) -> None:
        owner_fee, shares = self.service.calculate_reward_shares(
            Decimal("1.000001"),
            Decimal("0"),
            {"beta": Decimal("1"), "alpha": Decimal("1")},
        )

        self.assertEqual(owner_fee, Decimal("0.000000"))
        self.assertEqual(shares[0].member_id, "alpha")
        self.assertEqual(shares[0].remainder_bonus, 1)
        self.assertEqual(shares[0].final_share, Decimal("0.500001"))
        self.assertEqual(shares[1].remainder_bonus, 0)
        self.assertEqual(shares[1].final_share, Decimal("0.500000"))

    def test_fee_deduction_is_applied_before_member_distribution(self) -> None:
        owner_fee, shares = self.service.calculate_reward_shares(
            Decimal("100.000000"),
            Decimal("7.5"),
            {"alpha": Decimal("3"), "beta": Decimal("1")},
        )

        self.assertEqual(owner_fee, Decimal("7.500000"))
        self.assertEqual(sum((share.final_share for share in shares), Decimal("0")), Decimal("92.500000"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
