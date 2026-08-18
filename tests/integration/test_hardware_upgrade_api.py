from __future__ import annotations

import os
import sys
import unittest
from decimal import Decimal
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
from domain.hardware.upgrade_service import HardwareUpgradeService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "******localhost:5432/global_mining_network"


class HardwareUpgradeIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def _cleanup_player(self, *, email: str) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT player_id FROM players WHERE email = %s", (email,))
                row = cur.fetchone()
                if row is None:
                    conn.commit()
                    return
                pid = row[0]
                cur.execute("DELETE FROM auth_sessions WHERE player_id = %s", (pid,))
                cur.execute("DELETE FROM player_inventory WHERE player_id = %s", (pid,))
                cur.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = %s", (str(pid),))
                cur.execute("DELETE FROM player_profiles WHERE player_id = %s", (pid,))
                cur.execute("DELETE FROM players WHERE player_id = %s", (pid,))
            conn.commit()

    def _seed_reward_balance(self, *, player_id: str, amount: Decimal) -> None:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO economy_player_ledger_entries (
                        ledger_entry_id, block_number, player_id, amount,
                        contribution_hashes, currency, entry_type, metadata
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, '{}'::jsonb)
                    """,
                    (uuid4(), 1, player_id, amount, Decimal("0"), "credits",
                     "block.finalized.player_reward.v1"),
                )
            conn.commit()

    def _register_and_get_player_id(self, *, client: TestClient, email: str) -> str:
        resp = client.post("/api/v1/auth/register", json={
            "email": email,
            "password": "Passw0rd!",
            "player_name": email.split("@")[0],
        })
        self.assertEqual(resp.status_code, 200)
        player_id = resp.json()["player_id"]
        # Ensure profile row is created by fetching profile once
        client.get("/api/v1/players/profile", params={"player_id": player_id})
        return player_id

    # ------------------------------------------------------------------
    # Upgrade service unit-level integration
    # ------------------------------------------------------------------

    def test_hardware_definitions_json_loads_three_or_more_tiers(self) -> None:
        service = HardwareUpgradeService()
        defs = service.get_all_tier_definitions()
        self.assertGreaterEqual(len(defs), 3)

    def test_tier1_starter_hardware_in_definitions(self) -> None:
        service = HardwareUpgradeService()
        tier1_def = service.get_definition("starter_rusty_home_computer")
        self.assertIsNotNone(tier1_def)
        assert tier1_def is not None
        self.assertEqual(tier1_def.tier, 1)
        self.assertEqual(tier1_def.market_price, Decimal("0"))

    def test_improved_workstation_in_definitions(self) -> None:
        service = HardwareUpgradeService()
        tier2_def = service.get_definition("improved_workstation")
        self.assertIsNotNone(tier2_def)
        assert tier2_def is not None
        self.assertEqual(tier2_def.tier, 2)
        self.assertGreater(tier2_def.market_price, Decimal("0"))
        self.assertGreater(tier2_def.base_hashrate, 12.0)

    def test_professional_mining_rig_in_definitions(self) -> None:
        service = HardwareUpgradeService()
        tier3_def = service.get_definition("professional_mining_rig")
        self.assertIsNotNone(tier3_def)
        assert tier3_def is not None
        self.assertEqual(tier3_def.tier, 3)
        self.assertIsNotNone(tier3_def.unlock_condition)

    # ------------------------------------------------------------------
    # Upgrade purchase flow
    # ------------------------------------------------------------------

    def test_hardware_upgrade_purchase_swaps_inventory_and_updates_hardware_id(self) -> None:
        email = f"hw_upgrade_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                resp = client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "improved_workstation",
                    "quantity": 1,
                })
                self.assertEqual(resp.status_code, 200)
                body = resp.json()
                self.assertTrue(body["success"])

                # Verify player hardware_id updated
                with psycopg.connect(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT hardware_id FROM players WHERE player_id = %s",
                            (UUID(player_id),),
                        )
                        row = cur.fetchone()
                self.assertIsNotNone(row)
                assert row is not None
                self.assertEqual(row[0], "improved_workstation")
        finally:
            self._cleanup_player(email=email)

    def test_hardware_upgrade_old_hardware_removed_from_inventory(self) -> None:
        email = f"hw_inv_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "improved_workstation",
                    "quantity": 1,
                })

                # new hardware in inventory
                with psycopg.connect(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT item_id FROM player_inventory WHERE player_id = %s ORDER BY item_id",
                            (UUID(player_id),),
                        )
                        rows = [r[0] for r in cur.fetchall()]

                self.assertIn("improved_workstation", rows)
                # old starter hardware removed
                self.assertNotIn("starter_rusty_home_computer", rows)
        finally:
            self._cleanup_player(email=email)

    def test_hardware_upgrade_ledger_entry_type_is_hardware_upgrade_v1(self) -> None:
        email = f"hw_ledger_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "improved_workstation",
                    "quantity": 1,
                })

                with psycopg.connect(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT entry_type, item_id, previous_item_id
                            FROM economy_player_ledger_entries
                            WHERE player_id = %s AND entry_type = 'hardware.upgrade.v1'
                            """,
                            (player_id,),
                        )
                        row = cur.fetchone()

                self.assertIsNotNone(row, "Expected a hardware.upgrade.v1 ledger entry")
                assert row is not None
                self.assertEqual(row[0], "hardware.upgrade.v1")
                self.assertEqual(row[1], "improved_workstation")
                self.assertIsNotNone(row[2], "previous_item_id should be set")
        finally:
            self._cleanup_player(email=email)

    def test_hardware_upgrade_recalculates_effective_hashrate(self) -> None:
        email = f"hw_hashrate_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                before = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(before.status_code, 200)
                before_hashrate = before.json()["effective_hashrate"]

                client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "improved_workstation",
                    "quantity": 1,
                })

                after = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(after.status_code, 200)
                after_hashrate = after.json()["effective_hashrate"]

                self.assertGreater(after_hashrate, before_hashrate)
        finally:
            self._cleanup_player(email=email)

    def test_profile_v16_shows_current_hardware_after_upgrade(self) -> None:
        email = f"hw_prof_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "improved_workstation",
                    "quantity": 1,
                })

                resp = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(resp.status_code, 200)
                payload = resp.json()

                self.assertEqual(payload["schema_version"], "player.profile.v1.6")
                self.assertIsNotNone(payload["current_hardware"])
                self.assertEqual(payload["current_hardware"]["hardware_id"], "improved_workstation")
                self.assertEqual(payload["current_hardware"]["tier"], 2)
        finally:
            self._cleanup_player(email=email)

    def test_profile_v16_shows_upgrade_progression(self) -> None:
        email = f"hw_prog_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)

                resp = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(resp.status_code, 200)
                payload = resp.json()

                progression = payload["upgrade_progression"]
                self.assertGreaterEqual(len(progression), 3)
                tiers = [e["tier"] for e in progression]
                self.assertEqual(tiers, sorted(tiers))
                current_entries = [e for e in progression if e["is_current"]]
                self.assertEqual(len(current_entries), 1)
        finally:
            self._cleanup_player(email=email)

    def test_profile_v16_shows_next_recommended_upgrade_for_tier1(self) -> None:
        email = f"hw_next_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)

                resp = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(resp.status_code, 200)
                payload = resp.json()

                rec = payload["next_recommended_upgrade"]
                self.assertIsNotNone(rec)
                assert rec is not None
                self.assertEqual(rec["tier"], 2)
                self.assertGreater(rec["cost"], 0)
                self.assertGreater(rec["eta_seconds"], 0)
                self.assertFalse(rec["unlock_blocked"])
        finally:
            self._cleanup_player(email=email)

    def test_tier3_upgrade_is_blocked_for_player_tier1(self) -> None:
        email = f"hw_tier3_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("20000"))

                resp = client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "professional_mining_rig",
                    "quantity": 1,
                })
                self.assertEqual(resp.status_code, 200)
                body = resp.json()
                self.assertFalse(body["success"])
                self.assertEqual(body["error"], "item_locked")
        finally:
            self._cleanup_player(email=email)

    def test_eta_is_zero_when_player_has_enough_balance(self) -> None:
        email = f"hw_eta_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                # Seed enough to afford tier 2
                service = HardwareUpgradeService()
                tier2_def = service.get_definition("improved_workstation")
                assert tier2_def is not None
                self._seed_reward_balance(player_id=player_id, amount=tier2_def.market_price)

                resp = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(resp.status_code, 200)
                payload = resp.json()

                rec = payload["next_recommended_upgrade"]
                self.assertIsNotNone(rec)
                assert rec is not None
                self.assertEqual(rec["eta_seconds"], 0)
        finally:
            self._cleanup_player(email=email)

    def test_full_tier1_to_tier2_upgrade_journey(self) -> None:
        """Tier 1 → Tier 2 end-to-end: purchase, inventory swap, hashrate increase, ledger."""
        email = f"hw_journey_{uuid4().hex[:8]}@example.com"
        self._cleanup_player(email=email)
        try:
            with TestClient(app) as client:
                player_id = self._register_and_get_player_id(client=client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                profile_before = client.get("/api/v1/players/profile", params={"player_id": player_id}).json()
                self.assertEqual(profile_before["hardware_id"], "starter_rusty_home_computer")
                self.assertIsNotNone(profile_before["next_recommended_upgrade"])

                purchase_resp = client.post("/api/v1/market/purchase", json={
                    "player_id": player_id,
                    "item_id": "improved_workstation",
                    "quantity": 1,
                })
                self.assertTrue(purchase_resp.json()["success"])

                profile_after = client.get("/api/v1/players/profile", params={"player_id": player_id}).json()
                self.assertEqual(profile_after["hardware_id"], "improved_workstation")
                self.assertEqual(profile_after["current_hardware"]["tier"], 2)
                self.assertGreater(profile_after["effective_hashrate"], profile_before["effective_hashrate"])
                self.assertEqual(profile_after["next_recommended_upgrade"]["tier"], 3)

                with psycopg.connect(self.database_url) as conn:
                    with conn.cursor() as cur:
                        cur.execute(
                            "SELECT COUNT(*) FROM economy_player_ledger_entries "
                            "WHERE player_id = %s AND entry_type = 'hardware.upgrade.v1'",
                            (player_id,),
                        )
                        count = cur.fetchone()[0]
                self.assertEqual(count, 1)
        finally:
            self._cleanup_player(email=email)


if __name__ == "__main__":
    unittest.main(verbosity=2)
