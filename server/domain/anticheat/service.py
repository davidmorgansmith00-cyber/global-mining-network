from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json

from shared.database import database_is_configured, open_connection


ACTION_MONITOR = "MONITOR"
ACTION_WARNING = "WARNING"
ACTION_MUTE_24H = "MUTE_24H"
ACTION_SUSPEND = "SUSPEND"

PURCHASES_PER_HOUR_THRESHOLD = 20
BALANCE_CHANGES_PER_DAY_THRESHOLD = 100
WEALTH_SPIKE_MULTIPLIER = 5
SCORE_SUSPEND = 100
SCORE_MUTE = 50
SCORE_WARNING = 20
_CREDIT_LEDGER_ENTRY_TYPES = (
    "block.finalized.player_reward.v1",
    "market.purchase.v1",
    "hardware.upgrade.v1",
    "player.equipment_trade.v1",
    "pool.reward_distribution.v1",
)
_PURCHASE_ENTRY_TYPES = ("market.purchase.v1", "player.equipment_trade.v1")


@dataclass(frozen=True)
class AnomalyCheckResult:
    player_id: str
    total_score: int
    rate_score: int
    state_score: int
    wealth_score: int
    action: str
    reasons: list[str]


@dataclass(frozen=True)
class AntiCheatAction:
    action_id: str
    player_id: str
    action_type: str
    reason: str
    anomaly_score: int
    evidence_json: dict
    created_at: datetime
    expires_at: datetime | None
    appeal_status: str | None


