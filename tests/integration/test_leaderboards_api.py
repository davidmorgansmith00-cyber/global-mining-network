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
from tools.apply_migrations import apply_migrations


_PG_USER = os.getenv("PGUSER", "postgres")
_PG_PASSWORD = os.getenv("PGPASSWORD", "postgres")
_PG_HOST = os.getenv("PGHOST", "localhost")
_PG_PORT = os.getenv("PGPORT", "5432")
_PG_DATABASE = os.getenv("PGDATABASE", "global_mining_network")
DEFAULT_DATABASE_URL = f"postgresql://{_PG_USER}:{_PG_PASSWORD}@{_PG_HOST}:{_PG_PORT}/{_PG_DATABASE}"
_PASS = "password123"


class LeaderboardsApiIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def _register_player(self, client: TestClient, *, email: str) -> str:
        response = client.post("/api/v1/auth/register", json={"email": email, "password": _PASS})
        self.assertEqual(response.status_code, 200)
        return response.json()["player_id"]

    def _seed_hashrate(self, *, player_id: str, hashrate: Decimal) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE players
                    SET effective_hashrate_cached = %s
                    WHERE player_id = %s
                    """,
                    (hashrate.quantize(Decimal("0.000001")), UUID(player_id)),
                )
            connection.commit()

    def _seed_ledger_entry(self, *, player_id: str, amount: Decimal, entry_type: str, block_number: int = 1) -> None:
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
                        block_number,
                        player_id,
                        amount.quantize(Decimal("0.000001")),
                        Decimal("1.000000"),
                        "credits",
                        entry_type,
                    ),
                )
            connection.commit()

    def _seed_pool_with_members(self, *, pool_id: str, owner_id: str, member_ids: list[str]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO mining_pools (pool_id, owner_id, pool_name, description, fee_percentage, status)
                    VALUES (%s, %s, %s, %s, %s, 'active')
                    """,
                    (UUID(pool_id), owner_id, "Integration Pool", "test", Decimal("2.50")),
                )
                for member_id in member_ids:
                    cursor.execute(
                        """
                        INSERT INTO pool_members (pool_id, player_id)
                        VALUES (%s, %s)
                        ON CONFLICT (pool_id, player_id) DO UPDATE SET left_at = NULL
                        """,
                        (UUID(pool_id), member_id),
                    )
            connection.commit()

    def _cleanup(self, *, player_ids: list[str], pool_ids: list[str]) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                if pool_ids:
                    pool_uuid_values = [UUID(pool_id) for pool_id in pool_ids]
                    cursor.execute("DELETE FROM pool_members WHERE pool_id = ANY(%s)", (pool_uuid_values,))
                    cursor.execute("DELETE FROM mining_pools WHERE pool_id = ANY(%s)", (pool_uuid_values,))

                if player_ids:
                    player_uuids = [UUID(player_id) for player_id in player_ids]
                    cursor.execute("DELETE FROM auth_sessions WHERE player_id = ANY(%s)", (player_uuids,))
                    cursor.execute("DELETE FROM leaderboard_visibility WHERE player_id = ANY(%s)", (player_ids,))
                    cursor.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = ANY(%s)", (player_ids,))
                    cursor.execute("DELETE FROM player_profiles WHERE player_id = ANY(%s)", (player_uuids,))
                    cursor.execute("DELETE FROM players WHERE player_id = ANY(%s)", (player_uuids,))
            connection.commit()

    def test_leaderboards_refresh_and_visibility_follow_authoritative_state(self) -> None:
        created_players: list[str] = []
        created_pools: list[str] = []
        try:
            with TestClient(app) as client:
                alpha_id = self._register_player(client, email=f"lb_alpha_{uuid4().hex[:10]}@example.com")
                beta_id = self._register_player(client, email=f"lb_beta_{uuid4().hex[:10]}@example.com")
                created_players.extend([alpha_id, beta_id])

                self._seed_hashrate(player_id=alpha_id, hashrate=Decimal("999999.000000"))
                self._seed_hashrate(player_id=beta_id, hashrate=Decimal("888888.000000"))

                self._seed_ledger_entry(
                    player_id=alpha_id, amount=Decimal("100.000000"), entry_type="block.finalized.player_reward.v1"
                )
                self._seed_ledger_entry(player_id=alpha_id, amount=Decimal("-25.000000"), entry_type="market.purchase.v1")
                self._seed_ledger_entry(
                    player_id=beta_id, amount=Decimal("50.000000"), entry_type="block.finalized.player_reward.v1"
                )
                self._seed_ledger_entry(
                    player_id=beta_id, amount=Decimal("5.000000"), entry_type="pool.reward_distribution.v1"
                )

                pool_id = str(uuid4())
                created_pools.append(pool_id)
                self._seed_pool_with_members(pool_id=pool_id, owner_id=alpha_id, member_ids=[alpha_id, beta_id])

                hashrate_payload = client.get("/api/v1/leaderboards/hashrate")
                self.assertEqual(hashrate_payload.status_code, 200)
                hashrate_rows = {row["player_id"]: row for row in hashrate_payload.json()["leaderboard"]}
                self.assertIn(alpha_id, hashrate_rows)
                self.assertIn(beta_id, hashrate_rows)
                self.assertLess(hashrate_rows[alpha_id]["rank"], hashrate_rows[beta_id]["rank"])

                weekly_payload = client.get("/api/v1/leaderboards/weekly-earnings")
                self.assertEqual(weekly_payload.status_code, 200)
                weekly_rows = {row["player_id"]: row for row in weekly_payload.json()["leaderboard"]}
                self.assertEqual(weekly_rows[alpha_id]["earnings_7d"], "100.000000")
                self.assertEqual(weekly_rows[beta_id]["earnings_7d"], "55.000000")

                wealth_payload = client.get("/api/v1/leaderboards/wealth")
                self.assertEqual(wealth_payload.status_code, 200)
                wealth_rows = {row["player_id"]: row for row in wealth_payload.json()["leaderboard"]}
                self.assertEqual(wealth_rows[alpha_id]["total_wealth"], "75.000000")
                self.assertEqual(wealth_rows[beta_id]["total_wealth"], "55.000000")

                pools_payload = client.get("/api/v1/leaderboards/pools")
                self.assertEqual(pools_payload.status_code, 200)
                pool_row = next((row for row in pools_payload.json()["leaderboard"] if row["pool_id"] == pool_id), None)
                self.assertIsNotNone(pool_row)
                self.assertEqual(pool_row["member_count"], 2)
                self.assertEqual(pool_row["total_hashrate"], "1888887.000000")

                position_payload = client.get(f"/api/v1/players/{beta_id}/leaderboard-position")
                self.assertEqual(position_payload.status_code, 200)
                self.assertEqual(position_payload.json()["hashrate_rank"], hashrate_rows[beta_id]["rank"])

                hidden_response = client.post("/api/v1/players/leaderboard-visibility", json={"player_id": alpha_id})
                self.assertEqual(hidden_response.status_code, 200)
                self.assertTrue(hidden_response.json()["is_hidden"])

                hidden_hashrate_payload = client.get("/api/v1/leaderboards/hashrate")
                self.assertEqual(hidden_hashrate_payload.status_code, 200)
                hidden_ids = {row["player_id"] for row in hidden_hashrate_payload.json()["leaderboard"]}
                self.assertNotIn(alpha_id, hidden_ids)
                self.assertIn(beta_id, hidden_ids)
        finally:
            self._cleanup(player_ids=created_players, pool_ids=created_pools)


if __name__ == "__main__":
    unittest.main(verbosity=2)
