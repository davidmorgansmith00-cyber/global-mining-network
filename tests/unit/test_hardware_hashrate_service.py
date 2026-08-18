from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.hardware.schemas import CoolingState, HardwareConfig, PowerState
from domain.hardware.service import GmnHardwareHashrateService


class GmnHardwareHashrateServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.service = GmnHardwareHashrateService()
        self.hardware = HardwareConfig(
            hardware_id="rig_alpha",
            base_hashrate=40.0,
            base_power_consumption=120.0,
            heat_generation=55.0,
        )

    def test_formula_multiplies_base_hashrate_by_power_and_cooling_modifiers(self) -> None:
        effective_hashrate = self.service.calculate_effective_hashrate(
            player_id="player_alpha",
            hardware_config=self.hardware,
            power_state=PowerState(power_consumed=90.0, power_capacity=120.0),
            cooling_state=CoolingState(cooling_efficiency=0.8),
        )

        self.assertEqual(effective_hashrate, 32.0)

    def test_power_throttle_curve_stays_full_under_capacity_and_floors_when_severely_over_capacity(self) -> None:
        under_capacity_multiplier = self.service.calculate_power_throttle_multiplier(90.0, 120.0)
        moderate_overdraw_multiplier = self.service.calculate_power_throttle_multiplier(180.0, 120.0)
        severe_overdraw_multiplier = self.service.calculate_power_throttle_multiplier(240.0, 120.0)

        self.assertEqual(under_capacity_multiplier, 1.0)
        self.assertAlmostEqual(moderate_overdraw_multiplier, 0.646447, places=6)
        self.assertEqual(severe_overdraw_multiplier, 0.1)

    def test_power_throttle_handles_zero_power_and_zero_capacity_edges(self) -> None:
        zero_power_multiplier = self.service.calculate_power_throttle_multiplier(0.0, 120.0)
        zero_capacity_multiplier = self.service.calculate_power_throttle_multiplier(120.0, 0.0)

        self.assertEqual(zero_power_multiplier, 1.0)
        self.assertEqual(zero_capacity_multiplier, 0.1)

    def test_cooling_multiplier_is_clamped_between_zero_and_one(self) -> None:
        zero_cooling_hashrate = self.service.calculate_effective_hashrate(
            player_id="player_alpha",
            hardware_config=self.hardware,
            power_state=PowerState(power_consumed=120.0, power_capacity=120.0),
            cooling_state=CoolingState(cooling_efficiency=-1.0),
        )
        capped_cooling_hashrate = self.service.calculate_effective_hashrate(
            player_id="player_alpha",
            hardware_config=self.hardware,
            power_state=PowerState(power_consumed=120.0, power_capacity=120.0),
            cooling_state=CoolingState(cooling_efficiency=1.7),
        )

        self.assertEqual(zero_cooling_hashrate, 0.0)
        self.assertEqual(capped_cooling_hashrate, 40.0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
