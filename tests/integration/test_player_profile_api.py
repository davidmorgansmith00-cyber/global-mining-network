from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.main import app
from domain.players.service import PlayerProfileService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "******localhost:5432/global_mining_network"


class PlayerProfileApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def _cleanup_player_by_email(self, *, email: str) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT player_id FROM players WHERE email = %s", (email,))
                row = cursor.fetchone()
                if row is None:
                    connection.commit()
                    return
                player_id = row[0]

                cursor.execute("DELETE FROM auth_sessions WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM player_profiles WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM players WHERE player_id = %s", (player_id,))
            connection.commit()

    def test_profile_endpoint_returns_v13_cooling_constraint_contract(self) -> None:
        email = f"profile_contract_{uuid4().hex[:10]}@example.com"
        password = "password123"

        try:
            with TestClient(app) as client:
                registered = client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": password},
                )
                self.assertEqual(registered.status_code, 200)
                player_id = registered.json()["player_id"]

                response = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(response.status_code, 200)

                payload = response.json()
                self.assertEqual(payload["schema_version"], "player.profile.v1.3")
                self.assertEqual(payload["player_id"], player_id)
                self.assertEqual(payload["hardware_id"], "starter_rusty_home_computer")
                self.assertEqual(payload["base_hashrate"], 12.0)
                self.assertEqual(payload["power_available"], 0.0)
                self.assertEqual(payload["power_consumed"], 120.0)
                self.assertEqual(payload["power_capacity"], 120.0)
                self.assertEqual(payload["power_throttle_multiplier"], 1.0)
                # Default cooling_capacity=100; starter heat=40 (at full power), so no penalty
                self.assertGreaterEqual(payload["cooling_capacity"], 0.0)
                self.assertEqual(payload["cooling_efficiency_multiplier"], 1.0)
                self.assertIsNotNone(payload["last_heat_dissipation_at"])
                self.assertEqual(payload["effective_hashrate"], 12.0)
                self.assertEqual(
                    set(payload.keys()),
                    {
                        "schema_version",
                        "player_id",
                        "hardware_id",
                        "base_hashrate",
                        "power_available",
                        "power_consumed",
                        "power_capacity",
                        "power_throttle_multiplier",
                        "heat_generated",
                        "cooling_capacity",
                        "cooling_efficiency_multiplier",
                        "last_heat_dissipation_at",
                        "effective_hashrate",
                    },
                )
        finally:
            self._cleanup_player_by_email(email=email)

    def test_hardware_change_updates_power_and_heat_and_applies_throttle_on_next_profile_poll(self) -> None:
        email = f"profile_recalc_{uuid4().hex[:10]}@example.com"
        password = "password123"

        try:
            with TestClient(app) as client:
                registered = client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": password},
                )
                self.assertEqual(registered.status_code, 200)
                player_id = registered.json()["player_id"]

                # Upgrade hardware + give enough power capacity → no power throttle
                # cooling_capacity set high so no cooling throttle either
                upgraded_profile = PlayerProfileService().assign_hardware_state(
                    player_id=player_id,
                    hardware_id="starter_improved_home_computer",
                    power_capacity=240.0,
                    cooling_capacity=200.0,
                )
                self.assertEqual(upgraded_profile.power_available, 60.0)
                self.assertEqual(upgraded_profile.power_consumed, 180.0)
                self.assertEqual(upgraded_profile.power_throttle_multiplier, 1.0)
                self.assertEqual(upgraded_profile.cooling_efficiency_multiplier, 1.0)
                self.assertEqual(upgraded_profile.effective_hashrate, 24.0)

                # Reduce power_capacity so power throttle kicks in;
                # keep cooling_capacity high to isolate power-throttle effect
                updated_profile = PlayerProfileService().assign_hardware_state(
                    player_id=player_id,
                    power_capacity=120.0,
                    cooling_capacity=200.0,
                )
                self.assertAlmostEqual(updated_profile.power_throttle_multiplier, 0.646447, places=6)
                self.assertEqual(updated_profile.power_available, 0.0)
                self.assertEqual(updated_profile.power_consumed, 180.0)
                self.assertEqual(updated_profile.cooling_efficiency_multiplier, 1.0)
                self.assertAlmostEqual(updated_profile.effective_hashrate, 15.514719, places=4)

                response = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["hardware_id"], "starter_improved_home_computer")
                self.assertEqual(payload["base_hashrate"], 24.0)
                self.assertEqual(payload["power_available"], 0.0)
                self.assertEqual(payload["power_consumed"], 180.0)
                self.assertEqual(payload["power_capacity"], 120.0)
                self.assertAlmostEqual(payload["power_throttle_multiplier"], 0.646447, places=6)
                self.assertEqual(payload["cooling_efficiency_multiplier"], 1.0)
                self.assertAlmostEqual(payload["effective_hashrate"], 15.514719, places=4)

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT
                                hardware_id,
                                power_consumed,
                                power_capacity,
                                power_throttle_multiplier_cached,
                                heat_generated,
                                cooling_capacity,
                                cooling_efficiency_multiplier_cached,
                                last_heat_dissipation_at,
                                effective_hashrate_cached,
                                effective_hashrate_updated_at
                            FROM players
                            WHERE player_id = %s
                            """,
                            (UUID(player_id),),
                        )
                        row = cursor.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "starter_improved_home_computer")
                self.assertEqual(float(row[1]), 180.0)
                self.assertEqual(float(row[2]), 120.0)
                self.assertAlmostEqual(float(row[3]), 0.646447, places=6)
                self.assertGreaterEqual(float(row[4]), 0.0)   # heat_generated
                self.assertEqual(float(row[5]), 200.0)        # cooling_capacity
                self.assertAlmostEqual(float(row[6]), 1.0, places=4)  # cooling multiplier
                self.assertIsNotNone(row[7])                  # last_heat_dissipation_at
                self.assertAlmostEqual(float(row[8]), 15.514719, places=4)
                self.assertIsNotNone(row[9])
        finally:
            self._cleanup_player_by_email(email=email)

    def test_cooling_throttle_applies_when_heat_exceeds_cooling_capacity(self) -> None:
        email = f"cooling_throttle_{uuid4().hex[:10]}@example.com"
        password = "password123"

        try:
            with TestClient(app) as client:
                registered = client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": password},
                )
                self.assertEqual(registered.status_code, 200)
                player_id = registered.json()["player_id"]

                # Set cooling_capacity very low so heat always exceeds it
                overcooled_profile = PlayerProfileService().assign_hardware_state(
                    player_id=player_id,
                    power_capacity=240.0,
                    cooling_capacity=1.0,  # almost no cooling → severe penalty
                )
                # cooling_efficiency_multiplier must be < 1.0
                self.assertLess(overcooled_profile.cooling_efficiency_multiplier, 1.0)
                # effective_hashrate must be less than base (12.0)
                self.assertLess(overcooled_profile.effective_hashrate, 12.0)
                self.assertGreaterEqual(overcooled_profile.cooling_efficiency_multiplier, 0.1)
        finally:
            self._cleanup_player_by_email(email=email)

    def test_profile_openapi_contract_lists_v13_hashrate_fields(self) -> None:
        openapi = app.openapi()
        operation = openapi["paths"]["/api/v1/players/profile"]["get"]
        self.assertEqual(operation["summary"], "Get Player Profile")

        response_schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
        self.assertEqual(response_schema["$ref"], "#/components/schemas/PlayerProfileResponse")

        profile_schema = openapi["components"]["schemas"]["PlayerProfileResponse"]
        for field_name in (
            "schema_version",
            "player_id",
            "hardware_id",
            "base_hashrate",
            "power_available",
            "power_consumed",
            "power_capacity",
            "power_throttle_multiplier",
            "heat_generated",
            "cooling_capacity",
            "cooling_efficiency_multiplier",
            "last_heat_dissipation_at",
            "effective_hashrate",
        ):
            self.assertIn(field_name, profile_schema["properties"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
