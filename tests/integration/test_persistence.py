from __future__ import annotations

import os
import sys
import time
import unittest
from pathlib import Path
from uuid import UUID, uuid4

import psycopg


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.auth.schemas import LoginRequest, RegisterRequest
from domain.auth.service import AuthService
from domain.players.service import PlayerBootstrapService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/global_mining_network"


class PersistenceFlowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        cls._wait_for_database(cls.database_url)
        apply_migrations()

    @staticmethod
    def _wait_for_database(database_url: str, timeout_seconds: int = 20) -> None:
        deadline = time.time() + timeout_seconds
        last_error: Exception | None = None
        while time.time() < deadline:
            try:
                with psycopg.connect(database_url):
                    return
            except Exception as exc:  # pragma: no cover - wait/retry path
                last_error = exc
                time.sleep(0.5)
        raise RuntimeError(f"Database did not become ready: {last_error}")

    def test_migrations_create_required_tables(self) -> None:
        required_tables = [
            "players",
            "auth_sessions",
            "domain_events",
            "player_profiles",
            "blockchain_active_block",
            "blockchain_finalized_blocks",
            "economy_ledger_entries",
            "economy_player_ledger_entries",
            "difficulty_settings",
            "network_events",
            "client_event_checkpoints",
            "maintenance_cleanup_rate_limit_state",
        ]
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                for table_name in required_tables:
                    cursor.execute("SELECT to_regclass(%s)", (table_name,))
                    resolved_table = cursor.fetchone()[0]
                    self.assertEqual(resolved_table, table_name)

                cursor.execute(
                    """
                    SELECT column_name
                    FROM information_schema.columns
                    WHERE table_name = 'economy_player_ledger_entries'
                      AND column_name = 'contribution_hashes'
                    """
                )
                contribution_column = cursor.fetchone()
                self.assertIsNotNone(contribution_column)

    def test_db_backed_register_login_bootstrap(self) -> None:
        unique_email = f"persist_{uuid4().hex[:10]}@example.com"

        auth = AuthService()
        registered = auth.register(RegisterRequest(email=unique_email, password="password123"))
        player_id = UUID(registered.player_id)

        self.assertTrue(registered.access_token.startswith("access_"))
        self.assertTrue(registered.refresh_token.startswith("refresh_"))

        logged_in = auth.login(LoginRequest(email=unique_email, password="password123"))
        self.assertEqual(logged_in.player_id, registered.player_id)

        bootstrapped = PlayerBootstrapService().bootstrap(player_id=registered.player_id)
        self.assertEqual(bootstrapped.player_id, registered.player_id)
        self.assertEqual(bootstrapped.starter_machine.hardware_id, "starter_rusty_home_computer")
        self.assertEqual(bootstrapped.starter_machine.hashrate_hps, 12)

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM auth_sessions WHERE player_id = %s", (player_id,))
                session_count = cursor.fetchone()[0]
                self.assertGreaterEqual(session_count, 2)

                cursor.execute(
                    "SELECT starter_hardware_id, starter_hashrate_hps FROM player_profiles WHERE player_id = %s",
                    (player_id,),
                )
                profile_row = cursor.fetchone()
                self.assertIsNotNone(profile_row)
                self.assertEqual(profile_row[0], "starter_rusty_home_computer")
                self.assertEqual(profile_row[1], 12)

                cursor.execute("DELETE FROM auth_sessions WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM player_profiles WHERE player_id = %s", (player_id,))
                cursor.execute("DELETE FROM players WHERE player_id = %s", (player_id,))
            connection.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)