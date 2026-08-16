from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock
from typing import Protocol

from shared.database import open_connection


@dataclass(frozen=True)
class ActiveBlockSnapshot:
    block_number: int
    required_work: Decimal
    accumulated_work: Decimal


@dataclass(frozen=True)
class FinalizedBlockRecord:
    block_number: int
    required_work: Decimal
    total_work: Decimal
    finalized_at: datetime


@dataclass(frozen=True)
class AddWorkOutcome:
    active_block_number_before: int
    finalized_block_number: int | None
    required_work: Decimal
    total_work: Decimal | None


class DifficultyAdjuster(Protocol):
    def compute_next_required_work(
        self,
        *,
        current_required_work: Decimal,
        finalized_blocks: list[FinalizedBlockRecord],
    ) -> Decimal: ...


class InMemoryBlockchainStateStore:
    def __init__(self, *, required_work: Decimal, difficulty_adjuster: DifficultyAdjuster | None = None) -> None:
        self._active = ActiveBlockSnapshot(block_number=1, required_work=required_work, accumulated_work=Decimal("0"))
        self._finalized: list[FinalizedBlockRecord] = []
        self._difficulty_adjuster = difficulty_adjuster
        self._lock = Lock()

    def get_active_block(self) -> ActiveBlockSnapshot:
        return self._active

    def add_work(self, *, contribution: Decimal, finalized_at: datetime) -> AddWorkOutcome:
        with self._lock:
            before = self._active
            total_work = before.accumulated_work + contribution
            if total_work >= before.required_work:
                finalized = FinalizedBlockRecord(
                    block_number=before.block_number,
                    required_work=before.required_work,
                    total_work=total_work,
                    finalized_at=finalized_at.astimezone(UTC),
                )
                self._finalized.append(finalized)
                next_required_work = before.required_work
                if self._difficulty_adjuster is not None:
                    next_required_work = self._difficulty_adjuster.compute_next_required_work(
                        current_required_work=before.required_work,
                        finalized_blocks=self._finalized,
                    )
                residual = total_work - before.required_work
                self._active = ActiveBlockSnapshot(
                    block_number=before.block_number + 1,
                    required_work=next_required_work,
                    accumulated_work=residual,
                )
                return AddWorkOutcome(
                    active_block_number_before=before.block_number,
                    finalized_block_number=before.block_number,
                    required_work=before.required_work,
                    total_work=total_work,
                )

            self._active = ActiveBlockSnapshot(
                block_number=before.block_number,
                required_work=before.required_work,
                accumulated_work=total_work,
            )
            return AddWorkOutcome(
                active_block_number_before=before.block_number,
                finalized_block_number=None,
                required_work=before.required_work,
                total_work=None,
            )

    def list_finalized_blocks(self) -> list[FinalizedBlockRecord]:
        return list(self._finalized)


class PostgresBlockchainStateStore:
    def __init__(self, *, required_work: Decimal, difficulty_adjuster: DifficultyAdjuster | None = None) -> None:
        self.required_work = required_work
        self.difficulty_adjuster = difficulty_adjuster

    def _ensure_active_row(self) -> None:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO blockchain_active_block (singleton_id, block_number, required_work, accumulated_work)
                    VALUES (TRUE, 1, %s, 0)
                    ON CONFLICT (singleton_id) DO NOTHING
                    """,
                    (self.required_work,),
                )
            connection.commit()

    def get_active_block(self) -> ActiveBlockSnapshot:
        self._ensure_active_row()
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT block_number, required_work, accumulated_work
                    FROM blockchain_active_block
                    WHERE singleton_id = TRUE
                    """
                )
                row = cursor.fetchone()
        return ActiveBlockSnapshot(block_number=row[0], required_work=row[1], accumulated_work=row[2])

    def add_work(self, *, contribution: Decimal, finalized_at: datetime) -> AddWorkOutcome:
        self._ensure_active_row()
        finalized_at_utc = finalized_at.astimezone(UTC)

        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT block_number, required_work, accumulated_work
                    FROM blockchain_active_block
                    WHERE singleton_id = TRUE
                    FOR UPDATE
                    """
                )
                current_block_number, current_required_work, current_accumulated_work = cursor.fetchone()
                total_work = current_accumulated_work + contribution

                if total_work >= current_required_work:
                    cursor.execute(
                        """
                        INSERT INTO blockchain_finalized_blocks (block_number, required_work, total_work, finalized_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (block_number) DO NOTHING
                        """,
                        (current_block_number, current_required_work, total_work, finalized_at_utc),
                    )
                    next_required_work = current_required_work
                    if self.difficulty_adjuster is not None:
                        cursor.execute(
                            """
                            SELECT block_number, required_work, total_work, finalized_at
                            FROM blockchain_finalized_blocks
                            ORDER BY block_number ASC
                            """
                        )
                        finalized_rows = cursor.fetchall()
                        finalized_records = [
                            FinalizedBlockRecord(
                                block_number=row[0],
                                required_work=row[1],
                                total_work=row[2],
                                finalized_at=row[3],
                            )
                            for row in finalized_rows
                        ]
                        next_required_work = self.difficulty_adjuster.compute_next_required_work(
                            current_required_work=current_required_work,
                            finalized_blocks=finalized_records,
                        )

                    residual = total_work - current_required_work
                    cursor.execute(
                        """
                        UPDATE blockchain_active_block
                        SET block_number = %s,
                            required_work = %s,
                            accumulated_work = %s,
                            updated_at = NOW()
                        WHERE singleton_id = TRUE
                        """,
                        (current_block_number + 1, next_required_work, residual),
                    )
                    connection.commit()
                    return AddWorkOutcome(
                        active_block_number_before=current_block_number,
                        finalized_block_number=current_block_number,
                        required_work=current_required_work,
                        total_work=total_work,
                    )

                cursor.execute(
                    """
                    UPDATE blockchain_active_block
                    SET accumulated_work = %s,
                        updated_at = NOW()
                    WHERE singleton_id = TRUE
                    """,
                    (total_work,),
                )
            connection.commit()

        return AddWorkOutcome(
            active_block_number_before=current_block_number,
            finalized_block_number=None,
            required_work=current_required_work,
            total_work=None,
        )

    def list_finalized_blocks(self) -> list[FinalizedBlockRecord]:
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT block_number, required_work, total_work, finalized_at
                    FROM blockchain_finalized_blocks
                    ORDER BY block_number ASC
                    """
                )
                rows = cursor.fetchall()
        return [
            FinalizedBlockRecord(
                block_number=row[0],
                required_work=row[1],
                total_work=row[2],
                finalized_at=row[3],
            )
            for row in rows
        ]
