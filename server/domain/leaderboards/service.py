from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal

from shared.database import database_is_configured, open_connection


_CREDIT_LEDGER_ENTRY_TYPES = (
    "block.finalized.player_reward.v1",
    "market.purchase.v1",
    "hardware.upgrade.v1",
    "player.equipment_trade.v1",
    "pool.reward_distribution.v1",
)


@dataclass(frozen=True)
class HashrateRank:
    rank: int
    player_id: str
    player_name: str
    effective_hashrate: Decimal
    is_hidden: bool
    updated_at: datetime


@dataclass(frozen=True)
class PoolRank:
    rank: int
    pool_id: str
    pool_name: str
    total_hashrate: Decimal
    member_count: int
    is_hidden: bool
    updated_at: datetime


@dataclass(frozen=True)
class TierProgressionRank:
    rank: int
    player_id: str
    player_name: str
    tier: int
    days_to_reach: Decimal
    reached_at: datetime
    is_hidden: bool
    updated_at: datetime


@dataclass(frozen=True)
class WeeklyEarningsRank:
    rank: int
    player_id: str
    player_name: str
    earnings_7d: Decimal
    is_hidden: bool
    updated_at: datetime


@dataclass(frozen=True)
class WealthRank:
    rank: int
    player_id: str
    player_name: str
    total_wealth: Decimal
    is_hidden: bool
    updated_at: datetime


@dataclass(frozen=True)
class PlayerLeaderboardPosition:
    player_id: str
    hashrate_rank: int | None
    weekly_earnings_rank: int | None
    wealth_rank: int | None
    total_players: int
    percentile: Decimal | None