class AntiCheatService:
    def check_rate_limits(self, player_id: str, event_type: str) -> bool:
        if not database_is_configured():
            return True

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                if event_type == "purchase":
                    hour_ago = now - timedelta(hours=1)
                    cur.execute(
                        """
                        SELECT COUNT(*)
                        FROM economy_player_ledger_entries
                        WHERE player_id = %s
                          AND entry_type = ANY(%s)
                          AND created_at >= %s
                        """,
                        (player_id, list(_PURCHASE_ENTRY_TYPES), hour_ago),
                    )
                    count = int(cur.fetchone()[0])
                    return count <= PURCHASES_PER_HOUR_THRESHOLD
                return True

    def check_impossible_states(self, player_id: str) -> list[str]:
        if not database_is_configured():
            return []

        anomalies: list[str] = []
        with open_connection() as conn:
            with conn.cursor() as cur:
                if self._get_player_credit_balance(cur, player_id) < Decimal("0"):
                    anomalies.append("negative_balance")
        return anomalies

    def calculate_anomaly_score(
        self,
        player_id: str,
        event_type: str,
        event_data: dict,
    ) -> AnomalyCheckResult:
        del event_type, event_data

        if not database_is_configured():
            return AnomalyCheckResult(
                player_id=player_id,
                total_score=0,
                rate_score=0,
                state_score=0,
                wealth_score=0,
                action=ACTION_MONITOR,
                reasons=[],
            )

        rate_score = 0
        state_score = 0
        wealth_score = 0
        reasons: list[str] = []
        now = datetime.now(tz=UTC)

        with open_connection() as conn:
            with conn.cursor() as cur:
                hour_ago = now - timedelta(hours=1)
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM economy_player_ledger_entries
                    WHERE player_id = %s
                      AND entry_type = ANY(%s)
                      AND created_at >= %s
                    """,
                    (player_id, list(_PURCHASE_ENTRY_TYPES), hour_ago),
                )
                purchases_per_hour = int(cur.fetchone()[0])
                if purchases_per_hour > PURCHASES_PER_HOUR_THRESHOLD:
                    rate_score += 50
                    reasons.append(f"purchases_per_hour:{purchases_per_hour}")

                day_ago = now - timedelta(days=1)
                cur.execute(
                    """
                    SELECT COUNT(*)
                    FROM economy_player_ledger_entries
                    WHERE player_id = %s
                      AND created_at >= %s
                    """,
                    (player_id, day_ago),
                )
                balance_changes_per_day = int(cur.fetchone()[0])
                if balance_changes_per_day > BALANCE_CHANGES_PER_DAY_THRESHOLD:
                    rate_score += 30
                    reasons.append(f"balance_changes_per_day:{balance_changes_per_day}")

                balance = self._get_player_credit_balance(cur, player_id)
                if balance < Decimal("0"):
                    state_score += 100
                    reasons.append("negative_balance")

                thirty_days_ago = now - timedelta(days=30)
                cur.execute(
                    """
                    SELECT COALESCE(AVG(daily_total), 0)
                    FROM (
                        SELECT DATE(created_at) AS day, SUM(GREATEST(amount, 0)) AS daily_total
                        FROM economy_player_ledger_entries
                        WHERE player_id = %s
                          AND created_at >= %s
                          AND created_at < NOW() - INTERVAL '1 day'
                          AND amount > 0
                        GROUP BY day
                    ) daily
                    """,
                    (player_id, thirty_days_ago),
                )
                avg_daily = Decimal(str(cur.fetchone()[0]))
                cur.execute(
                    """
                    SELECT COALESCE(SUM(GREATEST(amount, 0)), 0)
                    FROM economy_player_ledger_entries
                    WHERE player_id = %s
                      AND created_at >= NOW() - INTERVAL '1 day'
                      AND amount > 0
                    """,
                    (player_id,),
                )
                today_earnings = Decimal(str(cur.fetchone()[0]))
                if avg_daily > Decimal("0") and today_earnings > avg_daily * WEALTH_SPIKE_MULTIPLIER:
                    wealth_score += 40
                    reasons.append(f"wealth_spike:{today_earnings}>{avg_daily * WEALTH_SPIKE_MULTIPLIER}")

        total_score = rate_score + state_score + wealth_score
        return AnomalyCheckResult(
            player_id=player_id,
            total_score=total_score,
            rate_score=rate_score,
            state_score=state_score,
            wealth_score=wealth_score,
            action=self.determine_action(total_score),
            reasons=reasons,
        )

    def enforce_action(
        self,
        player_id: str,
        action: str,
        reason: str,
        evidence: dict,
    ) -> str:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        expires_at = now + timedelta(hours=24) if action == ACTION_MUTE_24H else None
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO anti_cheat_actions
                        (player_id, action_type, reason, anomaly_score, evidence_json, created_at, expires_at)
                    VALUES (%s, %s, %s, %s, %s::jsonb, %s, %s)
                    RETURNING action_id::text
                    """,
                    (
                        player_id,
                        action,
                        reason,
                        int(evidence.get("total_score", 0)),
                        json.dumps(evidence),
                        now,
                        expires_at,
                    ),
                )
                action_id = str(cur.fetchone()[0])
                cur.execute(
                    """
                    INSERT INTO anti_cheat_events
                        (player_id, event_type, check_passed, anomaly_score, created_at)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (player_id, action, action == ACTION_MONITOR, int(evidence.get("total_score", 0)), now),
                )
            conn.commit()
        return action_id

    def appeal_action(self, player_id: str, action_id: str, appeal_reason: str) -> str:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE anti_cheat_actions
                    SET appealed_at = %s,
                        appeal_status = 'pending',
                        evidence_json = evidence_json || jsonb_build_object('appeal_reason', %s::text)
                    WHERE action_id = %s
                      AND player_id = %s
                      AND appeal_status IS NULL
                    RETURNING appeal_status
                    """,
                    (now, appeal_reason, action_id, player_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("action_not_found_or_already_appealed")
            conn.commit()
        return str(row[0])

    def get_active_actions(self, player_id: str) -> list[AntiCheatAction]:
        if not database_is_configured():
            return []

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT action_id::text, player_id, action_type, reason,
                           anomaly_score, evidence_json, created_at, expires_at, appeal_status
                    FROM anti_cheat_actions
                    WHERE player_id = %s
                      AND (expires_at IS NULL OR expires_at > %s)
                      AND (appeal_status IS NULL OR appeal_status = 'pending')
                    ORDER BY created_at DESC
                    """,
                    (player_id, now),
                )
                rows = cur.fetchall()
        return [
            AntiCheatAction(
                action_id=row[0],
                player_id=row[1],
                action_type=row[2],
                reason=row[3],
                anomaly_score=int(row[4]),
                evidence_json=row[5] if isinstance(row[5], dict) else {},
                created_at=row[6],
                expires_at=row[7],
                appeal_status=row[8],
            )
            for row in rows
        ]

    @staticmethod
    def determine_action(total_score: int) -> str:
        if total_score >= SCORE_SUSPEND:
            return ACTION_SUSPEND
        if total_score >= SCORE_MUTE:
            return ACTION_MUTE_24H
        if total_score >= SCORE_WARNING:
            return ACTION_WARNING
        return ACTION_MONITOR

    @staticmethod
    def _get_player_credit_balance(cursor: object, player_id: str) -> Decimal:
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM economy_player_ledger_entries
            WHERE player_id = %s
              AND currency = 'credits'
              AND entry_type = ANY(%s)
            """,
            (player_id, list(_CREDIT_LEDGER_ENTRY_TYPES)),
        )
        row = cursor.fetchone()
        return Decimal("0") if row is None or row[0] is None else Decimal(str(row[0]))
