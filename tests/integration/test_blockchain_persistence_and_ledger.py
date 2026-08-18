from __future__ import annotations

import os
import sys
import threading
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import psycopg


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.blockchain.store import PostgresBlockchainStateStore
from domain.economy.ledger import PostgresLedgerPoster
from domain.economy.read_models import project_player_reward_balances
from domain.mining.service import MiningSimulationService
from domain.players.service import PlayerProfileService
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/global_mining_network"


class BlockchainPersistenceAndLedgerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def setUp(self) -> None:
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM economy_player_ledger_entries")
                cursor.execute("DELETE FROM economy_ledger_entries")
                cursor.execute("DELETE FROM blockchain_finalized_blocks")
                cursor.execute("DELETE FROM blockchain_active_block")
            connection.commit()

    def test_active_block_state_persists_across_service_instances(self) -> None:
        started_at = datetime(2026, 8, 15, 16, 0, tzinfo=UTC)

        store = PostgresBlockchainStateStore(required_work=Decimal("100"))
        first_service = MiningSimulationService(required_work=Decimal("100"), blockchain_state_store=store)
        first_service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        first_service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        mid_snapshot = store.get_active_block()
        self.assertEqual(mid_snapshot.block_number, 1)
        self.assertEqual(mid_snapshot.accumulated_work, Decimal("50.000000"))

        second_service = MiningSimulationService(required_work=Decimal("100"), blockchain_state_store=store)
        second_service.register_operation(
            operation_id="op_b",
            base_hashrate_hps=Decimal("10"),
            started_at=started_at + timedelta(seconds=5),
        )
        result = second_service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=11))

        self.assertEqual(result.finalized_block_number, 1)
        self.assertEqual(store.get_active_block().block_number, 2)
        self.assertEqual(store.get_active_block().accumulated_work, Decimal("10.000000"))

        finalized = store.list_finalized_blocks()
        self.assertEqual(len(finalized), 1)
        self.assertEqual(finalized[0].block_number, 1)

    def test_finalization_posts_ledger_contract_entry(self) -> None:
        started_at = datetime(2026, 8, 15, 17, 0, tzinfo=UTC)

        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("25"), started_at=started_at)
        result = service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))
        self.assertEqual(result.finalized_block_number, 1)

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT entry_type, amount, reference_block_number
                    FROM economy_ledger_entries
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], "block.finalized.reward_pool.v1")
        self.assertEqual(row[1], Decimal("100.000000"))
        self.assertEqual(row[2], 1)

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT player_id, amount, block_number, contribution_hashes
                    FROM economy_player_ledger_entries
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                player_row = cursor.fetchone()

        self.assertIsNotNone(player_row)
        self.assertEqual(player_row[0], "op_a")
        self.assertEqual(player_row[1], Decimal("100.000000"))
        self.assertEqual(player_row[2], 1)
        self.assertEqual(player_row[3], Decimal("100.000000"))

    def test_cross_process_finalization_race_records_one_block_and_one_ledger_entry(self) -> None:
        started_at = datetime(2026, 8, 15, 18, 0, tzinfo=UTC)
        tick_end = started_at + timedelta(seconds=2)
        barrier = threading.Barrier(2)

        service_a = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service_b = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service_a.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("30"), started_at=started_at)
        service_b.register_operation(operation_id="op_b", player_id="player_b", base_hashrate_hps=Decimal("30"), started_at=started_at)

        results: list[int | None] = []
        results_lock = threading.Lock()

        def run_tick(service: MiningSimulationService, operation_id: str) -> None:
            barrier.wait()
            tick_result = service.process_tick(operation_id=operation_id, ended_at=tick_end)
            with results_lock:
                results.append(tick_result.finalized_block_number)

        threads = [
            threading.Thread(target=run_tick, args=(service_a, "op_a")),
            threading.Thread(target=run_tick, args=(service_b, "op_b")),
        ]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        self.assertEqual([item for item in results if item is not None], [1])

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM blockchain_finalized_blocks")
                self.assertEqual(cursor.fetchone()[0], 1)

                cursor.execute(
                    "SELECT COUNT(*) FROM economy_ledger_entries WHERE reference_block_number = %s",
                    (1,),
                )
                self.assertEqual(cursor.fetchone()[0], 1)

    def test_player_reward_ledger_replay_projects_deterministic_balances(self) -> None:
        started_at = datetime(2026, 8, 15, 18, 30, tzinfo=UTC)

        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(
            operation_id="op_a",
            player_id="player_a",
            base_hashrate_hps=Decimal("8"),
            started_at=started_at,
        )
        service.register_operation(
            operation_id="op_b",
            player_id="player_b",
            base_hashrate_hps=Decimal("2"),
            started_at=started_at,
        )

        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=10))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=10))

        first_projection = {
            entry.player_id: entry.reward_balance
            for entry in project_player_reward_balances()
        }
        second_projection = {
            entry.player_id: entry.reward_balance
            for entry in project_player_reward_balances()
        }

        self.assertEqual(first_projection, second_projection)
        self.assertEqual(first_projection["player_a"], Decimal("80.000000"))
        self.assertEqual(first_projection["player_b"], Decimal("20.000000"))
        self.assertEqual(sum(first_projection.values(), Decimal("0")), Decimal("100.000000"))

    def test_player_reward_replay_projects_cumulative_balances_across_multiple_blocks(self) -> None:
        started_at = datetime(2026, 8, 15, 18, 40, tzinfo=UTC)

        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(
            operation_id="op_a",
            player_id="player_a",
            base_hashrate_hps=Decimal("6"),
            started_at=started_at,
        )
        service.register_operation(
            operation_id="op_b",
            player_id="player_b",
            base_hashrate_hps=Decimal("4"),
            started_at=started_at,
        )

        # Block 1 finalization
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=10))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=10))
        # Block 2 finalization
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=20))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=20))

        projection = {entry.player_id: entry.reward_balance for entry in project_player_reward_balances()}

        self.assertEqual(projection["player_a"], Decimal("120.000000"))
        self.assertEqual(projection["player_b"], Decimal("80.000000"))
        self.assertEqual(sum(projection.values(), Decimal("0")), Decimal("200.000000"))

    def test_offline_progress_entries_preserve_cap_audit_fields(self) -> None:
        posted_at = datetime(2026, 8, 18, 1, 0, tzinfo=UTC)

        PostgresLedgerPoster().post_offline_progress_entry(
            player_id="player_a",
            credited_work=Decimal("1000.000000"),
            simulated_work=Decimal("1440.000000"),
            contribution_hashes=Decimal("1000.000000"),
            cap_applied=True,
            cap_amount=Decimal("440.000000"),
            offline_cap_tier=1,
            cap_limit=Decimal("1000"),
            window_started_at=posted_at - timedelta(minutes=2),
            window_ended_at=posted_at,
            posted_at=posted_at,
        )

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT amount, contribution_hashes, cap_applied, cap_amount, offline_cap_tier, currency, entry_type
                    FROM economy_player_ledger_entries
                    WHERE player_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    ("player_a",),
                )
                row = cursor.fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], Decimal("1000.000000"))
        self.assertEqual(row[1], Decimal("1000.000000"))
        self.assertTrue(row[2])
        self.assertEqual(row[3], Decimal("440.000000"))
        self.assertEqual(row[4], 1)
        self.assertEqual(row[5], "work")
        self.assertEqual(row[6], "mining.offline_progress.v1")

    def test_ledger_replay_matches_persisted_player_tier_and_offline_cap(self) -> None:
        email = "replay_progression@example.com"
        password_hash = "hash"
        player_id = "11111111-1111-4111-8111-111111111111"
        profile_service = PlayerProfileService()

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM auth_sessions WHERE player_id::text = %s", (player_id,))
                cursor.execute("DELETE FROM player_profiles WHERE player_id::text = %s", (player_id,))
                cursor.execute("DELETE FROM players WHERE player_id::text = %s", (player_id,))
                cursor.execute(
                    """
                    INSERT INTO players (player_id, email, password_hash)
                    VALUES (%s, %s, %s)
                    """,
                    (player_id, email, password_hash),
                )
            connection.commit()

        try:
            profile_service.repository.create_profile(UUID(player_id))
            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    for block_number in range(1, 21):
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
                                Decimal("5.000000"),
                                Decimal("5.000000"),
                                "credits",
                                "block.finalized.player_reward.v1",
                            ),
                        )
                    connection.commit()

            profile = profile_service.get_profile(player_id=player_id)

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(DISTINCT block_number)
                        FROM economy_player_ledger_entries
                        WHERE player_id = %s
                          AND entry_type = 'block.finalized.player_reward.v1'
                        """,
                        (player_id,),
                    )
                    block_count = cursor.fetchone()[0]

            replayed_tier = profile_service.calculate_player_tier(block_count)
            replayed_cap = profile_service.get_offline_cap_for_tier(replayed_tier)

            self.assertEqual(profile.blocks_finalized_contributed_count, block_count)
            self.assertEqual(profile.player_tier, replayed_tier)
            self.assertEqual(profile.current_offline_cap, replayed_cap)
            self.assertEqual(profile.player_tier, 3)
            self.assertEqual(profile.current_offline_cap, Decimal("10000"))
        finally:
            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM auth_sessions WHERE player_id::text = %s", (player_id,))
                    cursor.execute("DELETE FROM economy_player_ledger_entries WHERE player_id = %s", (player_id,))
                    cursor.execute("DELETE FROM player_profiles WHERE player_id::text = %s", (player_id,))
                    cursor.execute("DELETE FROM players WHERE player_id::text = %s", (player_id,))
                connection.commit()


if __name__ == "__main__":
    unittest.main(verbosity=2)