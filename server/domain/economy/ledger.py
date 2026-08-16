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


class NoOpLedgerPoster:
    def __init__(self) -> None:
        self.entries: list[BlockFinalizationLedgerEntry] = []
        self.player_entries: list[PlayerRewardLedgerEntry] = []

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
            connection.commit()
