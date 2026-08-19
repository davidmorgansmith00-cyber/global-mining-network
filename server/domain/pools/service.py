from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_FLOOR
from uuid import UUID

from shared.database import database_is_configured, open_connection


POOL_REWARD_DISTRIBUTION_TYPE = "pool.reward_distribution.v1"
_MIN_UNIT = Decimal("0.000001")
MAX_FEE_PERCENTAGE = Decimal("10")
MIN_FEE_PERCENTAGE = Decimal("0")


@dataclass(frozen=True)
class PoolInfo:
    pool_id: str
    owner_id: str
    pool_name: str
    description: str
    fee_percentage: Decimal
    status: str
    created_at: datetime
    dissolved_at: datetime | None


@dataclass(frozen=True)
class PoolMember:
    pool_id: str
    player_id: str
    joined_at: datetime
    left_at: datetime | None
    accumulated_reward_at_leave: Decimal


@dataclass(frozen=True)
class PoolStats:
    pool_id: str
    pool_name: str
    owner_id: str
    fee_percentage: Decimal
    status: str
    member_count: int
    members: list[PoolMember]
    blocks_completed: int
    total_distributed_rewards: Decimal


@dataclass(frozen=True)
class RewardShare:
    member_id: str
    member_hashrate: Decimal
    gross_share: Decimal
    final_share: Decimal
    remainder_bonus: int


