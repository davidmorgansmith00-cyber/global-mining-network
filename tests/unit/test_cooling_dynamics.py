from __future__ import annotations

import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.players.service import PlayerProfileService


class PassiveHeatDissipationTests(unittest.TestCase):
    """Unit tests for the passive heat dissipation helper (no DB required)."""

    def _dissipate(
        self,
        heat: float,
        rate: float,
        elapsed_minutes: float,
    ) -> float:
        now = datetime.now(tz=timezone.utc)
        last_at = now - timedelta(minutes=elapsed_minutes)
        return PlayerProfileService._apply_passive_dissipation(
            heat_generated=heat,
            dissipation_rate_per_minute=rate,
            last_dissipation_at=last_at,
        )

    def test_heat_unchanged_when_rate_is_zero(self) -> None:
        result = self._dissipate(heat=80.0, rate=0.0, elapsed_minutes=60.0)
        self.assertAlmostEqual(result, 80.0, places=6)

    def test_heat_unchanged_when_already_zero(self) -> None:
        result = self._dissipate(heat=0.0, rate=0.05, elapsed_minutes=60.0)
        self.assertEqual(result, 0.0)

    def test_heat_unchanged_when_no_dissipation_timestamp(self) -> None:
        result = PlayerProfileService._apply_passive_dissipation(
            heat_generated=50.0,
            dissipation_rate_per_minute=0.05,
            last_dissipation_at=None,
        )
        self.assertAlmostEqual(result, 50.0, places=6)

    def test_heat_decays_exponentially_over_one_minute(self) -> None:
        # 5% per minute: heat_after = 80 × 0.95^1 = 76
        result = self._dissipate(heat=80.0, rate=0.05, elapsed_minutes=1.0)
        self.assertAlmostEqual(result, 76.0, places=4)

    def test_heat_decays_over_multiple_minutes(self) -> None:
        # 5% per minute over 10 minutes: 80 × 0.95^10 ≈ 47.747...
        result = self._dissipate(heat=80.0, rate=0.05, elapsed_minutes=10.0)
        expected = 80.0 * (0.95 ** 10)
        self.assertAlmostEqual(result, expected, places=4)

    def test_heat_never_goes_negative(self) -> None:
        # Extreme dissipation rate over very long time
        result = self._dissipate(heat=10.0, rate=0.99, elapsed_minutes=1000.0)
        self.assertGreaterEqual(result, 0.0)

    def test_heat_unchanged_when_elapsed_time_is_zero(self) -> None:
        now = datetime.now(tz=timezone.utc)
        result = PlayerProfileService._apply_passive_dissipation(
            heat_generated=50.0,
            dissipation_rate_per_minute=0.05,
            last_dissipation_at=now,
        )
        # Elapsed ≈ 0 seconds → negligible decay
        self.assertAlmostEqual(result, 50.0, places=2)

    def test_naive_datetime_treated_as_utc(self) -> None:
        naive_ts = datetime.now(tz=timezone.utc).replace(tzinfo=None) - timedelta(minutes=1.0)
        result = PlayerProfileService._apply_passive_dissipation(
            heat_generated=80.0,
            dissipation_rate_per_minute=0.05,
            last_dissipation_at=naive_ts,
        )
        # Should decay by ~5% over ~1 minute
        self.assertAlmostEqual(result, 76.0, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
