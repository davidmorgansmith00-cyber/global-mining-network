from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from shared.database import database_is_configured, open_connection


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ModerationAction:
    action_id: str
    player_id: str
    action_type: str
    reason: str
    duration_seconds: int | None
    taken_by_staff_id: str
    created_at: datetime
    expires_at: datetime | None
    source_ticket_id: str | None


@dataclass(frozen=True)
class ModerationAppeal:
    appeal_id: str
    player_id: str
    moderation_action_id: str
    appeal_reason: str
    appeal_evidence: dict | None
    status: str
    reviewed_by_staff_id: str | None
    reviewed_at: datetime | None
    denial_reason: str | None
    created_at: datetime


@dataclass(frozen=True)
class ModeratorStats:
    actions_taken: int
    appeals_reviewed: int
    queue_depth: int


# ---------------------------------------------------------------------------
# Graduated enforcement defaults (overridden by DB config table)
# ---------------------------------------------------------------------------
_DEFAULT_ESCALATION: dict[str, list[tuple[str, int | None]]] = {
    "harassment": [("warning", None), ("mute", 86400), ("suspend", 604800)],
    "exploit":    [("warning", None), ("suspend", 604800)],
    "spam":       [("warning", None), ("mute", 86400), ("suspend", 604800)],
    "cheat":      [("suspend", 2592000)],
}


