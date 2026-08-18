from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import json
from uuid import UUID, uuid4

from domain.blockchain.network_stream import NetworkEventStream, get_network_event_stream
from shared.database import database_is_configured, open_connection


EVENT_LOG_MODIFIER_APPLIED = "event.modifier_applied.v1"
EVENT_LOG_BRANCH_RESOLVED = "event.branch_resolved.v1"
EVENT_LOG_CANCELLED = "event.cancelled.v1"


@dataclass(frozen=True)
class EventRecord:
    event_id: str
    event_name: str
    event_type: str
    start_at: datetime
    end_at: datetime
    modifier_type: str | None
    modifier_value: Decimal | None
    rollout_stage: str
    status: str


class EventService:
    def __init__(self, *, network_event_stream: NetworkEventStream | None = None) -> None:
        self._network_event_stream = network_event_stream or get_network_event_stream()
        self._memory_events: dict[str, EventRecord] = {}
        self._memory_branches: dict[str, dict[str, Decimal]] = {}
        self._memory_scores: dict[str, dict[str, Decimal]] = {}

    def create_event(
        self,
        *,
        name: str,
        type: str,
        start_at: datetime,
        end_at: datetime,
        modifier_type: str | None,
        modifier_value: Decimal | None,
    ) -> str:
        event_id = str(uuid4())
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO game_events (
                            event_id, event_name, event_type, start_at, end_at,
                            modifier_type, modifier_value, rollout_stage, status
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, 'internal', 'scheduled')
                        """,
                        (
                            event_id,
                            name,
                            type,
                            start_at.astimezone(UTC),
                            end_at.astimezone(UTC),
                            modifier_type,
                            modifier_value,
                        ),
                    )
                connection.commit()
            return event_id

        self._memory_events[event_id] = EventRecord(
            event_id=event_id,
            event_name=name,
            event_type=type,
            start_at=start_at.astimezone(UTC),
            end_at=end_at.astimezone(UTC),
            modifier_type=modifier_type,
            modifier_value=modifier_value,
            rollout_stage="internal",
            status="scheduled",
        )
        return event_id

    def activate_event(self, event_id: str, rollout_stage: str) -> None:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE game_events
                        SET status = 'active', rollout_stage = %s, updated_at = NOW()
                        WHERE event_id = %s
                        """,
                        (rollout_stage, event_id),
                    )
                    cursor.execute(
                        """
                        INSERT INTO event_balance_snapshots (event_id, player_id, balance_before)
                        SELECT %s, player_id, COALESCE(SUM(amount), 0)
                        FROM economy_player_ledger_entries
                        WHERE currency = 'credits'
                        GROUP BY player_id
                        ON CONFLICT (event_id, player_id) DO NOTHING
                        """,
                        (event_id,),
                    )
                connection.commit()
            return

        event = self._memory_events[event_id]
        self._memory_events[event_id] = EventRecord(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type,
            start_at=event.start_at,
            end_at=event.end_at,
            modifier_type=event.modifier_type,
            modifier_value=event.modifier_value,
            rollout_stage=rollout_stage,
            status="active",
        )

    def create_fork_event_branch(self, event_id: str, branch_name: str) -> str:
        branch_id = str(uuid4())
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        INSERT INTO fork_event_branches (branch_id, event_id, branch_name, accumulated_work)
                        VALUES (%s, %s, %s, 0)
                        """,
                        (branch_id, event_id, branch_name),
                    )
                connection.commit()
            return branch_id

        branches = self._memory_branches.setdefault(event_id, {})
        branches[branch_id] = Decimal("0")
        return branch_id

    def record_branch_contribution(self, branch_id: str, player_id: str, work_contributed: Decimal) -> None:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE fork_event_branches
                        SET accumulated_work = accumulated_work + %s
                        WHERE branch_id = %s
                        RETURNING event_id
                        """,
                        (work_contributed, branch_id),
                    )
                    row = cursor.fetchone()
                    if row is None:
                        raise KeyError("unknown_branch")
                    event_id = str(row[0])
                    cursor.execute(
                        """
                        INSERT INTO event_leaderboard (event_id, player_id, event_contribution_score, updated_at)
                        VALUES (%s, %s, %s, NOW())
                        ON CONFLICT (event_id, player_id)
                        DO UPDATE SET event_contribution_score = event_leaderboard.event_contribution_score + EXCLUDED.event_contribution_score,
                                      updated_at = NOW()
                        """,
                        (event_id, player_id, work_contributed),
                    )
                connection.commit()
            return

        for event_id, branches in self._memory_branches.items():
            if branch_id in branches:
                branches[branch_id] = branches[branch_id] + work_contributed
                score_board = self._memory_scores.setdefault(event_id, {})
                score_board[player_id] = score_board.get(player_id, Decimal("0")) + work_contributed
                return
        raise KeyError("unknown_branch")

    def resolve_fork_event(self, event_id: str) -> dict[str, str]:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT branch_id::text, branch_name, accumulated_work
                        FROM fork_event_branches
                        WHERE event_id = %s
                        ORDER BY accumulated_work DESC, branch_name ASC
                        """,
                        (event_id,),
                    )
                    branches = cursor.fetchall()
                    if len(branches) < 2:
                        raise ValueError("fork_event_requires_two_branches")
                    winner = branches[0]
                    winner_id = winner[0]

                    cursor.execute(
                        """
                        UPDATE fork_event_branches
                        SET winning_branch = (branch_id::text = %s),
                            resolved_at = NOW(),
                            archived_at = CASE WHEN branch_id::text = %s THEN NULL ELSE NOW() END
                        WHERE event_id = %s
                        """,
                        (winner_id, winner_id, event_id),
                    )
                    cursor.execute(
                        """
                        UPDATE game_events
                        SET status = 'completed', updated_at = NOW()
                        WHERE event_id = %s
                        """,
                        (event_id,),
                    )
                    cursor.execute(
                        """
                        WITH ranked AS (
                            SELECT player_id, event_contribution_score,
                                   ROW_NUMBER() OVER (ORDER BY event_contribution_score DESC, player_id ASC) AS computed_rank
                            FROM event_leaderboard
                            WHERE event_id = %s
                        )
                        UPDATE event_leaderboard el
                        SET rank = ranked.computed_rank,
                            updated_at = NOW()
                        FROM ranked
                        WHERE el.event_id = %s AND el.player_id = ranked.player_id
                        """,
                        (event_id, event_id),
                    )
                    cursor.execute(
                        """
                        INSERT INTO event_rewards (event_id, player_id, reward_type, reward_data)
                        SELECT %s, player_id, 'event_bonus',
                               jsonb_build_object('title', 'Fork Victor', 'placement', rank)
                        FROM event_leaderboard
                        WHERE event_id = %s
                          AND rank IS NOT NULL
                          AND rank <= 10
                        ORDER BY rank ASC
                        """,
                        (event_id, event_id),
                    )
                connection.commit()
            self._network_event_stream.publish(
                event_type=EVENT_LOG_BRANCH_RESOLVED,
                payload={"event_id": event_id, "winning_branch_id": winner_id},
            )
            return {"event_id": event_id, "winning_branch_id": winner_id}

        branches = self._memory_branches.get(event_id, {})
        if len(branches) < 2:
            raise ValueError("fork_event_requires_two_branches")
        winner_id = sorted(branches.items(), key=lambda item: (-item[1], item[0]))[0][0]
        self._network_event_stream.publish(
            event_type=EVENT_LOG_BRANCH_RESOLVED,
            payload={"event_id": event_id, "winning_branch_id": winner_id},
        )
        return {"event_id": event_id, "winning_branch_id": winner_id}

    def cancel_event(self, event_id: str, reason: str) -> None:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT s.player_id, s.balance_before, COALESCE(curr.balance_now, 0)
                        FROM event_balance_snapshots s
                        LEFT JOIN (
                            SELECT player_id, SUM(amount) AS balance_now
                            FROM economy_player_ledger_entries
                            WHERE currency = 'credits'
                            GROUP BY player_id
                        ) curr ON curr.player_id = s.player_id
                        WHERE s.event_id = %s
                        """,
                        (event_id,),
                    )
                    rows = cursor.fetchall()
                    for row in rows:
                        player_id, balance_before, balance_now = row[0], Decimal(str(row[1])), Decimal(str(row[2]))
                        delta = balance_before - balance_now
                        if delta == 0:
                            continue
                        cursor.execute(
                            """
                            INSERT INTO economy_player_ledger_entries (
                                ledger_entry_id, block_number, player_id, amount, contribution_hashes, currency, entry_type, metadata
                            )
                            VALUES (%s, NULL, %s, %s, 0, 'credits', 'event.rollback.balance_adjustment.v1', %s::jsonb)
                            """,
                            (
                                uuid4(),
                                player_id,
                                delta,
                                json.dumps({"event_id": event_id, "reason": reason}),
                            ),
                        )
                    cursor.execute(
                        """
                        UPDATE game_events
                        SET status = 'cancelled', cancelled_reason = %s, updated_at = NOW()
                        WHERE event_id = %s
                        """,
                        (reason, event_id),
                    )
                connection.commit()
            self._network_event_stream.publish(
                event_type=EVENT_LOG_CANCELLED,
                payload={"event_id": event_id, "reason": reason},
            )
            return

        event = self._memory_events[event_id]
        self._memory_events[event_id] = EventRecord(
            event_id=event.event_id,
            event_name=event.event_name,
            event_type=event.event_type,
            start_at=event.start_at,
            end_at=event.end_at,
            modifier_type=event.modifier_type,
            modifier_value=event.modifier_value,
            rollout_stage=event.rollout_stage,
            status="cancelled",
        )
        self._network_event_stream.publish(event_type=EVENT_LOG_CANCELLED, payload={"event_id": event_id, "reason": reason})

    def get_active_events(self) -> list[EventRecord]:
        now = datetime.now(UTC)
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT event_id::text, event_name, event_type, start_at, end_at, modifier_type, modifier_value, rollout_stage, status
                        FROM game_events
                        WHERE status = 'active'
                          AND start_at <= %s
                          AND end_at >= %s
                        ORDER BY end_at ASC
                        """,
                        (now, now),
                    )
                    rows = cursor.fetchall()
            return [
                EventRecord(
                    event_id=row[0],
                    event_name=row[1],
                    event_type=row[2],
                    start_at=row[3],
                    end_at=row[4],
                    modifier_type=row[5],
                    modifier_value=None if row[6] is None else Decimal(str(row[6])),
                    rollout_stage=row[7],
                    status=row[8],
                )
                for row in rows
            ]

        return [
            event
            for event in self._memory_events.values()
            if event.status == "active" and event.start_at <= now <= event.end_at
        ]

    def get_event_leaderboard(self, event_id: str, limit: int = 10) -> list[dict[str, str]]:
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        SELECT player_id, event_contribution_score, COALESCE(rank, 0)
                        FROM event_leaderboard
                        WHERE event_id = %s
                        ORDER BY event_contribution_score DESC, player_id ASC
                        LIMIT %s
                        """,
                        (event_id, limit),
                    )
                    rows = cursor.fetchall()
            return [
                {
                    "player_id": row[0],
                    "event_contribution_score": str(row[1]),
                    "rank": str(index + 1 if int(row[2]) <= 0 else row[2]),
                }
                for index, row in enumerate(rows)
            ]

        scores = self._memory_scores.get(event_id, {})
        ordered = sorted(scores.items(), key=lambda item: (-item[1], item[0]))[:limit]
        return [
            {"player_id": player_id, "event_contribution_score": str(score), "rank": str(index + 1)}
            for index, (player_id, score) in enumerate(ordered)
        ]

    def apply_reward_multiplier(self, *, base_reward: Decimal) -> Decimal:
        event = self._get_modifier_event(modifier_type="reward_multiplier")
        if event is None or event.modifier_value is None:
            return base_reward
        adjusted = (base_reward * event.modifier_value).quantize(Decimal("0.000001"))
        self._network_event_stream.publish(
            event_type=EVENT_LOG_MODIFIER_APPLIED,
            payload={
                "event_id": event.event_id,
                "modifier_type": "reward_multiplier",
                "modifier_value": str(event.modifier_value),
                "base_value": str(base_reward),
                "final_value": str(adjusted),
            },
        )
        return adjusted

    def apply_difficulty_modifier(self, *, base_required_work: Decimal) -> Decimal:
        event = self._get_modifier_event(modifier_type="difficulty_modifier")
        if event is None or event.modifier_value is None or event.modifier_value == 0:
            return base_required_work
        adjusted = (base_required_work / event.modifier_value).quantize(Decimal("0.000001"))
        self._network_event_stream.publish(
            event_type=EVENT_LOG_MODIFIER_APPLIED,
            payload={
                "event_id": event.event_id,
                "modifier_type": "difficulty_modifier",
                "modifier_value": str(event.modifier_value),
                "base_value": str(base_required_work),
                "final_value": str(adjusted),
            },
        )
        return adjusted

    def resolve_expired_fork_events(self) -> list[str]:
        now = datetime.now(UTC)
        if not database_is_configured():
            resolved: list[str] = []
            for event in self.get_active_events():
                if event.event_type == "fork" and event.end_at <= now:
                    self.resolve_fork_event(event.event_id)
                    resolved.append(event.event_id)
            return resolved

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT event_id::text
                    FROM game_events
                    WHERE event_type = 'fork' AND status = 'active' AND end_at <= %s
                    ORDER BY end_at ASC
                    """,
                    (now,),
                )
                rows = cursor.fetchall()
        resolved_ids: list[str] = []
        for row in rows:
            resolved = self.resolve_fork_event(str(row[0]))
            resolved_ids.append(resolved["event_id"])
        return resolved_ids

    def _get_modifier_event(self, *, modifier_type: str) -> EventRecord | None:
        active_events = self.get_active_events()
        for event in active_events:
            if event.modifier_type == modifier_type:
                return event
        return None

    @staticmethod
    def _coerce_uuid(value: str) -> UUID:
        return UUID(value)
