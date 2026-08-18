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
        # Heat within cooling capacity → cooling_multiplier = 1.0; power under capacity → 1.0
        # effective = 40 × 1.0 × 1.0 = 40
        effective_hashrate = self.service.calculate_effective_hashrate(
            player_id="player_alpha",
            hardware_config=self.hardware,
            power_state=PowerState(power_consumed=90.0, power_capacity=120.0),
            cooling_state=CoolingState(heat_generated=50.0, cooling_capacity=100.0),
        )

        self.assertEqual(effective_hashrate, 40.0)

    def test_formula_applies_cooling_penalty_when_heat_exceeds_capacity(self) -> None:
        # Heat=150, capacity=100 → excess_ratio=0.5; cubic_falloff=sqrt(0.5^3)=sqrt(0.125)≈0.353553
        # cooling_mult = max(0.1, 1.0 - 0.353553) ≈ 0.646447; power under capacity
        # effective = 40 × 0.646447 ≈ 25.857864
        effective_hashrate = self.service.calculate_effective_hashrate(
            player_id="player_alpha",
            hardware_config=self.hardware,
            power_state=PowerState(power_consumed=90.0, power_capacity=120.0),
            cooling_state=CoolingState(heat_generated=150.0, cooling_capacity=100.0),
        )

        self.assertAlmostEqual(effective_hashrate, 25.857864, places=6)

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

    def test_cooling_multiplier_is_one_when_heat_within_capacity(self) -> None:
        no_heat = self.service.calculate_cooling_efficiency_multiplier(0.0, 100.0)
        exactly_at_cap = self.service.calculate_cooling_efficiency_multiplier(100.0, 100.0)
        below_cap = self.service.calculate_cooling_efficiency_multiplier(50.0, 100.0)

        self.assertEqual(no_heat, 1.0)
        self.assertEqual(exactly_at_cap, 1.0)
        self.assertEqual(below_cap, 1.0)

    def test_cooling_multiplier_applies_cubic_falloff_above_capacity(self) -> None:
        # excess_ratio = (150-100)/100 = 0.5; falloff = sqrt(0.5^3) = sqrt(0.125) ≈ 0.353553
        moderate = self.service.calculate_cooling_efficiency_multiplier(150.0, 100.0)
        # excess_ratio = (300-100)/100 = 2.0; falloff = sqrt(8) ≈ 2.828 → clamped to 0.1
        severe = self.service.calculate_cooling_efficiency_multiplier(300.0, 100.0)

        self.assertAlmostEqual(moderate, 0.646447, places=6)
        self.assertEqual(severe, 0.1)

    def test_cooling_multiplier_floors_at_zero_capacity(self) -> None:
        result = self.service.calculate_cooling_efficiency_multiplier(50.0, 0.0)
        self.assertEqual(result, 0.1)

    def test_heat_generated_scales_with_power_consumption_ratio(self) -> None:
        # At full capacity → ratio=1.0; heat = 40 × 1.0 = 40
        full_load = self.service.calculate_heat_generated(40.0, 120.0, 120.0)
        # At half capacity → ratio=0.5; heat = 40 × 0.5 = 20
        half_load = self.service.calculate_heat_generated(40.0, 60.0, 120.0)
        # Zero power → 0
        no_load = self.service.calculate_heat_generated(40.0, 0.0, 120.0)

        self.assertAlmostEqual(full_load, 40.0, places=6)
        self.assertAlmostEqual(half_load, 20.0, places=6)
        self.assertAlmostEqual(no_load, 0.0, places=6)

    def test_heat_generated_caps_at_base_when_over_capacity(self) -> None:
        # power_consumed > power_capacity → ratio clamped to 1.0
        over_capacity = self.service.calculate_heat_generated(40.0, 200.0, 120.0)
        self.assertAlmostEqual(over_capacity, 40.0, places=6)

    def test_heat_generated_returns_base_when_capacity_is_zero(self) -> None:
        result = self.service.calculate_heat_generated(40.0, 120.0, 0.0)
        self.assertAlmostEqual(result, 40.0, places=6)


if __name__ == "__main__":
    unittest.main(verbosity=2)
