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
from domain.anticheat.service import ACTION_WARNING, AntiCheatService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "******localhost:5432/global_mining_network"


class AntiCheatApiIntegrationTests(unittest.TestCase):
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
                cursor.execute("DELETE FROM anti_cheat_events WHERE player_id = %s", (str(player_id),))
                cursor.execute("DELETE FROM anti_cheat_actions WHERE player_id = %s", (str(player_id),))
                cursor.execute("DELETE FROM auth_sessions WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM player_inventory WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = %s", (str(player_id),))
                cursor.execute("DELETE FROM player_profiles WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM players WHERE player_id = %s", (player_id,))
            connection.commit()

    def _register_player(self, client: TestClient, *, email: str) -> str:
        response = client.post("/api/v1/auth/register", json={"email": email, "password": "password123"})
        self.assertEqual(response.status_code, 200)
        return response.json()["player_id"]

    def test_check_endpoint_returns_monitor_for_new_player(self) -> None:
        email = f"anticheat_check_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id = self._register_player(client, email=email)
                response = client.get(f"/api/v1/anticheat/check/{player_id}")
                self.assertEqual(response.status_code, 200)
                payload = response.json()
                self.assertEqual(payload["player_id"], player_id)
                self.assertEqual(payload["total_score"], 0)
                self.assertEqual(payload["action"], "MONITOR")
                self.assertEqual(payload["reasons"], [])
        finally:
            self._cleanup_player_by_email(email=email)

    def test_actions_and_appeal_flow_is_auditable(self) -> None:
        email = f"anticheat_appeal_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id = self._register_player(client, email=email)
                action_id = AntiCheatService().enforce_action(
                    player_id=player_id,
                    action=ACTION_WARNING,
                    reason="integration_test_flag",
                    evidence={"total_score": 25, "signal": "test"},
                )

                actions_response = client.get(f"/api/v1/anticheat/actions/{player_id}")
                self.assertEqual(actions_response.status_code, 200)
                actions = actions_response.json()["actions"]
                self.assertEqual(len(actions), 1)
                self.assertEqual(actions[0]["action_id"], action_id)
                self.assertEqual(actions[0]["action_type"], ACTION_WARNING)
                self.assertIsNone(actions[0]["appeal_status"])

                appeal_response = client.post(
                    "/api/v1/anticheat/appeal",
                    json={
                        "player_id": player_id,
                        "action_id": action_id,
                        "appeal_reason": "false-positive-check",
                    },
                )
                self.assertEqual(appeal_response.status_code, 201)
                self.assertEqual(appeal_response.json()["status"], "pending")

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT appeal_status, evidence_json->>'appeal_reason'
                            FROM anti_cheat_actions
                            WHERE action_id = %s AND player_id = %s
                            """,
                            (UUID(action_id), player_id),
                        )
                        row = cursor.fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row[0], "pending")
                self.assertEqual(row[1], "false-positive-check")
        finally:
            self._cleanup_player_by_email(email=email)


if __name__ == "__main__":
    unittest.main(verbosity=2)
