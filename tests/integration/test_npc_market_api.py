from __future__ import annotations

import os
import sys
import unittest
from concurrent.futures import ThreadPoolExecutor
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
from domain.market.service import NpcMarketService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "******localhost:5432/global_mining_network"


class NpcMarketApiIntegrationTests(unittest.TestCase):
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
                cursor.execute("DELETE FROM player_inventory WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = %s", (str(player_id),))
                cursor.execute("DELETE FROM player_profiles WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM players WHERE player_id = %s", (player_id,))
            connection.commit()

    def _reset_market_inventory_state(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM npc_market_inventory_state")
            connection.commit()

    def _seed_reward_balance(self, *, player_id: str, amount: Decimal) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO economy_player_ledger_entries (
                        ledger_entry_id,
                        block_number,
                        player_id,
                        amount,
                        contribution_hashes,
                        currency,
                        entry_type,
                        metadata
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, '{}'::jsonb)
                    """,
                    (
                        uuid4(),
                        1,
                        player_id,
                        amount.quantize(Decimal("0.000001")),
                        Decimal("1.000000"),
                        "credits",
                        "block.finalized.player_reward.v1",
                    ),
                )
            connection.commit()

    def _register_player(self, client: TestClient, *, email: str) -> tuple[str, str]:
        response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        return payload["player_id"], payload["session_id"]

    def test_market_catalog_and_status_expose_catalog_items(self) -> None:
        with TestClient(app) as client:
            catalog = client.get("/api/v1/market/catalog")
            self.assertEqual(catalog.status_code, 200)
            catalog_payload = catalog.json()
            self.assertEqual(catalog_payload["schema_version"], "market.catalog.v1")
            self.assertGreaterEqual(len(catalog_payload["items"]), 2)

            status_payload = client.get("/api/v1/blockchain/status").json()
            self.assertIn("market_catalog", status_payload)
            self.assertGreaterEqual(len(status_payload["market_catalog"]), 2)

    def test_purchase_success_is_atomic_and_updates_inventory_and_ledger(self) -> None:
        email = f"market_success_{uuid4().hex[:10]}@example.com"
        self._reset_market_inventory_state()
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_player(client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("1000"))

                purchase = client.post(
                    "/api/v1/market/purchase",
                    params={"session_id": session_id},
                    json={"item_id": "starter_gpu_rig_mk1", "quantity": 2},
                )
                self.assertEqual(purchase.status_code, 200)
                payload = purchase.json()
                self.assertTrue(payload["success"])
                self.assertEqual(payload["receipt"]["item_id"], "starter_gpu_rig_mk1")
                self.assertEqual(payload["receipt"]["quantity"], 2)
                self.assertEqual(Decimal(payload["receipt"]["unit_price"]), Decimal("250.000000"))
                self.assertEqual(Decimal(payload["receipt"]["total_cost"]), Decimal("500.000000"))
                self.assertEqual(Decimal(payload["new_balance"]), Decimal("500.000000"))

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT quantity FROM player_inventory WHERE player_id = %s AND item_id = %s",
                            (UUID(player_id), "starter_gpu_rig_mk1"),
                        )
                        inventory_row = cursor.fetchone()
                        self.assertEqual(inventory_row[0], 2)
                        cursor.execute(
                            """
                            SELECT entry_type, item_id, quantity, unit_price, total_cost, amount
                            FROM economy_player_ledger_entries
                            WHERE player_id = %s
                              AND entry_type = 'market.purchase.v1'
                            ORDER BY created_at DESC
                            LIMIT 1
                            """,
                            (player_id,),
                        )
                        ledger_row = cursor.fetchone()
                        self.assertEqual(ledger_row[0], "market.purchase.v1")
                        self.assertEqual(ledger_row[1], "starter_gpu_rig_mk1")
                        self.assertEqual(ledger_row[2], 2)
                        self.assertEqual(ledger_row[3], Decimal("250.000000"))
                        self.assertEqual(ledger_row[4], Decimal("500.000000"))
                        self.assertEqual(ledger_row[5], Decimal("-500.000000"))
        finally:
            self._cleanup_player_by_email(email=email)
            self._reset_market_inventory_state()

    def test_purchase_fails_with_insufficient_balance(self) -> None:
        email = f"market_balance_{uuid4().hex[:10]}@example.com"
        self._reset_market_inventory_state()
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_player(client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("100"))

                purchase = client.post(
                    "/api/v1/market/purchase",
                    params={"session_id": session_id},
                    json={"item_id": "starter_gpu_rig_mk1", "quantity": 1},
                )
                self.assertEqual(purchase.status_code, 200)
                payload = purchase.json()
                self.assertFalse(payload["success"])
                self.assertEqual(payload["error"], "insufficient_balance")
        finally:
            self._cleanup_player_by_email(email=email)
            self._reset_market_inventory_state()

    def test_purchase_fails_when_item_out_of_stock(self) -> None:
        email = f"market_stock_{uuid4().hex[:10]}@example.com"
        self._reset_market_inventory_state()
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_player(client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("5000"))

                purchase = client.post(
                    "/api/v1/market/purchase",
                    params={"session_id": session_id},
                    json={"item_id": "starter_gpu_rig_mk1", "quantity": 6},
                )
                self.assertEqual(purchase.status_code, 200)
                payload = purchase.json()
                self.assertFalse(payload["success"])
                self.assertEqual(payload["error"], "out_of_stock")
        finally:
            self._cleanup_player_by_email(email=email)
            self._reset_market_inventory_state()

    def test_concurrent_purchases_do_not_double_sell_limited_stock(self) -> None:
        service = NpcMarketService()
        email_a = f"market_conc_a_{uuid4().hex[:10]}@example.com"
        email_b = f"market_conc_b_{uuid4().hex[:10]}@example.com"
        self._reset_market_inventory_state()
        try:
            with TestClient(app) as client:
                player_a, _session_a = self._register_player(client, email=email_a)
                player_b, _session_b = self._register_player(client, email=email_b)
                self._seed_reward_balance(player_id=player_a, amount=Decimal("1000"))
                self._seed_reward_balance(player_id=player_b, amount=Decimal("1000"))

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO npc_market_inventory_state (item_id, current_stock, last_restocked_at, updated_at)
                        VALUES (%s, %s, NOW(), NOW())
                        ON CONFLICT (item_id)
                        DO UPDATE SET current_stock = EXCLUDED.current_stock, updated_at = NOW()
                        """,
                        ("starter_gpu_rig_mk1", 1),
                    )
                connection.commit()

            with ThreadPoolExecutor(max_workers=2) as executor:
                first_future = executor.submit(service.execute_purchase, player_a, "starter_gpu_rig_mk1", 1)
                second_future = executor.submit(service.execute_purchase, player_b, "starter_gpu_rig_mk1", 1)
                first_result = first_future.result()
                second_result = second_future.result()

            results = [first_result, second_result]
            success_count = len([result for result in results if result.success])
            out_of_stock_count = len([result for result in results if result.error == "out_of_stock"])
            self.assertEqual(success_count, 1)
            self.assertEqual(out_of_stock_count, 1)
        finally:
            self._cleanup_player_by_email(email=email_a)
            self._cleanup_player_by_email(email=email_b)
            self._reset_market_inventory_state()

    def test_profile_v15_shows_inventory_and_affordable_market_items(self) -> None:
        email = f"market_profile_{uuid4().hex[:10]}@example.com"
        self._reset_market_inventory_state()
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_player(client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("1500"))
                purchase = client.post(
                    "/api/v1/market/purchase",
                    params={"session_id": session_id},
                    json={"item_id": "starter_gpu_rig_mk1", "quantity": 1},
                )
                self.assertEqual(purchase.status_code, 200)
                self.assertTrue(purchase.json()["success"])

                profile = client.get("/api/v1/players/profile", params={"player_id": player_id})
                self.assertEqual(profile.status_code, 200)
                payload = profile.json()
                self.assertEqual(payload["schema_version"], "player.profile.v1.5")
                self.assertGreaterEqual(len(payload["inventory"]), 1)
                self.assertEqual(payload["inventory"][0]["item_id"], "starter_gpu_rig_mk1")
                self.assertGreaterEqual(len(payload["available_for_purchase"]), 1)
        finally:
            self._cleanup_player_by_email(email=email)
            self._reset_market_inventory_state()

    def test_purchase_ledger_replay_matches_inventory_projection(self) -> None:
        email = f"market_replay_{uuid4().hex[:10]}@example.com"
        self._reset_market_inventory_state()
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_player(client, email=email)
                self._seed_reward_balance(player_id=player_id, amount=Decimal("2000"))
                for item_id, quantity in (("starter_gpu_rig_mk1", 2), ("upgraded_cooler_v2", 1)):
                    purchase = client.post(
                        "/api/v1/market/purchase",
                        params={"session_id": session_id},
                        json={"item_id": item_id, "quantity": quantity},
                    )
                    self.assertEqual(purchase.status_code, 200)
                    self.assertTrue(purchase.json()["success"])

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT item_id, quantity
                            FROM player_inventory
                            WHERE player_id = %s
                            ORDER BY item_id
                            """,
                            (UUID(player_id),),
                        )
                        inventory_rows = cursor.fetchall()
                        cursor.execute(
                            """
                            SELECT item_id, SUM(quantity)
                            FROM economy_player_ledger_entries
                            WHERE player_id = %s
                              AND entry_type = 'market.purchase.v1'
                            GROUP BY item_id
                            ORDER BY item_id
                            """,
                            (player_id,),
                        )
                        replay_rows = cursor.fetchall()
                self.assertEqual(inventory_rows, replay_rows)
        finally:
            self._cleanup_player_by_email(email=email)
            self._reset_market_inventory_state()


if __name__ == "__main__":
    unittest.main(verbosity=2)
