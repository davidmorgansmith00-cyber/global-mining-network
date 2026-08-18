from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import hashlib
import hmac
import json
import os
from uuid import uuid4

from domain.events.service import EventService
from shared.database import database_is_configured, open_connection


class AdminService:
    def __init__(self, *, event_service: EventService | None = None) -> None:
        self._event_service = event_service or EventService()
        self._maintenance_state = {"pause_blocks": False, "maintenance_mode": False}

    def get_roles(self, *, admin_id: str) -> set[str]:
        if not database_is_configured():
            return set()
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT role
                    FROM admin_roles
                    WHERE admin_id = %s
                      AND revoked_at IS NULL
                    """,
                    (admin_id,),
                )
                rows = cursor.fetchall()
        return {str(row[0]) for row in rows}

    def verify_password(self, password: str) -> bool:
        required_password_hash = os.getenv("ADMIN_DASHBOARD_PASSWORD_HASH", "").strip()
        if required_password_hash:
            candidate_hash = hashlib.sha256(password.encode("utf-8")).hexdigest()
            return hmac.compare_digest(candidate_hash, required_password_hash)
        required_password = os.getenv("ADMIN_DASHBOARD_PASSWORD", "local-admin-password")
        return hmac.compare_digest(password, required_password)

    def get_dashboard_metrics(self) -> dict[str, object]:
        if not database_is_configured():
            return {
                "active_players": 0,
                "blocks_last_hour": 0,
                "avg_block_time_seconds": 0.0,
                "pending_rewards": "0.000000",
                "maintenance": self._maintenance_state,
            }
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT COUNT(*) FROM players
                    WHERE updated_at >= NOW() - INTERVAL '24 hours'
                    """
                )
                active_players = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM blockchain_finalized_blocks
                    WHERE finalized_at >= NOW() - INTERVAL '1 hour'
                    """
                )
                blocks_last_hour = int(cursor.fetchone()[0])
                cursor.execute(
                    """
                    SELECT COALESCE(AVG(extract(epoch from finalized_at - LAG(finalized_at) OVER (ORDER BY block_number))), 0)
                    FROM blockchain_finalized_blocks
                    """
                )
                avg_block_time = float(cursor.fetchone()[0] or 0.0)
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM economy_player_ledger_entries
                    WHERE entry_type = 'block.finalized.player_reward.v1'
                    """
                )
                pending_rewards = Decimal(str(cursor.fetchone()[0]))
        return {
            "active_players": active_players,
            "blocks_last_hour": blocks_last_hour,
            "avg_block_time_seconds": avg_block_time,
            "pending_rewards": str(pending_rewards.quantize(Decimal("0.000001"))),
            "maintenance": self._maintenance_state,
        }

    def get_config(self) -> dict[str, object]:
        if not database_is_configured():
            return {}
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT config_key, config_value FROM admin_config_values ORDER BY config_key ASC")
                rows = cursor.fetchall()
        return {row[0]: row[1] for row in rows}

    def set_config(self, *, key: str, value: object, admin_id: str, reason: str) -> None:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT config_value FROM admin_config_values WHERE config_key = %s", (key,))
                previous = cursor.fetchone()
                cursor.execute(
                    """
                    INSERT INTO admin_config_values (config_key, config_value, updated_by, updated_at)
                    VALUES (%s, %s::jsonb, %s, NOW())
                    ON CONFLICT (config_key)
                    DO UPDATE SET config_value = EXCLUDED.config_value, updated_by = EXCLUDED.updated_by, updated_at = NOW()
                    """,
                    (key, json.dumps(value), admin_id),
                )
                self._insert_audit_log(
                    cursor=cursor,
                    admin_id=admin_id,
                    action_type="admin.config.update",
                    resource_id=key,
                    old_value=None if previous is None else previous[0],
                    new_value=value,
                    reason=reason,
                    twofa_verified=False,
                    ip_address="",
                    user_agent="",
                )
            connection.commit()

    def get_player_state(self, *, player_id: str) -> dict[str, object] | None:
        if not database_is_configured():
            return None
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT p.player_id::text, p.email, COALESCE(p.player_tier, 1), COALESCE(p.effective_hashrate_cached, 0)
                    FROM players p
                    WHERE p.player_id::text = %s
                    """,
                    (player_id,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute(
                    """
                    SELECT COALESCE(SUM(amount), 0)
                    FROM economy_player_ledger_entries
                    WHERE player_id = %s
                    """,
                    (player_id,),
                )
                balance = Decimal(str(cursor.fetchone()[0]))
        return {
            "player_id": row[0],
            "email": row[1],
            "player_tier": int(row[2]),
            "effective_hashrate": str(row[3]),
            "balance": str(balance.quantize(Decimal("0.000001"))),
        }

    def reset_player_balance(self, *, player_id: str, amount: Decimal, admin_id: str, reason: str) -> None:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    "SELECT COALESCE(SUM(amount), 0) FROM economy_player_ledger_entries WHERE player_id = %s",
                    (player_id,),
                )
                previous_balance = Decimal(str(cursor.fetchone()[0]))
                delta = amount - previous_balance
                cursor.execute(
                    """
                    INSERT INTO economy_player_ledger_entries (
                        ledger_entry_id, block_number, player_id, amount, contribution_hashes, currency, entry_type, metadata
                    )
                    VALUES (%s, NULL, %s, %s, 0, 'credits', 'admin.balance_reset.v1', %s::jsonb)
                    """,
                    (uuid4(), player_id, delta, json.dumps({"reason": reason, "admin_id": admin_id})),
                )
                self._insert_audit_log(
                    cursor=cursor,
                    admin_id=admin_id,
                    action_type="admin.player.reset_balance",
                    resource_id=player_id,
                    old_value={"balance": str(previous_balance)},
                    new_value={"balance": str(amount)},
                    reason=reason,
                    twofa_verified=True,
                    ip_address="",
                    user_agent="",
                )
            connection.commit()

    def cancel_event(self, *, event_id: str, reason: str, admin_id: str) -> None:
        self._event_service.cancel_event(event_id, reason)
        if not database_is_configured():
            return
        with open_connection() as connection:
            with connection.cursor() as cursor:
                self._insert_audit_log(
                    cursor=cursor,
                    admin_id=admin_id,
                    action_type="admin.event.cancel",
                    resource_id=event_id,
                    old_value=None,
                    new_value={"status": "cancelled", "reason": reason},
                    reason=reason,
                    twofa_verified=True,
                    ip_address="",
                    user_agent="",
                )
            connection.commit()

    def set_emergency_control(self, *, key: str, enabled: bool, admin_id: str, reason: str) -> None:
        if key not in self._maintenance_state:
            raise ValueError("unknown_control")
        previous = self._maintenance_state[key]
        self._maintenance_state[key] = bool(enabled)
        if not database_is_configured():
            return
        with open_connection() as connection:
            with connection.cursor() as cursor:
                self._insert_audit_log(
                    cursor=cursor,
                    admin_id=admin_id,
                    action_type=f"admin.emergency.{key}",
                    resource_id=key,
                    old_value={"enabled": previous},
                    new_value={"enabled": enabled},
                    reason=reason,
                    twofa_verified=True,
                    ip_address="",
                    user_agent="",
                )
            connection.commit()

    def get_audit_log(self, *, limit: int = 100, offset: int = 0) -> list[dict[str, object]]:
        if not database_is_configured():
            return []
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT audit_id, admin_id, action_type, resource_id, old_value, new_value, reason, twofa_verified, created_at
                    FROM admin_audit_log
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (min(max(limit, 1), 500), max(offset, 0)),
                )
                rows = cursor.fetchall()
        return [
            {
                "audit_id": int(row[0]),
                "admin_id": row[1],
                "action_type": row[2],
                "resource_id": row[3],
                "old_value": row[4],
                "new_value": row[5],
                "reason": row[6],
                "twofa_verified": bool(row[7]),
                "created_at": row[8].astimezone(UTC).isoformat(),
            }
            for row in rows
        ]

    @staticmethod
    def _insert_audit_log(
        *,
        cursor: object,
        admin_id: str,
        action_type: str,
        resource_id: str,
        old_value: object,
        new_value: object,
        reason: str,
        twofa_verified: bool,
        ip_address: str,
        user_agent: str,
    ) -> None:
        cursor.execute(
            """
            INSERT INTO admin_audit_log (
                admin_id, action_type, resource_id, old_value, new_value, reason, twofa_verified, created_at, ip_address, user_agent
            )
            VALUES (%s, %s, %s, %s::jsonb, %s::jsonb, %s, %s, %s, %s, %s)
            """,
            (
                admin_id,
                action_type,
                resource_id,
                json.dumps(old_value) if old_value is not None else None,
                json.dumps(new_value) if new_value is not None else None,
                reason,
                twofa_verified,
                datetime.now(UTC),
                ip_address,
                user_agent,
            ),
        )