class LeaderboardService:
    def refresh_hashrate_leaderboard(self) -> int:
        if not database_is_configured():
            return 0

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE leaderboard_hashrate")
                cur.execute(
                    """
                    INSERT INTO leaderboard_hashrate (rank, player_id, player_name, effective_hashrate, updated_at)
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY COALESCE(p.effective_hashrate_cached, 0) DESC, p.player_id::text ASC) AS rank,
                        p.player_id::text,
                        p.player_id::text AS player_name,
                        COALESCE(p.effective_hashrate_cached, 0)::numeric(38, 6) AS effective_hashrate,
                        %s AS updated_at
                    FROM players p
                    LEFT JOIN leaderboard_visibility lv ON p.player_id::text = lv.player_id
                    WHERE COALESCE(lv.is_hidden, FALSE) = FALSE
                    ORDER BY COALESCE(p.effective_hashrate_cached, 0) DESC, p.player_id::text ASC
                    LIMIT 100
                    """,
                    (now,),
                )
                count = cur.rowcount
            conn.commit()
        return count

    def refresh_pool_leaderboard(self) -> int:
        if not database_is_configured():
            return 0

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE leaderboard_pools")
                cur.execute(
                    """
                    INSERT INTO leaderboard_pools (rank, pool_id, pool_name, total_hashrate, member_count, updated_at)
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY total_hashrate DESC, pool_id ASC) AS rank,
                        pool_id,
                        pool_name,
                        total_hashrate,
                        member_count,
                        %s AS updated_at
                    FROM (
                        SELECT
                            mp.pool_id,
                            mp.pool_name,
                            COALESCE(SUM(COALESCE(p.effective_hashrate_cached, 0)), 0)::numeric(38, 6) AS total_hashrate,
                            COUNT(pm.player_id) AS member_count
                        FROM mining_pools mp
                        JOIN pool_members pm
                          ON mp.pool_id = pm.pool_id
                         AND pm.left_at IS NULL
                        LEFT JOIN players p
                          ON p.player_id::text = pm.player_id
                        WHERE mp.status = 'active'
                        GROUP BY mp.pool_id, mp.pool_name
                    ) ranked
                    ORDER BY total_hashrate DESC, pool_id ASC
                    LIMIT 50
                    """,
                    (now,),
                )
                count = cur.rowcount
            conn.commit()
        return count

    def refresh_weekly_earnings_leaderboard(self) -> int:
        if not database_is_configured():
            return 0

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE leaderboard_weekly_earnings")
                cur.execute(
                    """
                    INSERT INTO leaderboard_weekly_earnings (rank, player_id, player_name, earnings_7d, updated_at)
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY earnings_7d DESC, player_id ASC) AS rank,
                        player_id,
                        player_id AS player_name,
                        earnings_7d,
                        %s AS updated_at
                    FROM (
                        SELECT
                            le.player_id,
                            SUM(GREATEST(le.amount, 0)) AS earnings_7d
                        FROM economy_player_ledger_entries le
                        LEFT JOIN leaderboard_visibility lv ON le.player_id = lv.player_id
                        WHERE le.created_at >= NOW() - INTERVAL '7 days'
                          AND le.entry_type IN (
                              'block.finalized.player_reward.v1',
                              'pool.reward_distribution.v1',
                              'player.equipment_trade.v1'
                          )
                          AND COALESCE(lv.is_hidden, FALSE) = FALSE
                        GROUP BY le.player_id
                    ) ranked
                    ORDER BY earnings_7d DESC, player_id ASC
                    LIMIT 50
                    """,
                    (now,),
                )
                count = cur.rowcount
            conn.commit()
        return count

    def refresh_wealth_leaderboard(self) -> int:
        if not database_is_configured():
            return 0

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("TRUNCATE TABLE leaderboard_wealth")
                cur.execute(
                    """
                    INSERT INTO leaderboard_wealth (rank, player_id, player_name, total_wealth, updated_at)
                    SELECT
                        ROW_NUMBER() OVER (ORDER BY total_wealth DESC, player_id ASC) AS rank,
                        player_id,
                        player_id AS player_name,
                        total_wealth,
                        %s AS updated_at
                    FROM (
                        SELECT
                            le.player_id,
                            COALESCE(SUM(le.amount), 0)::numeric(38, 6) AS total_wealth
                        FROM economy_player_ledger_entries le
                        LEFT JOIN leaderboard_visibility lv ON le.player_id = lv.player_id
                        WHERE le.currency = 'credits'
                          AND le.entry_type = ANY(%s)
                          AND COALESCE(lv.is_hidden, FALSE) = FALSE
                        GROUP BY le.player_id
                    ) ranked
                    ORDER BY total_wealth DESC, player_id ASC
                    LIMIT 50
                    """,
                    (now, list(_CREDIT_LEDGER_ENTRY_TYPES)),
                )
                count = cur.rowcount
            conn.commit()
        return count

    def get_hashrate_leaderboard(self, limit: int = 100, offset: int = 0) -> list[HashrateRank]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rank, player_id, player_name, effective_hashrate, is_hidden, updated_at
                    FROM leaderboard_hashrate
                    ORDER BY rank ASC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()
        return [
            HashrateRank(
                rank=int(row[0]),
                player_id=row[1],
                player_name=row[2],
                effective_hashrate=Decimal(str(row[3])),
                is_hidden=bool(row[4]),
                updated_at=row[5],
            )
            for row in rows
        ]

    def get_pool_leaderboard(self, limit: int = 50, offset: int = 0) -> list[PoolRank]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rank, pool_id::text, pool_name, total_hashrate, member_count, is_hidden, updated_at
                    FROM leaderboard_pools
                    ORDER BY rank ASC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()
        return [
            PoolRank(
                rank=int(row[0]),
                pool_id=row[1],
                pool_name=row[2],
                total_hashrate=Decimal(str(row[3])),
                member_count=int(row[4]),
                is_hidden=bool(row[5]),
                updated_at=row[6],
            )
            for row in rows
        ]

    def get_weekly_earnings_leaderboard(self, limit: int = 50, offset: int = 0) -> list[WeeklyEarningsRank]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rank, player_id, player_name, earnings_7d, is_hidden, updated_at
                    FROM leaderboard_weekly_earnings
                    ORDER BY rank ASC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()
        return [
            WeeklyEarningsRank(
                rank=int(row[0]),
                player_id=row[1],
                player_name=row[2],
                earnings_7d=Decimal(str(row[3])),
                is_hidden=bool(row[4]),
                updated_at=row[5],
            )
            for row in rows
        ]

    def get_wealth_leaderboard(self, limit: int = 50, offset: int = 0) -> list[WealthRank]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT rank, player_id, player_name, total_wealth, is_hidden, updated_at
                    FROM leaderboard_wealth
                    ORDER BY rank ASC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()
        return [
            WealthRank(
                rank=int(row[0]),
                player_id=row[1],
                player_name=row[2],
                total_wealth=Decimal(str(row[3])),
                is_hidden=bool(row[4]),
                updated_at=row[5],
            )
            for row in rows
        ]

    def get_player_leaderboard_position(self, player_id: str) -> PlayerLeaderboardPosition:
        if not database_is_configured():
            return PlayerLeaderboardPosition(
                player_id=player_id,
                hashrate_rank=None,
                weekly_earnings_rank=None,
                wealth_rank=None,
                total_players=0,
                percentile=None,
            )

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) FROM players")
                total = int(cur.fetchone()[0])
                cur.execute("SELECT rank FROM leaderboard_hashrate WHERE player_id = %s", (player_id,))
                row = cur.fetchone()
                hashrate_rank = None if row is None else int(row[0])
                cur.execute("SELECT rank FROM leaderboard_weekly_earnings WHERE player_id = %s", (player_id,))
                row = cur.fetchone()
                weekly_rank = None if row is None else int(row[0])
                cur.execute("SELECT rank FROM leaderboard_wealth WHERE player_id = %s", (player_id,))
                row = cur.fetchone()
                wealth_rank = None if row is None else int(row[0])

        percentile = None
        if hashrate_rank is not None and total > 0:
            percentile = ((Decimal("1") - (Decimal(hashrate_rank) / Decimal(total))) * Decimal("100")).quantize(
                Decimal("0.01")
            )
        return PlayerLeaderboardPosition(
            player_id=player_id,
            hashrate_rank=hashrate_rank,
            weekly_earnings_rank=weekly_rank,
            wealth_rank=wealth_rank,
            total_players=total,
            percentile=percentile,
        )

    def toggle_leaderboard_visibility(self, player_id: str) -> bool:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO leaderboard_visibility (player_id, is_hidden, updated_at)
                    VALUES (%s, TRUE, %s)
                    ON CONFLICT (player_id) DO UPDATE
                      SET is_hidden = NOT leaderboard_visibility.is_hidden,
                          updated_at = EXCLUDED.updated_at
                    RETURNING is_hidden
                    """,
                    (player_id, now),
                )
                new_hidden = bool(cur.fetchone()[0])
            conn.commit()
        return new_hidden
