from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, ROUND_HALF_UP


DECIMAL_PLACES = Decimal("0.000001")


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _quantize(value: Decimal) -> Decimal:
    return value.quantize(DECIMAL_PLACES, rounding=ROUND_HALF_UP)


@dataclass(frozen=True)
class IntervalBoundaryState:
    occurred_at: datetime
    hashrate_multiplier: Decimal = Decimal("1")
    paused: bool = False


@dataclass(frozen=True)
class IntervalSlice:
    started_at: datetime
    ended_at: datetime
    elapsed_seconds: int
    effective_hashrate_hps: Decimal
    contribution_hashes: Decimal


def slice_progression_intervals(
    *,
    window_started_at: datetime,
    window_ended_at: datetime,
    base_hashrate_hps: Decimal,
    boundary_states: list[IntervalBoundaryState],
    starting_multiplier: Decimal = Decimal("1"),
    starting_paused: bool = False,
) -> list[IntervalSlice]:
    start = _to_utc(window_started_at)
    end = _to_utc(window_ended_at)
    if end <= start:
        return []

    ordered_boundaries = sorted(
        [
            IntervalBoundaryState(
                occurred_at=_to_utc(boundary.occurred_at),
                hashrate_multiplier=boundary.hashrate_multiplier,
                paused=boundary.paused,
            )
            for boundary in boundary_states
            if start <= _to_utc(boundary.occurred_at) < end
        ],
        key=lambda item: item.occurred_at,
    )

    slices: list[IntervalSlice] = []
    current_time = start
    current_multiplier = starting_multiplier
    current_paused = starting_paused

    for boundary in ordered_boundaries:
        if boundary.occurred_at > current_time:
            slices.append(
                _build_slice(
                    started_at=current_time,
                    ended_at=boundary.occurred_at,
                    base_hashrate_hps=base_hashrate_hps,
                    multiplier=current_multiplier,
                    paused=current_paused,
                )
            )

        current_time = boundary.occurred_at
        current_multiplier = boundary.hashrate_multiplier
        current_paused = boundary.paused

    if end > current_time:
        slices.append(
            _build_slice(
                started_at=current_time,
                ended_at=end,
                base_hashrate_hps=base_hashrate_hps,
                multiplier=current_multiplier,
                paused=current_paused,
            )
        )

    return [segment for segment in slices if segment.elapsed_seconds > 0]


def _build_slice(
    *,
    started_at: datetime,
    ended_at: datetime,
    base_hashrate_hps: Decimal,
    multiplier: Decimal,
    paused: bool,
) -> IntervalSlice:
    elapsed_seconds = int((ended_at - started_at).total_seconds())
    effective_hashrate = Decimal("0") if paused else _quantize(base_hashrate_hps * multiplier)
    contribution_hashes = _quantize(effective_hashrate * Decimal(elapsed_seconds))
    return IntervalSlice(
        started_at=started_at,
        ended_at=ended_at,
        elapsed_seconds=elapsed_seconds,
        effective_hashrate_hps=effective_hashrate,
        contribution_hashes=contribution_hashes,
    )
