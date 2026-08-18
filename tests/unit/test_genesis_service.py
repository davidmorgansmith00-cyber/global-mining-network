from __future__ import annotations

import base64
import sys
import unittest
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.genesis.service import GenesisService


def _test_signing_key() -> str:
    private_key = Ed25519PrivateKey.generate()
    return base64.b64encode(
        private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    ).decode("ascii")


class GenesisServiceTests(unittest.TestCase):
    def setUp(self) -> None:
        readiness = {
            "database": lambda: (True, "configured"),
            "redis_cache": lambda: (True, "configured"),
            "message_queue": lambda: (True, "configured"),
            "block_finalization_clean_slate": lambda: (True, "clean_slate"),
            "api_health": lambda: (True, "healthy"),
        }
        self.service = GenesisService(
            readiness_probes=readiness,
            signing_key=_test_signing_key(),
            environment="test",
            game_version="1.2.3",
        )
        self.player_snapshot = [
            {
                "player_id": "player-a",
                "joined_at": datetime(2026, 8, 18, 12, 0, tzinfo=UTC),
                "migrated_from_beta": True,
            },
            {
                "player_id": "player-b",
                "joined_at": datetime(2026, 8, 18, 12, 5, tzinfo=UTC),
                "migrated_from_beta": False,
            },
        ]
        self.starting_balances = {
            "player-a": Decimal("1000"),
            "player-b": Decimal("750"),
        }
        self.tiers = {"player-a": 2, "player-b": 1}

    @patch("domain.genesis.service.database_is_configured", return_value=False)
    def test_chain_id_is_deterministic_for_same_inputs(self, _mock_db: object) -> None:
        launch_date = datetime(2026, 8, 18, 15, 0, tzinfo=UTC)
        first = self.service.build_chain_id(
            launch_date=launch_date,
            environment="production",
            game_version="2.0.0",
        )
        second = self.service.build_chain_id(
            launch_date=launch_date,
            environment="production",
            game_version="2.0.0",
        )
        self.assertEqual(first, second)

    @patch("domain.genesis.service.database_is_configured", return_value=False)
    def test_validate_genesis_readiness_reports_ready_when_all_checks_pass(self, _mock_db: object) -> None:
        readiness = self.service.validate_genesis_readiness()
        self.assertTrue(readiness["ready"])
        self.assertEqual(len(readiness["checks"]), 5)

    @patch("domain.genesis.service.database_is_configured", return_value=False)
    def test_create_genesis_block_generates_verifiable_record(self, _mock_db: object) -> None:
        launch_date = datetime(2026, 8, 18, 15, 7, tzinfo=UTC)
        genesis_id = self.service.create_genesis_block(
            self.starting_balances,
            self.tiers,
            self.player_snapshot,
            launch_date=launch_date,
        )
        record = self.service.get_genesis_block(genesis_id)
        self.assertIsNotNone(record)
        self.assertEqual(
            record.chain_id,
            self.service.build_chain_id(
                launch_date=launch_date,
                environment="test",
                game_version="1.2.3",
            ),
        )
        self.assertTrue(self.service.verify_genesis_signature(record))
        self.assertEqual(self.service.get_genesis_status(), "genesis-created")

    @patch("domain.genesis.service.database_is_configured", return_value=False)
    def test_announce_genesis_makes_record_immutable_to_rollback(self, _mock_db: object) -> None:
        genesis_id = self.service.create_genesis_block(self.starting_balances, self.tiers, self.player_snapshot)
        announced = self.service.announce_genesis(genesis_id, "Genesis is live.")
        self.assertIsNotNone(announced.announced_at)
        self.assertEqual(self.service.get_genesis_status(), "genesis-announced")
        with self.assertRaises(PermissionError):
            self.service.rollback_genesis(genesis_id, "too late")

    @patch("domain.genesis.service.database_is_configured", return_value=False)
    def test_rollback_marks_pre_announced_genesis_archived(self, _mock_db: object) -> None:
        genesis_id = self.service.create_genesis_block(self.starting_balances, self.tiers, self.player_snapshot)
        archived = self.service.rollback_genesis(genesis_id, "staging validation failed")
        self.assertIsNotNone(archived.archived_at)
        self.assertEqual(archived.rollback_reason, "staging validation failed")
        self.assertEqual(self.service.get_genesis_status(), "pre-genesis")

    @patch("domain.genesis.service.database_is_configured", return_value=False)
    def test_verify_genesis_signature_rejects_tampered_record(self, _mock_db: object) -> None:
        genesis_id = self.service.create_genesis_block(self.starting_balances, self.tiers, self.player_snapshot)
        record = self.service.get_genesis_block(genesis_id)
        tampered = type(record)(
            genesis_id=record.genesis_id,
            block_hash=record.block_hash,
            merkle_root="bad-root",
            chain_id=record.chain_id,
            created_at=record.created_at,
            announced_at=record.announced_at,
            created_by_admin_id=record.created_by_admin_id,
            signature=record.signature,
            public_message=record.public_message,
            archived_at=record.archived_at,
            rollback_reason=record.rollback_reason,
        )
        self.assertFalse(self.service.verify_genesis_signature(tampered))


if __name__ == "__main__":
    unittest.main(verbosity=2)
