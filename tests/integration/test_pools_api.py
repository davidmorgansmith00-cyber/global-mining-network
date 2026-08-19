from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from uuid import uuid4

import psycopg
from fastapi.testclient import TestClient


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.main import app
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "******localhost:5432/global_mining_network"


class PoolsApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def _register_player(self, client: TestClient, *, email: str) -> str:
        response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
        self.assertEqual(response.status_code, 200)
        return response.json()["player_id"]

    def _cleanup_players(self, player_ids: list[str]) -> None:
        if not player_ids:
            return

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    DELETE FROM pool_members
                    WHERE player_id = ANY(%s)
                       OR pool_id IN (
                           SELECT pool_id
                           FROM mining_pools
                           WHERE owner_id = ANY(%s)
                       )
                    """,
                    (player_ids, player_ids),
                )
                cursor.execute(
                    "DELETE FROM mining_pools WHERE owner_id = ANY(%s)",
                    (player_ids,),
                )
                cursor.execute("DELETE FROM auth_sessions WHERE player_id::text = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM player_inventory WHERE player_id::text = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM player_profiles WHERE player_id::text = ANY(%s)", (player_ids,))
                cursor.execute("DELETE FROM players WHERE player_id::text = ANY(%s)", (player_ids,))
            connection.commit()

    def test_create_pool_auto_adds_owner_and_join_leave_membership_flow(self) -> None:
        owner_email = f"pools_owner_auto_{uuid4().hex[:10]}@example.com"
        member_email = f"pools_member_auto_{uuid4().hex[:10]}@example.com"
        created_players: list[str] = []
        try:
            with TestClient(app) as client:
                owner_id = self._register_player(client, email=owner_email)
                member_id = self._register_player(client, email=member_email)
                created_players.extend([owner_id, member_id])

                created = client.post(
                    "/api/v1/pools/create",
                    json={
                        "owner_id": owner_id,
                        "pool_name": "North Grid",
                        "description": "Baseline pool",
                        "fee_percentage": "5",
                    },
                )
                self.assertEqual(created.status_code, 201)
                pool_id = created.json()["pool_id"]

                pool_state = client.get(f"/api/v1/pools/{pool_id}")
                self.assertEqual(pool_state.status_code, 200)
                state_payload = pool_state.json()
                self.assertEqual(state_payload["member_count"], 1)
                self.assertEqual(state_payload["members"][0]["player_id"], owner_id)

                joined = client.post(f"/api/v1/pools/join/{pool_id}", json={"player_id": member_id})
                self.assertEqual(joined.status_code, 200)

                pool_state = client.get(f"/api/v1/pools/{pool_id}")
                self.assertEqual(pool_state.status_code, 200)
                state_payload = pool_state.json()
                self.assertEqual(state_payload["member_count"], 2)
                self.assertEqual(
                    {member["player_id"] for member in state_payload["members"]},
                    {owner_id, member_id},
                )

                left = client.post("/api/v1/pools/leave", json={"player_id": member_id, "pool_id": pool_id})
                self.assertEqual(left.status_code, 200)
                self.assertEqual(left.json()["accumulated_reward"], "0.000000")
        finally:
            self._cleanup_players(created_players)

    def test_joining_second_active_pool_returns_error(self) -> None:
        owner_a_email = f"pools_owner_a_{uuid4().hex[:10]}@example.com"
        owner_b_email = f"pools_owner_b_{uuid4().hex[:10]}@example.com"
        member_email = f"pools_member_b_{uuid4().hex[:10]}@example.com"
        created_players: list[str] = []
        try:
            with TestClient(app) as client:
                owner_a = self._register_player(client, email=owner_a_email)
                owner_b = self._register_player(client, email=owner_b_email)
                member_id = self._register_player(client, email=member_email)
                created_players.extend([owner_a, owner_b, member_id])

                pool_a = client.post(
                    "/api/v1/pools/create",
                    json={
                        "owner_id": owner_a,
                        "pool_name": "Pool A",
                        "description": "",
                        "fee_percentage": "3",
                    },
                )
                self.assertEqual(pool_a.status_code, 201)
                pool_a_id = pool_a.json()["pool_id"]

                pool_b = client.post(
                    "/api/v1/pools/create",
                    json={
                        "owner_id": owner_b,
                        "pool_name": "Pool B",
                        "description": "",
                        "fee_percentage": "4",
                    },
                )
                self.assertEqual(pool_b.status_code, 201)
                pool_b_id = pool_b.json()["pool_id"]

                joined = client.post(f"/api/v1/pools/join/{pool_a_id}", json={"player_id": member_id})
                self.assertEqual(joined.status_code, 200)

                second_join = client.post(f"/api/v1/pools/join/{pool_b_id}", json={"player_id": member_id})
                self.assertEqual(second_join.status_code, 400)
                self.assertEqual(second_join.json()["detail"], "already_in_another_pool")
        finally:
            self._cleanup_players(created_players)

    def test_dissolved_pool_rejects_new_joins(self) -> None:
        owner_email = f"pools_owner_close_{uuid4().hex[:10]}@example.com"
        member_email = f"pools_member_close_{uuid4().hex[:10]}@example.com"
        created_players: list[str] = []
        try:
            with TestClient(app) as client:
                owner_id = self._register_player(client, email=owner_email)
                member_id = self._register_player(client, email=member_email)
                created_players.extend([owner_id, member_id])

                created = client.post(
                    "/api/v1/pools/create",
                    json={
                        "owner_id": owner_id,
                        "pool_name": "Closing Pool",
                        "description": "",
                        "fee_percentage": "0",
                    },
                )
                self.assertEqual(created.status_code, 201)
                pool_id = created.json()["pool_id"]

                dissolved = client.post(f"/api/v1/pools/{pool_id}/dissolve", json={"owner_id": owner_id})
                self.assertEqual(dissolved.status_code, 200)

                join_after_dissolve = client.post(f"/api/v1/pools/join/{pool_id}", json={"player_id": member_id})
                self.assertEqual(join_after_dissolve.status_code, 400)
                self.assertEqual(join_after_dissolve.json()["detail"], "pool_not_active")
        finally:
            self._cleanup_players(created_players)


if __name__ == "__main__":
    unittest.main(verbosity=2)
