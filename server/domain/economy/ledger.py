from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
import json
from uuid import uuid4

from shared.database import open_connection


@dataclass(frozen=True)
class BlockFinalizationLedgerEntry:
    block_number: int
    required_work: Decimal
    total_work: Decimal
    reward_amount: Decimal
    posted_at: datetime


@dataclass(frozen=True)
class PlayerRewardLedgerEntry:
    block_number: int
    player_id: str
    reward_amount: Decimal
    contribution_hashes: Decimal
    posted_at: datetime


@dataclass(frozen=True)
class OfflineProgressLedgerEntry:
    player_id: str
    credited_work: Decimal
    simulated_work: Decimal
    contribution_hashes: Decimal
    cap_applied: bool
    cap_amount: Decimal
    offline_cap_tier: int
    cap_limit: Decimal
    window_started_at: datetime
    window_ended_at: datetime
    posted_at: datetime


class NoOpLedgerPoster:
    def __init__(self) -> None:
        self.entries: list[BlockFinalizationLedgerEntry] = []
        self.player_entries: list[PlayerRewardLedgerEntry] = []
        self.offline_entries: list[OfflineProgressLedgerEntry] = []

    def post_block_finalization(
        self,
        *,
        block_number: int,
        required_work: Decimal,
        total_work: Decimal,
        reward_amount: Decimal,
        posted_at: datetime,
    ) -> None:
        self.entries.append(
            BlockFinalizationLedgerEntry(
                block_number=block_number,
                required_work=required_work,
                total_work=total_work,
                reward_amount=reward_amount,
                posted_at=posted_at.astimezone(UTC),
            )
        )

    def post_player_reward_entries(
        self,
        *,
        block_number: int,
        rewards_by_player: dict[str, Decimal],
        contributions_by_player: dict[str, Decimal],
        posted_at: datetime,
    ) -> None:
        for player_id, reward_amount in rewards_by_player.items():
            self.player_entries.append(
                PlayerRewardLedgerEntry(
                    block_number=block_number,
                    player_id=player_id,
                    reward_amount=reward_amount,
                    contribution_hashes=contributions_by_player.get(player_id, Decimal("0")),
                    posted_at=posted_at.astimezone(UTC),
                )
            )

    def post_offline_progress_entry(
        self,
        *,
        player_id: str,
        credited_work: Decimal,
        simulated_work: Decimal,
        contribution_hashes: Decimal,
        cap_applied: bool,
        cap_amount: Decimal,
        offline_cap_tier: int,
        cap_limit: Decimal,
        window_started_at: datetime,
        window_ended_at: datetime,
        posted_at: datetime,
    ) -> None:
        self.offline_entries.append(
            OfflineProgressLedgerEntry(
                player_id=player_id,
                credited_work=credited_work,
                simulated_work=simulated_work,
                contribution_hashes=contribution_hashes,
                cap_applied=cap_applied,
                cap_amount=cap_amount,
                offline_cap_tier=offline_cap_tier,
                cap_limit=cap_limit,
                window_started_at=window_started_at.astimezone(UTC),
                window_ended_at=window_ended_at.astimezone(UTC),
                posted_at=posted_at.astimezone(UTC),
            )
        )


class PostgresLedgerPoster:
    def post_block_finalization(
        self,
        *,
        block_number: int,
        required_work: Decimal,
        total_work: Decimal,
        reward_amount: Decimal,
        posted_at: datetime,
    ) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO economy_ledger_entries (
                        ledger_entry_id,
                        entry_type,
                        amount,
                        currency,
                        reference_block_number,
                        metadata,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        uuid4(),
                        "block.finalized.reward_pool.v1",
                        reward_amount,
                        "credits",
                        block_number,
                        json.dumps(
                            {
                                "required_work": str(required_work),
                                "total_work": str(total_work),
                                "reward_amount": str(reward_amount),
                            }
                        ),
                        posted_at.astimezone(UTC),
                    ),
                )
            connection.commit()

    def post_player_reward_entries(
        self,
        *,
        block_number: int,
        rewards_by_player: dict[str, Decimal],
        contributions_by_player: dict[str, Decimal],
        posted_at: datetime,
    ) -> None:
        if not rewards_by_player:
            return

        with open_connection() as connection:
            with connection.cursor() as cursor:
                for player_id, reward_amount in rewards_by_player.items():
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
                            metadata,
                            created_at
                        )
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                        """,
                        (
                            uuid4(),
                            block_number,
                            player_id,
                            reward_amount,
                            contributions_by_player.get(player_id, Decimal("0")),
                            "credits",
                            "block.finalized.player_reward.v1",
                            json.dumps(
                                {
                                    "block_number": block_number,
                                    "player_id": player_id,
                                    "contribution_hashes": str(contributions_by_player.get(player_id, Decimal("0"))),
                                }
                            ),
                            posted_at.astimezone(UTC),
                        ),
                    )
                if rewards_by_player:
                    cursor.execute(
                        """
                        UPDATE players
                        SET blocks_finalized_contributed_count = progress.block_count,
                            player_tier = CASE
                                WHEN progress.block_count >= 20 THEN 3
                                WHEN progress.block_count >= 5 THEN 2
                                ELSE 1
                            END,
                            updated_at = NOW()
                        FROM (
                            SELECT player_id, COUNT(DISTINCT block_number) AS block_count
                            FROM economy_player_ledger_entries
                            WHERE entry_type = 'block.finalized.player_reward.v1'
                              AND player_id = ANY(%s)
                            GROUP BY player_id
                        ) progress
                        WHERE players.player_id::text = progress.player_id
                        """,
                        (list(rewards_by_player.keys()),),
                    )
            connection.commit()

    def post_offline_progress_entry(
        self,
        *,
        player_id: str,
        credited_work: Decimal,
        simulated_work: Decimal,
        contribution_hashes: Decimal,
        cap_applied: bool,
        cap_amount: Decimal,
        offline_cap_tier: int,
        cap_limit: Decimal,
        window_started_at: datetime,
        window_ended_at: datetime,
        posted_at: datetime,
    ) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
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
                        cap_applied,
                        cap_amount,
                        offline_cap_tier,
                        metadata,
                        created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                    """,
                    (
                        uuid4(),
                        None,
                        player_id,
                        credited_work,
                        contribution_hashes,
                        "work",
                        "mining.offline_progress.v1",
                        cap_applied,
                        cap_amount,
                        offline_cap_tier,
                        json.dumps(
                            {
                                "simulated_work": str(simulated_work),
                                "credited_work": str(credited_work),
                                "cap_limit": str(cap_limit),
                                "window_started_at": window_started_at.astimezone(UTC).isoformat(),
                                "window_ended_at": window_ended_at.astimezone(UTC).isoformat(),
                            }
                        ),
                        posted_at.astimezone(UTC),
                    ),
                )
            connection.commit()
