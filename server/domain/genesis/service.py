from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from decimal import Decimal
import base64
import binascii
import hashlib
import hmac
import json
import os
from typing import Any, Callable
from uuid import uuid4

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from shared.database import database_is_configured, open_connection
from shared.settings import settings


GENESIS_LEDGER_ENTRY_TYPE = "genesis.balance.v1"
DEFAULT_REQUIRED_WORK = Decimal("100")
BALANCE_QUANTIZE = Decimal("0.000001")


@dataclass(frozen=True)
class GenesisPlayerSnapshot:
    player_id: str
    starting_balance: Decimal
    starting_tier: int
    joined_at: datetime
    migrated_from_beta: bool


@dataclass(frozen=True)
class GenesisBlockRecord:
    genesis_id: str
    block_hash: str
    merkle_root: str
    chain_id: str
    created_at: datetime
    announced_at: datetime | None
    created_by_admin_id: str
    signature: str
    public_message: str
    archived_at: datetime | None = None
    rollback_reason: str = ""


@dataclass(frozen=True)
class GenesisReadinessCheck:
    name: str
    passed: bool
    detail: str


class GenesisService:
    def __init__(
        self,
        *,
        readiness_probes: dict[str, Callable[[], tuple[bool, str] | bool]] | None = None,
        signing_key: str | None = None,
        environment: str | None = None,
        game_version: str = "0.1.0",
    ) -> None:
        self._readiness_probes = readiness_probes or self._default_readiness_probes()
        self._signing_key = signing_key or self._resolve_signing_key()
        self._environment = (environment or settings.environment or "local").strip().lower()
        self._game_version = game_version
        self._private_key = self._load_private_key(self._signing_key)
        self._in_memory_record: GenesisBlockRecord | None = None
        self._in_memory_snapshots: list[GenesisPlayerSnapshot] = []

    @staticmethod
    def build_chain_id(*, launch_date: datetime, environment: str, game_version: str) -> str:
        normalized = json.dumps(
            {
                "launch_date": launch_date.astimezone(UTC).replace(microsecond=0).isoformat(),
                "environment": environment.strip().lower(),
                "game_version": game_version.strip(),
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(normalized).hexdigest()

    def validate_genesis_readiness(self) -> dict[str, Any]:
        checks: list[GenesisReadinessCheck] = []
        for name, probe in self._readiness_probes.items():
            result = probe()
            if isinstance(result, tuple):
                passed, detail = bool(result[0]), str(result[1])
            else:
                passed = bool(result)
                detail = "ok" if passed else "not_ready"
            checks.append(GenesisReadinessCheck(name=name, passed=passed, detail=detail))
        return {
            "ready": all(item.passed for item in checks),
            "checks": [asdict(item) for item in checks],
        }

    def create_genesis_block(
        self,
        starting_balances: Decimal | dict[str, Decimal | int | str],
        tier_assignments: dict[str, int] | None,
        player_snapshot: list[dict[str, Any]] | list[GenesisPlayerSnapshot],
        *,
        created_by_admin_id: str = "system",
        launch_date: datetime | None = None,
        game_version: str | None = None,
        required_work: Decimal = DEFAULT_REQUIRED_WORK,
    ) -> str:
        existing = self.get_current_genesis_block(include_archived=False)
        if existing is not None:
            raise ValueError("genesis_already_exists")

        created_at = (launch_date or datetime.now(UTC)).astimezone(UTC)
        normalized_snapshots = self._normalize_player_snapshots(
            starting_balances=starting_balances,
            tier_assignments=tier_assignments or {},
            player_snapshot=player_snapshot,
            created_at=created_at,
        )
        chain_id = self.build_chain_id(
            launch_date=created_at,
            environment=self._environment,
            game_version=game_version or self._game_version,
        )
        merkle_root = self._compute_merkle_root(normalized_snapshots)
        block_hash = self._compute_block_hash(
            chain_id=chain_id,
            created_at=created_at,
            merkle_root=merkle_root,
            player_snapshots=normalized_snapshots,
        )
        record = GenesisBlockRecord(
            genesis_id=str(uuid4()),
            block_hash=block_hash,
            merkle_root=merkle_root,
            chain_id=chain_id,
            created_at=created_at,
            announced_at=None,
            created_by_admin_id=created_by_admin_id,
            signature=self._sign_block_hash(block_hash),
            public_message="",
        )

        if database_is_configured():
            self._persist_genesis(
                record=record,
                player_snapshots=normalized_snapshots,
                required_work=required_work,
            )
        else:
            self._in_memory_record = record
            self._in_memory_snapshots = normalized_snapshots
        return record.genesis_id

    def announce_genesis(self, genesis_id: str, public_message: str) -> GenesisBlockRecord:
        record = self._require_genesis_record(genesis_id)
        if record.archived_at is not None:
            raise PermissionError("genesis_archived")
        if record.announced_at is not None:
            raise PermissionError("genesis_already_announced")
        announced_at = datetime.now(UTC)
        updated = GenesisBlockRecord(
            genesis_id=record.genesis_id,
            block_hash=record.block_hash,
            merkle_root=record.merkle_root,
            chain_id=record.chain_id,
            created_at=record.created_at,
            announced_at=announced_at,
            created_by_admin_id=record.created_by_admin_id,
            signature=record.signature,
            public_message=public_message.strip(),
            archived_at=None,
            rollback_reason="",
        )
        self._store_record(updated)
        return updated

    def verify_genesis_signature(self, genesis_block: GenesisBlockRecord | None = None) -> bool:
        record = genesis_block or self.get_current_genesis_block(include_archived=False)
        if record is None or record.archived_at is not None:
            return False
        snapshots = self.list_player_snapshots(record.genesis_id)
        expected_merkle_root = self._compute_merkle_root(snapshots)
        if not hmac.compare_digest(expected_merkle_root, record.merkle_root):
            return False
        expected_block_hash = self._compute_block_hash(
            chain_id=record.chain_id,
            created_at=record.created_at,
            merkle_root=record.merkle_root,
            player_snapshots=snapshots,
        )
        if not hmac.compare_digest(expected_block_hash, record.block_hash):
            return False
        try:
            self._private_key.public_key().verify(
                base64.b64decode(record.signature),
                record.block_hash.encode("utf-8"),
            )
        except Exception:
            return False
        return True

    def rollback_genesis(self, genesis_id: str, reason: str) -> GenesisBlockRecord:
        record = self._require_genesis_record(genesis_id)
        if record.announced_at is not None:
            raise PermissionError("genesis_immutable_after_announcement")
        archived = GenesisBlockRecord(
            genesis_id=record.genesis_id,
            block_hash=record.block_hash,
            merkle_root=record.merkle_root,
            chain_id=record.chain_id,
            created_at=record.created_at,
            announced_at=None,
            created_by_admin_id=record.created_by_admin_id,
            signature=record.signature,
            public_message=record.public_message,
            archived_at=datetime.now(UTC),
            rollback_reason=reason.strip(),
        )
        if database_is_configured():
            self._rollback_persisted_genesis(archived)
        else:
            self._in_memory_record = archived
        return archived

    def get_genesis_status(self) -> str:
        record = self.get_current_genesis_block(include_archived=False)
        if record is None:
            return "pre-genesis"
        if record.announced_at is None:
            return "genesis-created"
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COALESCE(MAX(block_number), 1)
                        FROM blockchain_finalized_blocks
                        """
                    )
                    latest_finalized_block = int(cursor.fetchone()[0])
            if latest_finalized_block > 1:
                return "post-genesis"
        return "genesis-announced"

    def initialize_runtime(self) -> dict[str, Any]:
        record = self.get_current_genesis_block(include_archived=False)
        if record is None:
            return {"status": "pre-genesis", "signature_valid": False}
        signature_valid = self.verify_genesis_signature(record)
        if not signature_valid:
            raise RuntimeError("genesis_signature_invalid")
        return {
            "status": self.get_genesis_status(),
            "signature_valid": signature_valid,
            "genesis_id": record.genesis_id,
            "chain_id": record.chain_id,
        }

    def get_current_genesis_block(self, *, include_archived: bool = False) -> GenesisBlockRecord | None:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    clause = "" if include_archived else "WHERE archived_at IS NULL"
                    cursor.execute(
                        f"""
                        SELECT
                            genesis_id::text,
                            block_hash,
                            merkle_root,
                            chain_id,
                            created_at,
                            announced_at,
                            created_by_admin_id,
                            signature,
                            public_message,
                            archived_at,
                            rollback_reason
                        FROM genesis_block
                        {clause}
                        ORDER BY created_at DESC
                        LIMIT 1
                        """
                    )
                    row = cursor.fetchone()
            return self._row_to_record(row)
        if self._in_memory_record is None:
            return None
        if not include_archived and self._in_memory_record.archived_at is not None:
            return None
        return self._in_memory_record

    def get_genesis_block(self, genesis_id: str) -> GenesisBlockRecord | None:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            genesis_id::text,
                            block_hash,
                            merkle_root,
                            chain_id,
                            created_at,
                            announced_at,
                            created_by_admin_id,
                            signature,
                            public_message,
                            archived_at,
                            rollback_reason
                        FROM genesis_block
                        WHERE genesis_id::text = %s
                        """,
                        (genesis_id,),
                    )
                    row = cursor.fetchone()
            return self._row_to_record(row)
        if self._in_memory_record and self._in_memory_record.genesis_id == genesis_id:
            return self._in_memory_record
        return None

    def list_player_snapshots(self, genesis_id: str) -> list[GenesisPlayerSnapshot]:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT
                            player_id,
                            starting_balance,
                            starting_tier,
                            joined_at,
                            migrated_from_beta
                        FROM genesis_player_snapshot
                        WHERE genesis_id::text = %s
                        ORDER BY player_id ASC
                        """,
                        (genesis_id,),
                    )
                    rows = cursor.fetchall()
            return [
                GenesisPlayerSnapshot(
                    player_id=str(row[0]),
                    starting_balance=Decimal(str(row[1])).quantize(BALANCE_QUANTIZE),
                    starting_tier=int(row[2]),
                    joined_at=row[3].astimezone(UTC),
                    migrated_from_beta=bool(row[4]),
                )
                for row in rows
            ]
        if self._in_memory_record and self._in_memory_record.genesis_id == genesis_id:
            return list(self._in_memory_snapshots)
        return []

    def get_status_payload(self) -> dict[str, Any]:
        record = self.get_current_genesis_block(include_archived=False)
        readiness = self.validate_genesis_readiness()
        return {
            "status": self.get_genesis_status(),
            "ready": readiness["ready"],
            "checks": readiness["checks"],
            "genesis": None if record is None else self.serialize_genesis_block(record),
        }

    def serialize_genesis_block(self, record: GenesisBlockRecord) -> dict[str, Any]:
        return {
            "genesis_id": record.genesis_id,
            "block_number": 1,
            "block_hash": record.block_hash,
            "merkle_root": record.merkle_root,
            "chain_id": record.chain_id,
            "created_at": record.created_at.isoformat(),
            "announced_at": None if record.announced_at is None else record.announced_at.isoformat(),
            "created_by_admin_id": record.created_by_admin_id,
            "signature": record.signature,
            "public_message": record.public_message,
            "archived_at": None if record.archived_at is None else record.archived_at.isoformat(),
            "rollback_reason": record.rollback_reason,
            "signature_valid": self.verify_genesis_signature(record),
            "public_key": self._public_key_hex(),
            "player_snapshots": [
                {
                    "player_id": item.player_id,
                    "starting_balance": str(item.starting_balance),
                    "starting_tier": item.starting_tier,
                    "joined_at": item.joined_at.isoformat(),
                    "migrated_from_beta": item.migrated_from_beta,
                }
                for item in self.list_player_snapshots(record.genesis_id)
            ],
        }

    def _persist_genesis(
        self,
        *,
        record: GenesisBlockRecord,
        player_snapshots: list[GenesisPlayerSnapshot],
        required_work: Decimal,
    ) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO genesis_block (
                        genesis_id,
                        block_hash,
                        merkle_root,
                        chain_id,
                        created_at,
                        announced_at,
                        created_by_admin_id,
                        signature,
                        public_message,
                        archived_at,
                        rollback_reason
                    )
                    VALUES (%s::uuid, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        record.genesis_id,
                        record.block_hash,
                        record.merkle_root,
                        record.chain_id,
                        record.created_at,
                        record.announced_at,
                        record.created_by_admin_id,
                        record.signature,
                        record.public_message,
                        record.archived_at,
                        record.rollback_reason,
                    ),
                )
                for snapshot in player_snapshots:
                    cursor.execute(
                        """
                        INSERT INTO genesis_player_snapshot (
                            genesis_id,
                            player_id,
                            starting_balance,
                            starting_tier,
                            joined_at,
                            migrated_from_beta
                        )
                        VALUES (%s::uuid, %s, %s, %s, %s, %s)
                        """,
                        (
                            record.genesis_id,
                            snapshot.player_id,
                            snapshot.starting_balance,
                            snapshot.starting_tier,
                            snapshot.joined_at,
                            snapshot.migrated_from_beta,
                        ),
                    )
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
                        VALUES (%s::uuid, 1, %s, %s, 0, 'credits', %s, %s::jsonb)
                        """,
                        (
                            str(uuid4()),
                            snapshot.player_id,
                            snapshot.starting_balance,
                            GENESIS_LEDGER_ENTRY_TYPE,
                            json.dumps(
                                {
                                    "genesis_id": record.genesis_id,
                                    "starting_tier": snapshot.starting_tier,
                                    "migrated_from_beta": snapshot.migrated_from_beta,
                                }
                            ),
                        ),
                    )
                    cursor.execute(
                        """
                        UPDATE players
                        SET player_tier = %s,
                            last_offline_progress_at = COALESCE(last_offline_progress_at, %s),
                            updated_at = NOW()
                        WHERE player_id::text = %s
                        """,
                        (snapshot.starting_tier, record.created_at, snapshot.player_id),
                    )
                cursor.execute(
                    """
                    INSERT INTO blockchain_finalized_blocks (
                        block_number,
                        required_work,
                        total_work,
                        finalized_at
                    )
                    VALUES (1, 0, 0, %s)
                    ON CONFLICT (block_number) DO NOTHING
                    """,
                    (record.created_at,),
                )
                cursor.execute(
                    """
                    INSERT INTO blockchain_active_block (singleton_id, block_number, required_work, accumulated_work, updated_at)
                    VALUES (TRUE, 2, %s, 0, NOW())
                    ON CONFLICT (singleton_id)
                    DO UPDATE SET block_number = EXCLUDED.block_number,
                                  required_work = EXCLUDED.required_work,
                                  accumulated_work = 0,
                                  updated_at = NOW()
                    """,
                    (required_work,),
                )
            connection.commit()

    def _rollback_persisted_genesis(self, record: GenesisBlockRecord) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE genesis_block
                    SET archived_at = %s,
                        rollback_reason = %s
                    WHERE genesis_id::text = %s
                    """,
                    (record.archived_at, record.rollback_reason, record.genesis_id),
                )
                cursor.execute(
                    """
                    DELETE FROM economy_player_ledger_entries
                    WHERE entry_type = %s
                      AND metadata->>'genesis_id' = %s
                    """,
                    (GENESIS_LEDGER_ENTRY_TYPE, record.genesis_id),
                )
                cursor.execute(
                    """
                    DELETE FROM blockchain_finalized_blocks
                    WHERE block_number = 1
                      AND total_work = 0
                    """
                )
                cursor.execute("DELETE FROM blockchain_active_block WHERE singleton_id = TRUE")
                cursor.execute(
                    """
                    UPDATE players
                    SET player_tier = 1,
                        updated_at = NOW()
                    WHERE player_id::text IN (
                        SELECT player_id
                        FROM genesis_player_snapshot
                        WHERE genesis_id::text = %s
                    )
                    """,
                    (record.genesis_id,),
                )
            connection.commit()

    def _require_genesis_record(self, genesis_id: str) -> GenesisBlockRecord:
        record = self.get_genesis_block(genesis_id)
        if record is None:
            raise KeyError(f"unknown genesis block: {genesis_id}")
        return record

    def _store_record(self, record: GenesisBlockRecord) -> None:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE genesis_block
                        SET announced_at = %s,
                            public_message = %s,
                            archived_at = %s,
                            rollback_reason = %s
                        WHERE genesis_id::text = %s
                        """,
                        (
                            record.announced_at,
                            record.public_message,
                            record.archived_at,
                            record.rollback_reason,
                            record.genesis_id,
                        ),
                    )
                connection.commit()
            return
        self._in_memory_record = record

    def _normalize_player_snapshots(
        self,
        *,
        starting_balances: Decimal | dict[str, Decimal | int | str],
        tier_assignments: dict[str, int],
        player_snapshot: list[dict[str, Any]] | list[GenesisPlayerSnapshot],
        created_at: datetime,
    ) -> list[GenesisPlayerSnapshot]:
        normalized: list[GenesisPlayerSnapshot] = []
        default_balance = (
            Decimal(str(starting_balances)).quantize(BALANCE_QUANTIZE)
            if not isinstance(starting_balances, dict)
            else None
        )
        for item in player_snapshot:
            if isinstance(item, GenesisPlayerSnapshot):
                player_id = item.player_id
                joined_at = item.joined_at.astimezone(UTC)
                migrated_from_beta = item.migrated_from_beta
                balance = item.starting_balance.quantize(BALANCE_QUANTIZE)
                tier = item.starting_tier
            else:
                player_id = str(item["player_id"])
                joined_at_value = item.get("joined_at") or created_at
                joined_at = (
                    joined_at_value.astimezone(UTC)
                    if isinstance(joined_at_value, datetime)
                    else datetime.fromisoformat(str(joined_at_value)).astimezone(UTC)
                )
                migrated_from_beta = bool(item.get("migrated_from_beta", False))
                raw_balance = (
                    starting_balances.get(player_id, 0)
                    if isinstance(starting_balances, dict)
                    else default_balance
                )
                balance = Decimal(str(raw_balance or 0)).quantize(BALANCE_QUANTIZE)
                tier = int(tier_assignments.get(player_id, item.get("starting_tier", 1)))
            normalized.append(
                GenesisPlayerSnapshot(
                    player_id=player_id,
                    starting_balance=balance,
                    starting_tier=max(1, tier),
                    joined_at=joined_at,
                    migrated_from_beta=migrated_from_beta,
                )
            )
        normalized.sort(key=lambda entry: entry.player_id)
        return normalized

    def _compute_merkle_root(self, player_snapshots: list[GenesisPlayerSnapshot]) -> str:
        if not player_snapshots:
            return hashlib.sha256(b"genesis:empty").hexdigest()
        leaf_hashes = [
            hashlib.sha256(
                json.dumps(
                    {
                        "player_id": item.player_id,
                        "starting_balance": str(item.starting_balance),
                        "starting_tier": item.starting_tier,
                        "joined_at": item.joined_at.astimezone(UTC).isoformat(),
                        "migrated_from_beta": item.migrated_from_beta,
                    },
                    sort_keys=True,
                    separators=(",", ":"),
                ).encode("utf-8")
            ).hexdigest()
            for item in player_snapshots
        ]
        while len(leaf_hashes) > 1:
            if len(leaf_hashes) % 2 == 1:
                leaf_hashes.append(leaf_hashes[-1])
            next_level: list[str] = []
            for index in range(0, len(leaf_hashes), 2):
                next_level.append(
                    hashlib.sha256(f"{leaf_hashes[index]}:{leaf_hashes[index + 1]}".encode("utf-8")).hexdigest()
                )
            leaf_hashes = next_level
        return leaf_hashes[0]

    def _compute_block_hash(
        self,
        *,
        chain_id: str,
        created_at: datetime,
        merkle_root: str,
        player_snapshots: list[GenesisPlayerSnapshot],
    ) -> str:
        payload = json.dumps(
            {
                "block_number": 1,
                "chain_id": chain_id,
                "created_at": created_at.astimezone(UTC).isoformat(),
                "merkle_root": merkle_root,
                "players": [
                    {
                        "player_id": item.player_id,
                        "starting_balance": str(item.starting_balance),
                        "starting_tier": item.starting_tier,
                        "joined_at": item.joined_at.astimezone(UTC).isoformat(),
                        "migrated_from_beta": item.migrated_from_beta,
                    }
                    for item in player_snapshots
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    def _sign_block_hash(self, block_hash: str) -> str:
        signature = self._private_key.sign(block_hash.encode("utf-8"))
        return base64.b64encode(signature).decode("ascii")

    @staticmethod
    def _row_to_record(row: Any) -> GenesisBlockRecord | None:
        if row is None:
            return None
        return GenesisBlockRecord(
            genesis_id=str(row[0]),
            block_hash=row[1],
            merkle_root=row[2],
            chain_id=row[3],
            created_at=row[4].astimezone(UTC),
            announced_at=None if row[5] is None else row[5].astimezone(UTC),
            created_by_admin_id=row[6],
            signature=row[7],
            public_message=row[8] or "",
            archived_at=None if row[9] is None else row[9].astimezone(UTC),
            rollback_reason=row[10] or "",
        )

    def _default_readiness_probes(self) -> dict[str, Callable[[], tuple[bool, str] | bool]]:
        def _database() -> tuple[bool, str]:
            return database_is_configured(), "configured" if database_is_configured() else "database_url_missing"

        def _cache() -> tuple[bool, str]:
            configured = bool(settings.redis_url.strip())
            return configured, "configured" if configured else "redis_url_missing"

        def _message_queue() -> tuple[bool, str]:
            queue_url = os.getenv("MESSAGE_QUEUE_URL", "").strip() or os.getenv("WORKER_QUEUE_URL", "").strip()
            return bool(queue_url), "configured" if queue_url else "queue_url_missing"

        def _clean_slate() -> tuple[bool, str]:
            if not database_is_configured():
                return False, "database_unavailable"
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT COUNT(*)
                        FROM blockchain_finalized_blocks
                        WHERE block_number > 1
                        """
                    )
                    pending = int(cursor.fetchone()[0])
            return pending == 0, "clean_slate" if pending == 0 else "existing_finalized_blocks"

        return {
            "database": _database,
            "redis_cache": _cache,
            "message_queue": _message_queue,
            "block_finalization_clean_slate": _clean_slate,
            "api_health": lambda: (True, "healthy"),
        }

    def _resolve_signing_key(self) -> str:
        configured_key = os.getenv("GENESIS_SIGNING_KEY", "").strip()
        if configured_key:
            return configured_key
        if (settings.environment or "local").strip().lower() in {"local", "test", "testing"}:
            return "local-genesis-signing-key"
        raise ValueError("GENESIS_SIGNING_KEY is required outside local and test environments")

    def _load_private_key(self, configured_key: str) -> Ed25519PrivateKey:
        pem_key = configured_key.encode("utf-8")
        if configured_key.startswith("-----BEGIN"):
            loaded = serialization.load_pem_private_key(pem_key, None)
            if isinstance(loaded, Ed25519PrivateKey):
                return loaded
            raise ValueError("GENESIS_SIGNING_KEY must be an ed25519 private key")

        candidate_bytes: bytes | None = None
        try:
            candidate_bytes = bytes.fromhex(configured_key)
        except ValueError:
            try:
                candidate_bytes = base64.b64decode(configured_key, validate=True)
            except (binascii.Error, ValueError):
                candidate_bytes = None

        if candidate_bytes is not None and len(candidate_bytes) == 32:
            return Ed25519PrivateKey.from_private_bytes(candidate_bytes)

        if self._environment in {"local", "test", "testing"}:
            return Ed25519PrivateKey.from_private_bytes(hashlib.sha256(configured_key.encode("utf-8")).digest())

        raise ValueError("GENESIS_SIGNING_KEY must be a PEM, hex, or base64 encoded 32-byte ed25519 key")

    def _public_key_hex(self) -> str:
        public_key_bytes = self._private_key.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return public_key_bytes.hex()


_genesis_service = GenesisService()


def get_genesis_service() -> GenesisService:
    return _genesis_service
