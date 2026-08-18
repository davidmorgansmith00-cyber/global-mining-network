from __future__ import annotations

import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from shared.database import database_is_configured, open_connection


# ---------------------------------------------------------------------------
# Automated categorisation keywords
# ---------------------------------------------------------------------------
_CATEGORY_KEYWORDS: list[tuple[str, str, str]] = [
    (r"\b(crash|error|freeze)\b", "bug", "critical"),
    (r"\b(exploit|farming|dupe|infinite)\b", "exploit", "critical"),
    (r"\b(offensive|harassment|spam)\b", "player_behavior", "high"),
    (r"\b(asset missing|texture|display)\b", "content", "medium"),
]


def _auto_categorise(title: str, description: str) -> tuple[str, str]:
    """Return (category, priority) based on keyword matching."""
    text = (title + " " + description).lower()
    for pattern, category, priority in _CATEGORY_KEYWORDS:
        if re.search(pattern, text):
            return category, priority
    return "bug", "medium"


# ---------------------------------------------------------------------------
# Domain models
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class SupportTicket:
    ticket_id: str
    player_id: str
    category: str
    title: str
    description: str
    priority: str
    status: str
    created_at: datetime
    first_response_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    resolution_reason: str | None


@dataclass(frozen=True)
class TicketMessage:
    message_id: str
    ticket_id: str
    from_role: str
    message_text: str
    created_at: datetime


@dataclass(frozen=True)
class SlaMetrics:
    avg_first_response_seconds: float | None
    avg_resolution_seconds: float | None
    total_tickets: int
    open_tickets: int


