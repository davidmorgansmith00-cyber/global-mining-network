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
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/global_mining_network"


class AuthApiIntegrationTests(unittest.TestCase):
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

    def test_auth_endpoints_support_register_refresh_logout_lifecycle(self) -> None:
        email = f"auth_api_{uuid4().hex[:10]}@example.com"
        password = "password123"

        try:
            with TestClient(app) as client:
                registered = client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": password},
                )
                self.assertEqual(registered.status_code, 200)
                registered_payload = registered.json()
                self.assertEqual(UUID(registered_payload["player_id"]).version, 4)
                self.assertEqual(UUID(registered_payload["session_id"]).version, 4)
                self.assertTrue(registered_payload["access_token"].startswith("access_"))
                self.assertTrue(registered_payload["refresh_token"].startswith("refresh_"))

                refreshed = client.post(
                    "/api/v1/auth/refresh",
                    json={
                        "session_id": registered_payload["session_id"],
                        "refresh_token": registered_payload["refresh_token"],
                    },
                )
                self.assertEqual(refreshed.status_code, 200)
                refreshed_payload = refreshed.json()
                self.assertEqual(refreshed_payload["player_id"], registered_payload["player_id"])
                self.assertEqual(refreshed_payload["session_id"], registered_payload["session_id"])
                self.assertNotEqual(refreshed_payload["refresh_token"], registered_payload["refresh_token"])

                revoked = client.post(
                    "/api/v1/auth/logout",
                    json={
                        "session_id": registered_payload["session_id"],
                        "refresh_token": refreshed_payload["refresh_token"],
                    },
                )
                self.assertEqual(revoked.status_code, 200)
                revoked_payload = revoked.json()
                self.assertEqual(revoked_payload["session_id"], registered_payload["session_id"])
                self.assertTrue(revoked_payload["revoked"])

                refresh_after_logout = client.post(
                    "/api/v1/auth/refresh",
                    json={
                        "session_id": registered_payload["session_id"],
                        "refresh_token": refreshed_payload["refresh_token"],
                    },
                )
                self.assertEqual(refresh_after_logout.status_code, 401)
                self.assertEqual(refresh_after_logout.json()["detail"], "Invalid session")
        finally:
            self._cleanup_player_by_email(email=email)

    def test_auth_refresh_rejects_invalid_token(self) -> None:
        email = f"auth_invalid_{uuid4().hex[:10]}@example.com"
        password = "password123"

        try:
            with TestClient(app) as client:
                registered = client.post(
                    "/api/v1/auth/register",
                    json={"email": email, "password": password},
                )
                self.assertEqual(registered.status_code, 200)
                payload = registered.json()

                invalid_refresh = client.post(
                    "/api/v1/auth/refresh",
                    json={
                        "session_id": payload["session_id"],
                        "refresh_token": "refresh_invalid_token",
                    },
                )
                self.assertEqual(invalid_refresh.status_code, 401)
                self.assertEqual(invalid_refresh.json()["detail"], "Invalid session")
        finally:
            self._cleanup_player_by_email(email=email)


if __name__ == "__main__":
    unittest.main(verbosity=2)