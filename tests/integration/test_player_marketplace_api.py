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
from domain.marketplace.service import PlayerMarketplaceService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "******localhost:5432/global_mining_network"
_PASS = "password123"


class PlayerMarketplaceApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()
        cls.marketplace_service = PlayerMarketplaceService()

    def _register_player(self, client: TestClient, *, email: str) -> str:
        response = client.post("/api/v1/auth/register", json={"email": email, "password": _PASS})
        self.assertEqual(response.status_code, 200)
        return response.json()["player_id"]

    def _seed_inventory(self, *, player_id: str, item_id: str, quantity: int) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO player_inventory (player_id, item_id, quantity, acquired_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (player_id, item_id)
                    DO UPDATE SET quantity = EXCLUDED.quantity, acquired_at = NOW()
                    """,
                    (UUID(player_id), item_id, quantity),
                )
            connection.commit()

    def _seed_credit_balance(self, *, player_id: str, amount: Decimal) -> None:
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

    def _cleanup_players(self, player_ids: list[str]) -> None:
        if not player_ids:
            return

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM player_reputation WHERE player_id = ANY(%s)", (player_ids,))
                cursor.execute(
                    """
                    DELETE FROM equipment_listings
                    WHERE seller_id = ANY(%s)
                    """,
                    (player_ids,),
                )
                cursor.execute("DELETE FROM auth_sessions WHERE player_id::text = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM player_inventory WHERE player_id::text = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM player_profiles WHERE player_id::text = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM players WHERE player_id::text = ANY(%s)", (player_ids,))
            connection.commit()

    def test_list_and_unlist_restores_inventory_and_marks_listing_unlisted(self) -> None:
        seller_email = f"pm_seller_unlist_{uuid4().hex[:10]}@example.com"
        created_players: list[str] = []
        try:
            with TestClient(app) as client:
                seller_id = self._register_player(client, email=seller_email)
                created_players.append(seller_id)
                self._seed_inventory(player_id=seller_id, item_id="starter_gpu_rig_mk1", quantity=4)

                listed = client.post(
                    "/api/v1/marketplace/list",
                    json={
                        "player_id": seller_id,
                        "hardware_id": "starter_gpu_rig_mk1",
                        "quantity": 3,
                        "price_per_unit": "10.000000",
                    },
                )
                self.assertEqual(listed.status_code, 201)
                listing_id = listed.json()["listing_id"]

                unlisted = client.delete(f"/api/v1/marketplace/listing/{listing_id}", params={"player_id": seller_id})
                self.assertEqual(unlisted.status_code, 200)

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT status, quantity_remaining FROM equipment_listings WHERE listing_id = %s",
                            (listing_id,),
                        )
                        listing_row = cursor.fetchone()
                        self.assertEqual(listing_row[0], "unlisted")
                        self.assertEqual(int(listing_row[1]), 3)

                        cursor.execute(
                            "SELECT quantity FROM player_inventory WHERE player_id = %s AND item_id = %s",
                            (UUID(seller_id), "starter_gpu_rig_mk1"),
                        )
                        inventory_row = cursor.fetchone()
                        self.assertEqual(int(inventory_row[0]), 4)
        finally:
            self._cleanup_players(created_players)

    def test_purchase_settlement_updates_listing_inventory_and_ledger(self) -> None:
        seller_email = f"pm_seller_purchase_{uuid4().hex[:10]}@example.com"
        buyer_email = f"pm_buyer_purchase_{uuid4().hex[:10]}@example.com"
        created_players: list[str] = []
        try:
            with TestClient(app) as client:
                seller_id = self._register_player(client, email=seller_email)
                buyer_id = self._register_player(client, email=buyer_email)
                created_players.extend([seller_id, buyer_id])

                self._seed_inventory(player_id=seller_id, item_id="starter_gpu_rig_mk1", quantity=3)
                self._seed_credit_balance(player_id=buyer_id, amount=Decimal("1000.000000"))

                listed = client.post(
                    "/api/v1/marketplace/list",
                    json={
                        "player_id": seller_id,
                        "hardware_id": "starter_gpu_rig_mk1",
                        "quantity": 2,
                        "price_per_unit": "100.000000",
                    },
                )
                self.assertEqual(listed.status_code, 201)
                listing_id = listed.json()["listing_id"]

                purchased = client.post(
                    "/api/v1/marketplace/purchase",
                    json={"buyer_id": buyer_id, "listing_id": listing_id, "quantity": 1},
                )
                self.assertEqual(purchased.status_code, 200)
                purchase_payload = purchased.json()
                self.assertEqual(purchase_payload["status"], "purchased")
                self.assertEqual(Decimal(purchase_payload["purchase_price"]), Decimal("100.000000"))
                self.assertEqual(Decimal(purchase_payload["marketplace_fee"]), Decimal("5.000000"))
                self.assertEqual(Decimal(purchase_payload["seller_proceeds"]), Decimal("95.000000"))

                listing_payload = client.get(f"/api/v1/marketplace/listing/{listing_id}")
                self.assertEqual(listing_payload.status_code, 200)
                self.assertEqual(listing_payload.json()["quantity_remaining"], 1)
                self.assertEqual(listing_payload.json()["status"], "active")

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            "SELECT quantity FROM player_inventory WHERE player_id = %s AND item_id = %s",
                            (UUID(seller_id), "starter_gpu_rig_mk1"),
                        )
                        seller_inventory = cursor.fetchone()
                        self.assertEqual(int(seller_inventory[0]), 1)

                        cursor.execute(
                            "SELECT quantity FROM player_inventory WHERE player_id = %s AND item_id = %s",
                            (UUID(buyer_id), "starter_gpu_rig_mk1"),
                        )
                        buyer_inventory = cursor.fetchone()
                        self.assertEqual(int(buyer_inventory[0]), 1)

                        cursor.execute(
                            """
                            SELECT player_id, amount, entry_type
                            FROM economy_player_ledger_entries
                            WHERE entry_type = 'player.equipment_trade.v1'
                              AND metadata->>'listing_id' = %s
                            ORDER BY amount ASC
                            """,
                            (listing_id,),
                        )
                        trade_rows = cursor.fetchall()
                        self.assertEqual(len(trade_rows), 2)
                        self.assertEqual(trade_rows[0][0], buyer_id)
                        self.assertEqual(Decimal(str(trade_rows[0][1])), Decimal("-100.000000"))
                        self.assertEqual(trade_rows[1][0], seller_id)
                        self.assertEqual(Decimal(str(trade_rows[1][1])), Decimal("95.000000"))
        finally:
            self._cleanup_players(created_players)

    def test_concurrent_purchase_requests_do_not_double_sell_single_unit(self) -> None:
        seller_email = f"pm_seller_race_{uuid4().hex[:10]}@example.com"
        buyer_a_email = f"pm_buyer_race_a_{uuid4().hex[:10]}@example.com"
        buyer_b_email = f"pm_buyer_race_b_{uuid4().hex[:10]}@example.com"
        created_players: list[str] = []
        try:
            with TestClient(app) as client:
                seller_id = self._register_player(client, email=seller_email)
                buyer_a = self._register_player(client, email=buyer_a_email)
                buyer_b = self._register_player(client, email=buyer_b_email)
                created_players.extend([seller_id, buyer_a, buyer_b])

                self._seed_inventory(player_id=seller_id, item_id="starter_gpu_rig_mk1", quantity=1)
                self._seed_credit_balance(player_id=buyer_a, amount=Decimal("500.000000"))
                self._seed_credit_balance(player_id=buyer_b, amount=Decimal("500.000000"))

                listed = client.post(
                    "/api/v1/marketplace/list",
                    json={
                        "player_id": seller_id,
                        "hardware_id": "starter_gpu_rig_mk1",
                        "quantity": 1,
                        "price_per_unit": "100.000000",
                    },
                )
                self.assertEqual(listed.status_code, 201)
                listing_id = listed.json()["listing_id"]

            with ThreadPoolExecutor(max_workers=2) as executor:
                first = executor.submit(self.marketplace_service.purchase_equipment, buyer_a, listing_id, 1)
                second = executor.submit(self.marketplace_service.purchase_equipment, buyer_b, listing_id, 1)
                first_result = first.result()
                second_result = second.result()

            results = [first_result, second_result]
            success_count = len([result for result in results if result.success])
            failure_count = len([result for result in results if not result.success])
            self.assertEqual(success_count, 1)
            self.assertEqual(failure_count, 1)

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COALESCE(SUM(quantity), 0)
                        FROM player_inventory
                        WHERE item_id = %s
                          AND player_id IN (%s, %s)
                        """,
                        ("starter_gpu_rig_mk1", UUID(buyer_a), UUID(buyer_b)),
                    )
                    buyer_total = cursor.fetchone()
                    self.assertEqual(int(buyer_total[0]), 1)
        finally:
            self._cleanup_players(created_players)


if __name__ == "__main__":
    unittest.main(verbosity=2)