class ModerationService:
    """Server-authoritative moderation workflow service."""

    # ------------------------------------------------------------------
    def take_moderation_action(
        self,
        player_id: str,
        action_type: str,
        reason: str,
        staff_id: str,
        duration_seconds: int | None = None,
        source_ticket_id: str | None = None,
    ) -> str:
        action_id = str(uuid.uuid4())
        expires_at: datetime | None = None
        if duration_seconds is not None:
            expires_at = datetime.now(UTC) + timedelta(seconds=duration_seconds)

        if not database_is_configured():
            return action_id

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO moderation_actions
                        (action_id, player_id, action_type, reason, duration_seconds,
                         taken_by_staff_id, expires_at, source_ticket_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        action_id, player_id, action_type, reason,
                        duration_seconds, staff_id, expires_at, source_ticket_id,
                    ),
                )
            conn.commit()
        return action_id

    # ------------------------------------------------------------------
    def queue_for_review(
        self,
        report_ticket_id: str,
        auto_suggested_action: str,
        player_id: str,
    ) -> bool:
        """Insert a sentinel 'escalate' action to represent a pending queue item."""
        if not database_is_configured():
            return True

        self.take_moderation_action(
            player_id=player_id,
            action_type="escalate",
            reason=f"auto-queued from ticket {report_ticket_id}: suggested={auto_suggested_action}",
            staff_id="system",
            source_ticket_id=report_ticket_id,
        )
        return True

    # ------------------------------------------------------------------
    def submit_appeal(
        self,
        player_id: str,
        moderation_action_id: str,
        appeal_reason: str,
        evidence_json: dict | None = None,
    ) -> str:
        import json

        appeal_id = str(uuid.uuid4())
        if not database_is_configured():
            return appeal_id

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO moderation_appeals
                        (appeal_id, player_id, moderation_action_id, appeal_reason, appeal_evidence)
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        appeal_id, player_id, moderation_action_id,
                        appeal_reason,
                        json.dumps(evidence_json) if evidence_json else None,
                    ),
                )
            conn.commit()
        return appeal_id

    # ------------------------------------------------------------------
    def review_appeal(
        self,
        appeal_id: str,
        approved: bool,
        staff_id: str,
        denial_reason: str | None = None,
    ) -> str:
        outcome = "approved" if approved else "denied"
        if not database_is_configured():
            return outcome

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE moderation_appeals
                    SET status = %s, reviewed_by_staff_id = %s,
                        reviewed_at = NOW(), denial_reason = %s
                    WHERE appeal_id = %s
                    """,
                    (outcome, staff_id, denial_reason, appeal_id),
                )
                if approved:
                    # Look up the action and mark it expired immediately
                    cur.execute(
                        """
                        UPDATE moderation_actions ma
                        SET expires_at = NOW()
                        FROM moderation_appeals apr
                        WHERE apr.appeal_id = %s
                          AND ma.action_id = apr.moderation_action_id
                        """,
                        (appeal_id,),
                    )
            conn.commit()
        return outcome

    # ------------------------------------------------------------------
    def get_moderation_queue(
        self, sort_by: str = "priority", limit: int = 50
    ) -> list[ModerationAction]:
        if not database_is_configured():
            return []

        order = "created_at ASC"
        if sort_by == "priority":
            order = "CASE action_type WHEN 'suspend' THEN 1 WHEN 'mute' THEN 2 WHEN 'warning' THEN 3 ELSE 4 END, created_at ASC"

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT action_id, player_id, action_type, reason, duration_seconds,
                           taken_by_staff_id, created_at, expires_at, source_ticket_id
                    FROM moderation_actions
                    WHERE action_type = 'escalate' OR (expires_at IS NULL OR expires_at > NOW())
                    ORDER BY {order} LIMIT %s
                    """,
                    (limit,),
                )
                rows = cur.fetchall()
        return [ModerationAction(*r) for r in rows]

    # ------------------------------------------------------------------
    def get_player_history(self, player_id: str) -> list[ModerationAction]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT action_id, player_id, action_type, reason, duration_seconds,
                           taken_by_staff_id, created_at, expires_at, source_ticket_id
                    FROM moderation_actions WHERE player_id = %s ORDER BY created_at DESC
                    """,
                    (player_id,),
                )
                rows = cur.fetchall()
        return [ModerationAction(*r) for r in rows]

    # ------------------------------------------------------------------
    def get_appeals(self, status_filter: str | None = None, limit: int = 50) -> list[ModerationAppeal]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                if status_filter:
                    cur.execute(
                        """
                        SELECT appeal_id, player_id, moderation_action_id, appeal_reason,
                               appeal_evidence, status, reviewed_by_staff_id, reviewed_at,
                               denial_reason, created_at
                        FROM moderation_appeals WHERE status = %s
                        ORDER BY created_at DESC LIMIT %s
                        """,
                        (status_filter, limit),
                    )
                else:
                    cur.execute(
                        """
                        SELECT appeal_id, player_id, moderation_action_id, appeal_reason,
                               appeal_evidence, status, reviewed_by_staff_id, reviewed_at,
                               denial_reason, created_at
                        FROM moderation_appeals
                        ORDER BY created_at DESC LIMIT %s
                        """,
                        (limit,),
                    )
                rows = cur.fetchall()
        return [ModerationAppeal(*r) for r in rows]

    # ------------------------------------------------------------------
    def get_moderator_stats(
        self,
        staff_id: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> ModeratorStats:
        if not database_is_configured():
            return ModeratorStats(0, 0, 0)

        params_a: list[Any] = []
        conditions_a = []
        if staff_id:
            conditions_a.append("taken_by_staff_id = %s")
            params_a.append(staff_id)
        if date_from:
            conditions_a.append("created_at >= %s")
            params_a.append(date_from)
        if date_to:
            conditions_a.append("created_at <= %s")
            params_a.append(date_to)
        where_a = ("WHERE " + " AND ".join(conditions_a)) if conditions_a else ""

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"SELECT COUNT(*) FROM moderation_actions {where_a}", params_a
                )
                actions_taken = int(cur.fetchone()[0])

                params_r: list[Any] = []
                conditions_r = ["reviewed_at IS NOT NULL"]
                if staff_id:
                    conditions_r.append("reviewed_by_staff_id = %s")
                    params_r.append(staff_id)
                if date_from:
                    conditions_r.append("reviewed_at >= %s")
                    params_r.append(date_from)
                if date_to:
                    conditions_r.append("reviewed_at <= %s")
                    params_r.append(date_to)
                where_r = "WHERE " + " AND ".join(conditions_r)
                cur.execute(
                    f"SELECT COUNT(*) FROM moderation_appeals {where_r}", params_r
                )
                appeals_reviewed = int(cur.fetchone()[0])

                cur.execute(
                    "SELECT COUNT(*) FROM moderation_actions WHERE action_type = 'escalate'"
                )
                queue_depth = int(cur.fetchone()[0])

        return ModeratorStats(actions_taken, appeals_reviewed, queue_depth)

    # ------------------------------------------------------------------
    def determine_graduated_action(
        self, player_id: str, offense_type: str
    ) -> tuple[str, int | None]:
        """Return (action_type, duration_seconds) for next offense escalation step."""
        if not database_is_configured():
            steps = _DEFAULT_ESCALATION.get(offense_type, [("warning", None)])
            return steps[0]

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT count FROM moderation_offense_history WHERE player_id = %s AND offense_type = %s",
                    (player_id, offense_type),
                )
                row = cur.fetchone()
                offense_count = int(row[0]) if row else 0

                cur.execute(
                    "SELECT warning_count, mute_count, suspend_count, suspend_duration_seconds FROM moderation_offense_escalation WHERE offense_type = %s",
                    (offense_type,),
                )
                config_row = cur.fetchone()

        steps = _DEFAULT_ESCALATION.get(offense_type, [("warning", None)])
        if config_row:
            warning_count, mute_count, suspend_count, suspend_duration = config_row
            steps = []
            steps.extend([("warning", None)] * int(warning_count))
            steps.extend([("mute", 86400)] * int(mute_count))
            steps.extend([("suspend", int(suspend_duration))] * int(suspend_count))

        idx = min(offense_count, len(steps) - 1)
        return steps[idx]