class PoolService:
    def create_pool(
        self,
        owner_id: str,
        pool_name: str,
        description: str,
        fee_percentage: Decimal,
    ) -> str:
        if not owner_id.strip():
            raise ValueError("owner_id_required")
        if not pool_name.strip():
            raise ValueError("pool_name_required")
        if fee_percentage < MIN_FEE_PERCENTAGE or fee_percentage > MAX_FEE_PERCENTAGE:
            raise ValueError("fee_percentage_out_of_range")
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO mining_pools (owner_id, pool_name, description, fee_percentage, status, created_at)
                    VALUES (%s, %s, %s, %s, 'active', %s)
                    RETURNING pool_id::text
                    """,
                    (owner_id.strip(), pool_name.strip(), description, str(fee_percentage), now),
                )
                row = cur.fetchone()
            conn.commit()
        return str(row[0])

    def join_pool(self, player_id: str, pool_id: str) -> None:
        if not player_id.strip():
            raise ValueError("player_id_required")
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT status FROM mining_pools WHERE pool_id = %s",
                    (pool_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("pool_not_found")
                if row[0] != "active":
                    raise ValueError("pool_not_active")

                cur.execute(
                    """
                    SELECT pool_id::text
                    FROM pool_members
                    WHERE player_id = %s AND left_at IS NULL
                    """,
                    (player_id,),
                )
                active_membership = cur.fetchone()
                if active_membership is not None:
                    if active_membership[0] == pool_id:
                        raise ValueError("already_a_member")
                    raise ValueError("already_in_another_pool")

                cur.execute(
                    """
                    INSERT INTO pool_members (pool_id, player_id, joined_at)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (pool_id, player_id) DO UPDATE
                      SET joined_at = EXCLUDED.joined_at,
                          left_at = NULL,
                          accumulated_reward_at_leave = 0
                    """,
                    (pool_id, player_id, now),
                )
            conn.commit()

    def leave_pool(self, player_id: str, pool_id: str) -> Decimal:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE pool_members
                    SET left_at = %s
                    WHERE pool_id = %s AND player_id = %s AND left_at IS NULL
                    RETURNING accumulated_reward_at_leave
                    """,
                    (now, pool_id, player_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("not_a_member")
                accumulated = Decimal(str(row[0]))
            conn.commit()
        return accumulated

    def get_pool_stats(self, pool_id: str) -> PoolStats | None:
        if not database_is_configured():
            return None

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pool_id::text, owner_id, pool_name, description,
                           fee_percentage, status, created_at, dissolved_at
                    FROM mining_pools
                    WHERE pool_id = %s
                    """,
                    (pool_id,),
                )
                pool_row = cur.fetchone()
                if pool_row is None:
                    return None

                cur.execute(
                    """
                    SELECT player_id, joined_at, left_at, accumulated_reward_at_leave
                    FROM pool_members
                    WHERE pool_id = %s AND left_at IS NULL
                    ORDER BY player_id ASC
                    """,
                    (pool_id,),
                )
                member_rows = cur.fetchall()
                members = [
                    PoolMember(
                        pool_id=pool_id,
                        player_id=row[0],
                        joined_at=row[1],
                        left_at=row[2],
                        accumulated_reward_at_leave=Decimal(str(row[3])),
                    )
                    for row in member_rows
                ]

                cur.execute(
                    """
                    SELECT COUNT(DISTINCT metadata->>'block_number'),
                           COALESCE(SUM(amount), 0)
                    FROM economy_player_ledger_entries
                    WHERE entry_type = %s
                      AND metadata->>'pool_id' = %s
                    """,
                    (POOL_REWARD_DISTRIBUTION_TYPE, pool_id),
                )
                ledger_row = cur.fetchone()

        blocks_completed = 0 if ledger_row is None or ledger_row[0] is None else int(ledger_row[0])
        total_distributed = Decimal("0") if ledger_row is None or ledger_row[1] is None else Decimal(str(ledger_row[1]))
        return PoolStats(
            pool_id=pool_row[0],
            pool_name=pool_row[2],
            owner_id=pool_row[1],
            fee_percentage=Decimal(str(pool_row[4])),
            status=pool_row[5],
            member_count=len(members),
            members=members,
            blocks_completed=blocks_completed,
            total_distributed_rewards=total_distributed,
        )

    def dissolve_pool(self, pool_id: str, owner_id: str) -> None:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT owner_id, status FROM mining_pools WHERE pool_id = %s",
                    (pool_id,),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("pool_not_found")
                if row[0] != owner_id:
                    raise ValueError("not_pool_owner")
                if row[1] != "active":
                    raise ValueError("pool_already_dissolved")

                cur.execute(
                    "UPDATE pool_members SET left_at = %s WHERE pool_id = %s AND left_at IS NULL",
                    (now, pool_id),
                )
                cur.execute(
                    "UPDATE mining_pools SET status = 'dissolved', dissolved_at = %s WHERE pool_id = %s",
                    (now, pool_id),
                )
            conn.commit()

    def list_pools(self, limit: int = 50, offset: int = 0) -> list[PoolInfo]:
        if not database_is_configured():
            return []

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT pool_id::text, owner_id, pool_name, description,
                           fee_percentage, status, created_at, dissolved_at
                    FROM mining_pools
                    WHERE status = 'active'
                    ORDER BY created_at DESC
                    LIMIT %s OFFSET %s
                    """,
                    (limit, offset),
                )
                rows = cur.fetchall()

        return [
            PoolInfo(
                pool_id=row[0],
                owner_id=row[1],
                pool_name=row[2],
                description=row[3],
                fee_percentage=Decimal(str(row[4])),
                status=row[5],
                created_at=row[6],
                dissolved_at=row[7],
            )
            for row in rows
        ]

    def calculate_reward_shares(
        self,
        pool_reward: Decimal,
        fee_percentage: Decimal,
        member_hashrates: dict[str, Decimal],
    ) -> tuple[Decimal, list[RewardShare]]:
        if pool_reward < Decimal("0"):
            raise ValueError("pool_reward_must_be_non_negative")
        if fee_percentage < MIN_FEE_PERCENTAGE or fee_percentage > MAX_FEE_PERCENTAGE:
            raise ValueError("fee_percentage_out_of_range")
        if any(hashrate < Decimal("0") for hashrate in member_hashrates.values()):
            raise ValueError("member_hashrate_must_be_non_negative")

        if not member_hashrates:
            return pool_reward.quantize(_MIN_UNIT), []

        total_hashrate = sum(member_hashrates.values(), Decimal("0"))
        if total_hashrate <= Decimal("0"):
            return pool_reward.quantize(_MIN_UNIT), []

        quantized_reward = pool_reward.quantize(_MIN_UNIT)
        owner_fee = (quantized_reward * (fee_percentage / Decimal("100"))).quantize(
            _MIN_UNIT,
            rounding=ROUND_FLOOR,
        )
        reward_after_fee = quantized_reward - owner_fee

        raw_shares: dict[str, Decimal] = {}
        for member_id, hashrate in member_hashrates.items():
            contribution = hashrate / total_hashrate
            raw_shares[member_id] = (reward_after_fee * contribution).quantize(
                _MIN_UNIT,
                rounding=ROUND_FLOOR,
            )

        total_floored = sum(raw_shares.values(), Decimal("0"))
        remainder_units = int(((reward_after_fee - total_floored) / _MIN_UNIT).to_integral_value(rounding=ROUND_FLOOR))

        shares: list[RewardShare] = []
        for index, member_id in enumerate(sorted(member_hashrates.keys())):
            bonus = 1 if index < remainder_units else 0
            final_share = raw_shares[member_id] + (Decimal(bonus) * _MIN_UNIT)
            shares.append(
                RewardShare(
                    member_id=member_id,
                    member_hashrate=member_hashrates[member_id],
                    gross_share=raw_shares[member_id],
                    final_share=final_share,
                    remainder_bonus=bonus,
                )
            )
        return owner_fee, shares
