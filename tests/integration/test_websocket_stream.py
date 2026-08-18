from __future__ import annotations

import json
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

_PASS = "password123"


class WebSocketStreamIntegrationTests(unittest.TestCase):
    """End-to-end integration tests for the /players/stream WebSocket endpoint.

    Requires a running Postgres database (see docker-compose.yml).
    """

    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def _register_and_login(self, *, client: TestClient, email: str) -> tuple[str, str]:
        """Register a player and return (player_id, session_id)."""
        reg = client.post(
            "/api/v1/auth/register",
            json={"email": email, "password": _PASS},
        )
        self.assertEqual(reg.status_code, 200, reg.text)
        player_id: str = reg.json()["player_id"]

        login = client.post(
            "/api/v1/auth/login",
            json={"email": email, "password": _PASS},
        )
        self.assertEqual(login.status_code, 200, login.text)
        session_id: str = login.json()["session_id"]
        return player_id, session_id

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
                cursor.execute(
                    "DELETE FROM economy_player_ledger_entries WHERE player_id = %s",
                    (str(player_id),),
                )
                cursor.execute("DELETE FROM player_profiles WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM players WHERE player_id = %s", (player_id,))
            connection.commit()

    # ------------------------------------------------------------------
    # Happy-path: connect + receive full state
    # ------------------------------------------------------------------

    def test_connect_returns_full_state_on_first_message(self) -> None:
        email = f"ws_stream_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)
                with client.websocket_connect(
                    f"/api/v1/players/stream/{player_id}?session_id={session_id}"
                ) as ws:
                    msg = json.loads(ws.receive_text())
                    self.assertEqual(msg["type"], "full_state")
                    self.assertEqual(msg["player_id"], player_id)
                    state = msg["state"]
                    for field in (
                        "effective_hashrate",
                        "power_consumed",
                        "player_tier",
                        "hardware_id",
                    ):
                        self.assertIn(field, state)
        finally:
            self._cleanup_player_by_email(email=email)

    def test_full_state_hardware_id_matches_starter(self) -> None:
        email = f"ws_hw_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)
                with client.websocket_connect(
                    f"/api/v1/players/stream/{player_id}?session_id={session_id}"
                ) as ws:
                    msg = json.loads(ws.receive_text())
                    self.assertEqual(msg["state"]["hardware_id"], "starter_rusty_home_computer")
        finally:
            self._cleanup_player_by_email(email=email)

    def test_full_state_player_tier_is_one_for_new_player(self) -> None:
        email = f"ws_tier_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)
                with client.websocket_connect(
                    f"/api/v1/players/stream/{player_id}?session_id={session_id}"
                ) as ws:
                    msg = json.loads(ws.receive_text())
                    self.assertEqual(msg["state"]["player_tier"], 1)
        finally:
            self._cleanup_player_by_email(email=email)

    # ------------------------------------------------------------------
    # Authentication failures
    # ------------------------------------------------------------------

    def test_invalid_session_id_rejects_connection(self) -> None:
        email = f"ws_auth_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, _ = self._register_and_login(client=client, email=email)
                with self.assertRaises(Exception):
                    with client.websocket_connect(
                        f"/api/v1/players/stream/{player_id}?session_id=not-a-uuid"
                    ) as ws:
                        ws.receive_text()
        finally:
            self._cleanup_player_by_email(email=email)

    def test_mismatched_player_id_rejects_connection(self) -> None:
        email = f"ws_mismatch_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)
                wrong_player_id = str(uuid4())
                with self.assertRaises(Exception):
                    with client.websocket_connect(
                        f"/api/v1/players/stream/{wrong_player_id}?session_id={session_id}"
                    ) as ws:
                        ws.receive_text()
        finally:
            self._cleanup_player_by_email(email=email)

    # ------------------------------------------------------------------
    # Subscription filtering
    # ------------------------------------------------------------------

    def test_subscribe_command_accepted_without_disconnect(self) -> None:
        email = f"ws_sub_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)
                with client.websocket_connect(
                    f"/api/v1/players/stream/{player_id}?session_id={session_id}"
                ) as ws:
                    # Consume initial full_state
                    ws.receive_text()
                    # Send subscribe command — should not raise or disconnect
                    ws.send_text(
                        json.dumps(
                            {
                                "action": "subscribe",
                                "subscriptions": ["hashrate_updates", "balance_updates"],
                            }
                        )
                    )
        finally:
            self._cleanup_player_by_email(email=email)

    def test_unsubscribe_command_accepted_without_disconnect(self) -> None:
        email = f"ws_unsub_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)
                with client.websocket_connect(
                    f"/api/v1/players/stream/{player_id}?session_id={session_id}"
                ) as ws:
                    ws.receive_text()
                    ws.send_text(
                        json.dumps(
                            {
                                "action": "unsubscribe",
                                "subscriptions": ["market_updates"],
                            }
                        )
                    )
        finally:
            self._cleanup_player_by_email(email=email)

    # ------------------------------------------------------------------
    # Schema consistency with REST profile
    # ------------------------------------------------------------------

    def test_full_state_fields_consistent_with_rest_profile(self) -> None:
        """Key fields sent via WebSocket should match the REST player profile."""
        email = f"ws_schema_{uuid4().hex[:10]}@example.com"
        try:
            with TestClient(app) as client:
                player_id, session_id = self._register_and_login(client=client, email=email)

                # Fetch REST profile
                profile_resp = client.get(f"/api/v1/players/profile?player_id={player_id}")
                self.assertEqual(profile_resp.status_code, 200)
                rest = profile_resp.json()

                with client.websocket_connect(
                    f"/api/v1/players/stream/{player_id}?session_id={session_id}"
                ) as ws:
                    ws_msg = json.loads(ws.receive_text())
                    ws_state = ws_msg["state"]

                self.assertEqual(ws_state["player_tier"], rest["player_tier"])
                self.assertAlmostEqual(
                    ws_state["effective_hashrate"],
                    rest["effective_hashrate"],
                    places=2,
                )
                self.assertEqual(ws_state["hardware_id"], rest["hardware_id"])
        finally:
            self._cleanup_player_by_email(email=email)


if __name__ == "__main__":
    unittest.main(verbosity=2)
