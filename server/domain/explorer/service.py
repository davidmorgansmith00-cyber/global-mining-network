from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from domain.genesis.service import get_genesis_service
from shared.database import database_is_configured, open_connection


def _clamp_limit(limit: int, *, default: int = 50, maximum: int = 500) -> int:
    if limit <= 0:
        return default
    return min(limit, maximum)


class ChainExplorerService:
    def __init__(self) -> None:
        self._genesis_service = get_genesis_service()

    def get_blocks(
        self,
        *,
        limit: int = 50,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if not database_is_configured():
            return []
        bounded_limit = _clamp_limit(limit)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT block_number, block_id, difficulty, reward_pool, miners_count, completion_time
                    FROM v_block_summary
                    WHERE completion_time >= %s
                      AND completion_time <= %s
                    ORDER BY block_number DESC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        start_date or datetime(1970, 1, 1, tzinfo=UTC),
                        end_date or datetime.now(UTC),
                        bounded_limit,
                        max(offset, 0),
                    ),
                )
                rows = cursor.fetchall()
        return [
            {
                "block_number": int(row[0]),
                "block_id": row[1],
                "difficulty": str(row[2]),
                "reward_pool": str(row[3]),
                "miners_count": int(row[4]),
                "completion_time": row[5].astimezone(UTC).isoformat(),
            }
            for row in rows
        ]

    def get_block_details(self, *, block_number: int) -> dict[str, Any] | None:
        if block_number == 1:
            genesis = self._genesis_service.get_current_genesis_block(include_archived=False)
            if genesis is not None:
                payload = self._genesis_service.serialize_genesis_block(genesis)
                payload.update(
                    {
                        "block_id": genesis.block_hash,
                        "difficulty": "0.000000",
                        "reward_pool": "0.000000",
                        "miners_count": 0,
                        "completion_time": genesis.created_at.isoformat(),
                        "miners": [],
                    }
                )
                return payload
        if not database_is_configured():
            return None
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT block_number, block_id, difficulty, reward_pool, miners_count, completion_time
                    FROM v_block_summary
                    WHERE block_number = %s
                    """,
                    (block_number,),
                )
                row = cursor.fetchone()
                if row is None:
                    return None
                cursor.execute(
                    """
                    SELECT player_id, contribution_amount, reward_earned, timestamp
                    FROM v_player_contribution_history
                    WHERE block_number = %s
                    ORDER BY contribution_amount DESC, player_id ASC
                    """,
                    (block_number,),
                )
                miners = cursor.fetchall()
        return {
            "block_number": int(row[0]),
            "block_id": row[1],
            "difficulty": str(row[2]),
            "reward_pool": str(row[3]),
            "miners_count": int(row[4]),
            "completion_time": row[5].astimezone(UTC).isoformat(),
            "miners": [
                {
                    "player_id": item[0],
                    "contribution_amount": str(item[1]),
                    "reward_earned": str(item[2]),
                    "timestamp": item[3].astimezone(UTC).isoformat(),
                }
                for item in miners
            ],
        }

    def get_player_history(self, *, player_id: str, limit: int = 50, offset: int = 0) -> list[dict[str, Any]]:
        if not database_is_configured():
            return []
        bounded_limit = _clamp_limit(limit)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT player_id, block_number, contribution_amount, reward_earned, timestamp
                    FROM v_player_contribution_history
                    WHERE player_id = %s
                    ORDER BY block_number DESC
                    LIMIT %s OFFSET %s
                    """,
                    (player_id, bounded_limit, max(offset, 0)),
                )
                rows = cursor.fetchall()
        return [
            {
                "player_id": row[0],
                "block_number": int(row[1]),
                "contribution_amount": str(row[2]),
                "reward_earned": str(row[3]),
                "timestamp": row[4].astimezone(UTC).isoformat(),
            }
            for row in rows
        ]

    def get_player_earnings(self, *, player_id: str, start_date: datetime | None, end_date: datetime | None) -> list[dict[str, Any]]:
        if not database_is_configured():
            return []
        start_at = start_date or datetime(1970, 1, 1, tzinfo=UTC)
        end_at = end_date or datetime.now(UTC)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT DATE_TRUNC('day', timestamp) AS day_bucket, COALESCE(SUM(reward_earned), 0)
                    FROM v_player_contribution_history
                    WHERE player_id = %s
                      AND timestamp >= %s
                      AND timestamp <= %s
                    GROUP BY day_bucket
                    ORDER BY day_bucket ASC
                    """,
                    (player_id, start_at, end_at),
                )
                rows = cursor.fetchall()
        return [
            {"date": row[0].date().isoformat(), "earnings": str(row[1])}
            for row in rows
        ]

    def get_transactions(
        self,
        *,
        transaction_type: str | None = None,
        player_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if not database_is_configured():
            return []
        bounded_limit = _clamp_limit(limit)
        clauses = ["timestamp >= %s", "timestamp <= %s"]
        params: list[Any] = [start_date or datetime(1970, 1, 1, tzinfo=UTC), end_date or datetime.now(UTC)]
        if transaction_type:
            clauses.append("type = %s")
            params.append(transaction_type)
        if player_id:
            clauses.append("(player_id = %s OR to_player = %s OR from_player = %s)")
            params.extend([player_id, player_id, player_id])
        params.extend([bounded_limit, max(offset, 0)])
        where_clause = " AND ".join(clauses)
        query = f"""
            SELECT transaction_id, from_player, to_player, amount, type, timestamp
            FROM v_transaction_ledger
            WHERE {where_clause}
            ORDER BY timestamp DESC
            LIMIT %s OFFSET %s
        """
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
        return [
            {
                "transaction_id": row[0],
                "from_player": row[1],
                "to_player": row[2],
                "amount": str(row[3]),
                "type": row[4],
                "timestamp": row[5].astimezone(UTC).isoformat(),
            }
            for row in rows
        ]

    def get_pool_history(
        self,
        *,
        pool_id: str,
        limit: int = 50,
        offset: int = 0,
        start_date: datetime | None = None,
        end_date: datetime | None = None,
    ) -> list[dict[str, Any]]:
        if not database_is_configured():
            return []
        bounded_limit = _clamp_limit(limit)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT pool_id, event_type, player_id, amount, timestamp
                    FROM v_pool_history
                    WHERE pool_id = %s
                      AND timestamp >= %s
                      AND timestamp <= %s
                    ORDER BY timestamp DESC
                    LIMIT %s OFFSET %s
                    """,
                    (
                        pool_id,
                        start_date or datetime(1970, 1, 1, tzinfo=UTC),
                        end_date or datetime.now(UTC),
                        bounded_limit,
                        max(offset, 0),
                    ),
                )
                rows = cursor.fetchall()
        return [
            {
                "pool_id": row[0],
                "event_type": row[1],
                "player_id": row[2],
                "amount": str(row[3]),
                "timestamp": row[4].astimezone(UTC).isoformat(),
            }
            for row in rows
        ]

    def search(self, *, query: str, limit: int = 10) -> list[dict[str, str]]:
        normalized_query = query.strip().lower()
        bounded_limit = _clamp_limit(limit, default=10, maximum=50)
        items: list[dict[str, str]] = []
        genesis = self._genesis_service.get_current_genesis_block(include_archived=False)
        if genesis is not None and (
            "genesis".startswith(normalized_query)
            or genesis.block_hash.lower().startswith(normalized_query)
            or genesis.chain_id.lower().startswith(normalized_query)
        ):
            items.append(
                {
                    "type": "block",
                    "id": "1",
                    "label": f"Genesis Block #1 · {genesis.block_hash[:12]}",
                }
            )
        if not database_is_configured():
            return items
        needle = f"%{normalized_query}%"
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT player_id::text, email
                    FROM players
                    WHERE LOWER(player_id::text) LIKE %s OR LOWER(email) LIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (needle, needle, max(bounded_limit - len(items), 0)),
                )
                player_rows = cursor.fetchall()
                cursor.execute(
                    """
                    SELECT pool_id::text, pool_name
                    FROM mining_pools
                    WHERE LOWER(pool_name) LIKE %s
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (needle, bounded_limit),
                )
                pool_rows = cursor.fetchall()
        results = list(items)
        results.extend(
            [
                {"type": "player", "id": row[0], "label": row[1] or row[0]}
                for row in player_rows
            ]
        )
        results.extend({"type": "pool", "id": row[0], "label": row[1]} for row in pool_rows)
        return results[:bounded_limit]
