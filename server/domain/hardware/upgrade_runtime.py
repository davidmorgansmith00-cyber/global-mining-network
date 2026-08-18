from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from uuid import UUID, uuid4

from psycopg.errors import UniqueViolation

from domain.hardware.upgrade_service import HardwareUpgradeService
from domain.market.service import NpcMarketService
from shared.database import database_is_configured, open_connection

UPGRADE_DURATION_SECONDS = 86400
UPGRADE_LEDGER_ENTRY_TYPE = "hardware.upgrade.start.v1"


class HardwareUpgradeRuntimeService:
    def __init__(self) -> None:
        self.definitions = HardwareUpgradeService()
        self.market = NpcMarketService()

    def start(self, *, player_id: str, hardware_id: str, idempotency_key: str) -> dict[str, object]:
        if not database_is_configured():
            return {"status": "rejected", "reason": "database_unavailable"}
        if not idempotency_key.strip():
            return {"status": "rejected", "reason": "idempotency_key_required"}
        target = self.definitions.get_definition(hardware_id)
        if target is None or target.tier < 2:
            return {"status": "rejected", "reason": "hardware_not_upgradeable"}

        player_uuid = UUID(player_id)
        now = datetime.now(UTC)
        try:
            with open_connection() as connection:
                connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                with connection.cursor() as cursor:
                    cursor.execute(
                        "SELECT hardware_id, COALESCE(player_tier, 1) FROM players WHERE player_id = %s FOR UPDATE",
                        (player_uuid,),
                    )
                    player = cursor.fetchone()
                    if player is None:
                        return {"status": "rejected", "reason": "player_not_found"}
                    previous_hardware_id, player_tier = str(player[0]), int(player[1])
                    existing = self._get_by_key(cursor, player_uuid, idempotency_key)
                    if existing is not None:
                        return self._serialize(existing)
                    if previous_hardware_id == hardware_id:
                        return {"status": "rejected", "reason": "hardware_already_equipped"}
                    if target.unlock_condition and player_tier < int(target.unlock_condition.split(">=")[-1].strip()):
                        return {"status": "rejected", "reason": "tier_locked"}
                    cursor.execute(
                        "SELECT upgrade_id, hardware_id, previous_hardware_id, idempotency_key, status, cost, started_at, completes_at, completed_at, rejection_reason FROM hardware_upgrade_operations WHERE player_id = %s AND status = 'running' FOR UPDATE",
                        (player_uuid,),
                    )
                    if cursor.fetchone() is not None:
                        return {"status": "rejected", "reason": "upgrade_in_progress"}
                    balance = self.market._get_player_credit_balance(cursor=cursor, player_id=player_id)
                    cost = target.market_price.quantize(Decimal("0.000001"))
                    if balance < cost:
                        return {"status": "rejected", "reason": "insufficient_balance"}
                    upgrade_id = uuid4()
                    completes_at = now + timedelta(seconds=UPGRADE_DURATION_SECONDS)
                    cursor.execute(
                        "INSERT INTO hardware_upgrade_operations (upgrade_id, player_id, hardware_id, previous_hardware_id, idempotency_key, cost, started_at, completes_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
                        (upgrade_id, player_uuid, hardware_id, previous_hardware_id, idempotency_key, cost, now, completes_at),
                    )
                    cursor.execute(
                        "INSERT INTO economy_player_ledger_entries (ledger_entry_id, player_id, amount, contribution_hashes, currency, entry_type, item_id, previous_item_id, quantity, unit_price, total_cost, metadata, created_at) VALUES (%s, %s, %s, 0, 'credits', %s, %s, %s, 1, %s, %s, %s::jsonb, %s)",
                        (uuid4(), player_id, -cost, UPGRADE_LEDGER_ENTRY_TYPE, hardware_id, previous_hardware_id, cost, cost, json.dumps({"upgrade_id": str(upgrade_id), "idempotency_key": idempotency_key}), now),
                    )
                connection.commit()
        except UniqueViolation:
            return {"status": "rejected", "reason": "upgrade_conflict"}
        return {"status": "running", "upgrade_id": str(upgrade_id), "hardware_id": hardware_id, "started_at": now, "completes_at": completes_at, "completion_confirmed": False}

    def current(self, *, player_id: str) -> dict[str, object]:
        if not database_is_configured():
            return {"status": "rejected", "reason": "database_unavailable"}
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT upgrade_id, hardware_id, previous_hardware_id, status, cost, started_at, completes_at, completed_at, rejection_reason FROM hardware_upgrade_operations WHERE player_id = %s ORDER BY started_at DESC LIMIT 1", (UUID(player_id),))
                row = cursor.fetchone()
                if row is None:
                    return {"schema_version": "hardware.upgrade.v1", "status": "idle", "completion_confirmed": False}
                result = self._serialize(row)
                if result.get("status") == "running" and datetime.now(UTC) >= result["completes_at"]:
                    self._complete(cursor, player_id, result)
                    connection.commit()
                    result["status"] = "completed"
                    result["completed_at"] = datetime.now(UTC)
                    result["completion_confirmed"] = True
                return result

    @staticmethod
    def _get_by_key(cursor, player_uuid: UUID, key: str):
        cursor.execute("SELECT upgrade_id, hardware_id, previous_hardware_id, idempotency_key, status, cost, started_at, completes_at, completed_at, rejection_reason FROM hardware_upgrade_operations WHERE player_id = %s AND idempotency_key = %s", (player_uuid, key))
        return cursor.fetchone()

    def _complete(self, cursor, player_id: str, result: dict[str, object]) -> None:
        cursor.execute("UPDATE players SET hardware_id = %s, power_consumed = (SELECT base_power_consumption FROM hardware_definitions WHERE hardware_id = %s), heat_generated = 0, updated_at = %s WHERE player_id = %s", (result["hardware_id"], result["hardware_id"], datetime.now(UTC), UUID(player_id)))
        cursor.execute("UPDATE hardware_upgrade_operations SET status = 'completed', completed_at = %s WHERE upgrade_id = %s AND status = 'running'", (datetime.now(UTC), UUID(str(result["upgrade_id"]))))

    @staticmethod
    def _serialize(row) -> dict[str, object]:
        return {
            "schema_version": "hardware.upgrade.v1",
            "upgrade_id": str(row[0]),
            "hardware_id": str(row[1]),
            "previous_hardware_id": str(row[2]),
            "status": str(row[3]),
            "cost": row[4],
            "started_at": row[5],
            "completes_at": row[6],
            "completed_at": row[7],
            "rejection_reason": row[8],
            "completion_confirmed": str(row[3]) == "completed",
        }