class SupportService:
    """Server-authoritative support ticket service."""

    # ------------------------------------------------------------------
    def create_ticket(
        self,
        player_id: str,
        title: str,
        description: str,
        category: str | None = None,
        screenshot_b64: str | None = None,
        logs_b64: str | None = None,
        player_state: dict | None = None,
        environment_info: dict | None = None,
    ) -> str:
        ticket_id = str(uuid.uuid4())
        auto_cat, auto_pri = _auto_categorise(title, description)
        if category is None:
            category = auto_cat

        # Determine priority from category if possible
        for pattern, cat, pri in _CATEGORY_KEYWORDS:
            if cat == category and re.search(pattern, (title + " " + description).lower()):
                auto_pri = pri
                break

        if not database_is_configured():
            return ticket_id

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO support_tickets
                        (ticket_id, player_id, category, title, description, priority, status)
                    VALUES (%s, %s, %s, %s, %s, %s, 'open')
                    """,
                    (ticket_id, player_id, category, title, description, auto_pri),
                )

                # capture evidence snapshot
                if player_state is not None or environment_info is not None:
                    import json

                    cur.execute(
                        """
                        INSERT INTO support_ticket_evidence
                            (evidence_id, ticket_id, player_state_snapshot_json, environment_info_json)
                        VALUES (%s, %s, %s, %s)
                        """,
                        (
                            str(uuid.uuid4()),
                            ticket_id,
                            json.dumps(player_state or {}),
                            json.dumps(environment_info or {}),
                        ),
                    )

            conn.commit()
        return ticket_id

    # ------------------------------------------------------------------
    def add_message(self, ticket_id: str, from_role: str, message_text: str) -> str:
        message_id = str(uuid.uuid4())
        if not database_is_configured():
            return message_id

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO support_ticket_messages (message_id, ticket_id, from_role, message_text)
                    VALUES (%s, %s, %s, %s)
                    """,
                    (message_id, ticket_id, from_role, message_text),
                )
                # Record first_response_at for staff replies
                if from_role == "staff":
                    cur.execute(
                        """
                        UPDATE support_tickets
                        SET first_response_at = COALESCE(first_response_at, NOW())
                        WHERE ticket_id = %s
                        """,
                        (ticket_id,),
                    )
            conn.commit()
        return message_id

    # ------------------------------------------------------------------
    def update_ticket_status(self, ticket_id: str, status: str, staff_id: str) -> str:
        valid = {"open", "in_progress", "resolved", "closed"}
        if status not in valid:
            raise ValueError(f"Invalid status: {status}")

        if not database_is_configured():
            return status

        with open_connection() as conn:
            with conn.cursor() as cur:
                extra_sql = ""
                if status == "resolved":
                    extra_sql = ", resolved_at = NOW()"
                elif status == "closed":
                    extra_sql = ", closed_at = NOW()"
                cur.execute(
                    f"UPDATE support_tickets SET status = %s{extra_sql} WHERE ticket_id = %s",
                    (status, ticket_id),
                )
            conn.commit()
        return status

    # ------------------------------------------------------------------
    def close_ticket(self, ticket_id: str, resolution_reason: str, staff_id: str) -> bool:
        if not database_is_configured():
            return True

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE support_tickets
                    SET status = 'closed', closed_at = NOW(), resolution_reason = %s
                    WHERE ticket_id = %s
                    """,
                    (resolution_reason, ticket_id),
                )
            conn.commit()
        return True

    # ------------------------------------------------------------------
    def get_ticket(self, ticket_id: str) -> SupportTicket | None:
        if not database_is_configured():
            return None

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT ticket_id, player_id, category, title, description,
                           priority, status, created_at, first_response_at,
                           resolved_at, closed_at, resolution_reason
                    FROM support_tickets WHERE ticket_id = %s
                    """,
                    (ticket_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return SupportTicket(*row)

    # ------------------------------------------------------------------
    def get_ticket_messages(self, ticket_id: str) -> list[TicketMessage]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT message_id, ticket_id, from_role, message_text, created_at
                    FROM support_ticket_messages
                    WHERE ticket_id = %s ORDER BY created_at
                    """,
                    (ticket_id,),
                )
                rows = cur.fetchall()
        return [TicketMessage(*r) for r in rows]

    # ------------------------------------------------------------------
    def search_tickets(
        self,
        player_id: str | None = None,
        category: str | None = None,
        status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[SupportTicket]:
        if not database_is_configured():
            return []

        conditions = []
        params: list[Any] = []
        if player_id:
            conditions.append("player_id = %s")
            params.append(player_id)
        if category:
            conditions.append("category = %s")
            params.append(category)
        if status:
            conditions.append("status = %s")
            params.append(status)
        if date_from:
            conditions.append("created_at >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= %s")
            params.append(date_to)

        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""
        params += [limit, offset]

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT ticket_id, player_id, category, title, description,
                           priority, status, created_at, first_response_at,
                           resolved_at, closed_at, resolution_reason
                    FROM support_tickets {where}
                    ORDER BY created_at DESC LIMIT %s OFFSET %s
                    """,
                    params,
                )
                rows = cur.fetchall()
        return [SupportTicket(*r) for r in rows]

    # ------------------------------------------------------------------
    def get_ticket_sla_metrics(
        self,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> SlaMetrics:
        if not database_is_configured():
            return SlaMetrics(None, None, 0, 0)

        conditions = []
        params: list[Any] = []
        if date_from:
            conditions.append("created_at >= %s")
            params.append(date_from)
        if date_to:
            conditions.append("created_at <= %s")
            params.append(date_to)
        where = ("WHERE " + " AND ".join(conditions)) if conditions else ""

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT
                        AVG(EXTRACT(EPOCH FROM (first_response_at - created_at))),
                        AVG(EXTRACT(EPOCH FROM (resolved_at - created_at))),
                        COUNT(*),
                        SUM(CASE WHEN status IN ('open', 'in_progress') THEN 1 ELSE 0 END)
                    FROM support_tickets {where}
                    """,
                    params,
                )
                row = cur.fetchone()

        avg_first = float(row[0]) if row[0] is not None else None
        avg_res = float(row[1]) if row[1] is not None else None
        total = int(row[2]) if row[2] else 0
        open_count = int(row[3]) if row[3] else 0
        return SlaMetrics(avg_first, avg_res, total, open_count)
