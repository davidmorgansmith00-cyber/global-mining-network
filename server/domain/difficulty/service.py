from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC
from decimal import Decimal, ROUND_HALF_UP

from domain.blockchain.store import FinalizedBlockRecord


WORK_QUANTIZE = Decimal("0.000001")


@dataclass(frozen=True)
class DifficultyConfig:
    target_block_seconds: int = 10
    history_window_size: int = 10
    max_upward_adjustment_pct: Decimal = Decimal("0.20")
    max_downward_adjustment_pct: Decimal = Decimal("0.20")
    minimum_required_work: Decimal = Decimal("1")


class DifficultyAdjustmentService:
    def __init__(self, config: DifficultyConfig | None = None) -> None:
        self.config = config or DifficultyConfig()

    def compute_next_required_work(
        self,
        *,
        current_required_work: Decimal,
        finalized_blocks: list[FinalizedBlockRecord],
    ) -> Decimal:
        if len(finalized_blocks) < 2:
            return self._quantize(max(current_required_work, self.config.minimum_required_work))

        window = finalized_blocks[-self.config.history_window_size :]
        if len(window) < 2:
            return self._quantize(max(current_required_work, self.config.minimum_required_work))

        first = window[0].finalized_at.astimezone(UTC)
        last = window[-1].finalized_at.astimezone(UTC)
        elapsed = (last - first).total_seconds()
        if elapsed <= 0:
            return self._quantize(max(current_required_work, self.config.minimum_required_work))

        observed_avg = Decimal(str(elapsed / (len(window) - 1)))
        target = Decimal(str(self.config.target_block_seconds))
        ratio = target / observed_avg

        if ratio > Decimal("1"):
            proposed_multiplier = Decimal("1") + min(
                ratio - Decimal("1"),
                self.config.max_upward_adjustment_pct,
            )
        else:
            proposed_multiplier = Decimal("1") - min(
                Decimal("1") - ratio,
                self.config.max_downward_adjustment_pct,
            )

        next_required_work = current_required_work * proposed_multiplier
        return self._quantize(max(next_required_work, self.config.minimum_required_work))

    @staticmethod
    def _quantize(value: Decimal) -> Decimal:
        return value.quantize(WORK_QUANTIZE, rounding=ROUND_HALF_UP)
