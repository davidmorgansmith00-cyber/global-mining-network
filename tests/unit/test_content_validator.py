from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.content.validator import ContentValidator


VALID_CONTENT_PACK = {
    "hardware": [
        {
            "id": "starter_home_rig",
            "name": "Starter Home Rig",
            "tier": 1,
            "base_hashrate": 12.0,
            "power_consumption": 120.0,
            "heat_generation": 40.0,
            "cost": 0,
            "unlock_tier": 1,
        },
        {
            "id": "garage_mining_stack",
            "name": "Garage Mining Stack",
            "tier": 2,
            "base_hashrate": 28.0,
            "power_consumption": 180.0,
            "heat_generation": 80.0,
            "cost": 1800,
            "unlock_tier": 2,
            "unlock_research_id": "research_cooling_basics",
        },
    ],
    "buildings": [
        {
            "id": "starter_shed",
            "name": "Starter Shed",
            "tier": 1,
            "power_capacity": 200.0,
            "cooling_capacity": 120.0,
            "cost": 0,
            "unlock_tier": 1,
        },
        {
            "id": "garage_farm",
            "name": "Garage Farm",
            "tier": 2,
            "power_capacity": 420.0,
            "cooling_capacity": 240.0,
            "cost": 2400,
            "unlock_tier": 2,
            "unlock_research_id": "research_power_bus",
        },
    ],
    "research": [
        {
            "id": "research_cooling_basics",
            "name": "Cooling Basics",
            "unlock_condition": {"tier": 1},
            "unlock_time_seconds": 900,
            "effects": {"unlocks": ["garage_mining_stack"]},
        },
        {
            "id": "research_power_bus",
            "name": "Power Bus Retrofit",
            "unlock_condition": {"research_id": "research_cooling_basics"},
            "unlock_time_seconds": 1800,
            "effects": {"unlocks": ["garage_farm"]},
        },
    ],
    "recipes": [
        {
            "id": "shed_to_garage_conversion",
            "input_item_id": "starter_shed",
            "output_item_id": "garage_farm",
            "input_quantity": 1,
            "output_quantity": 1,
            "duration_seconds": 3600,
            "cost_credits": 750,
            "unlock_tier": 2,
            "unlock_research_id": "research_power_bus",
        }
    ],
    "events": [
        {
            "id": "starter_launch_weekend",
            "name": "Starter Launch Weekend",
            "start_timestamp": "2026-09-01T00:00:00Z",
            "end_timestamp": "2026-09-03T00:00:00Z",
            "modifier_type": "reward_multiplier",
            "modifier_value": 1.1,
            "affected_players": "all",
        }
    ],
}


class ContentValidatorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.validator = ContentValidator()

    def test_valid_content_pack_passes_schema_and_rule_checks(self) -> None:
        errors, warnings = self.validator.validate_content_pack(copy.deepcopy(VALID_CONTENT_PACK), "Baseline impact note.")

        self.assertEqual(errors, [])
        self.assertEqual(warnings, [])

    def test_validate_schema_reports_invalid_hardware_fields(self) -> None:
        invalid_hardware = copy.deepcopy(VALID_CONTENT_PACK["hardware"])
        invalid_hardware[0]["base_hashrate"] = -1

        errors = self.validator.validate_schema(invalid_hardware, self.validator.load_schema("hardware"))

        self.assertTrue(any("minimum of 0" in error.lower() or "greater than" in error.lower() for error in errors))

    def test_orphan_unlocks_detect_missing_research_dependency(self) -> None:
        content = copy.deepcopy(VALID_CONTENT_PACK)
        content["hardware"][1]["unlock_research_id"] = "missing_research"

        errors = self.validator.check_orphan_unlocks(content)

        self.assertEqual(
            errors,
            ["orphan unlock: hardware:garage_mining_stack references missing research missing_research"],
        )

    def test_circular_dependencies_detect_research_cycles(self) -> None:
        content = copy.deepcopy(VALID_CONTENT_PACK)
        content["research"][0]["unlock_condition"] = {"research_id": "research_power_bus"}

        errors = self.validator.check_circular_dependencies(content)

        self.assertEqual(
            errors,
            ["circular dependency: research_cooling_basics -> research_power_bus -> research_cooling_basics"],
        )

    def test_balance_sanity_flags_impossible_recipe_shapes(self) -> None:
        content = copy.deepcopy(VALID_CONTENT_PACK)
        content["recipes"][0]["output_quantity"] = 0
        content["recipes"][0]["output_item_id"] = "starter_shed"

        errors = self.validator.check_balance_sanity(content)

        self.assertIn(
            "impossible recipe: shed_to_garage_conversion has non-positive output quantity",
            errors,
        )
        self.assertIn(
            "impossible recipe: shed_to_garage_conversion produces the same item it consumes",
            errors,
        )

    def test_missing_impact_notes_returns_warning(self) -> None:
        warnings = self.validator.check_economy_impact(copy.deepcopy(VALID_CONTENT_PACK), "")

        self.assertEqual(warnings, ["missing economy impact notes"])


if __name__ == "__main__":
    unittest.main()
