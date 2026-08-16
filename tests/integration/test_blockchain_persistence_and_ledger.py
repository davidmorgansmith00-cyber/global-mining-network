from __future__ import annotations

import os
import sys
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path

import psycopg


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.blockchain.store import PostgresBlockchainStateStore
from domain.economy.ledger import PostgresLedgerPoster
from domain.mining.service import MiningSimulationService
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


if __name__ == "__main__":
    unittest.main(verbosity=2)