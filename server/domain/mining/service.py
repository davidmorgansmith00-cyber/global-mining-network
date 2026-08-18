from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock
from typing import Protocol

from domain.blockchain.store import InMemoryBlockchainStateStore
from domain.blockchain.network_stream import get_network_event_stream
from domain.economy.ledger import NoOpLedgerPoster
from domain.economy.reward_settlement import RewardSettlementService
from domain.mining.contracts import (
    EVENT_COOLING_STATE_CHANGED,
    EVENT_HARDWARE_CHANGED,
    EVENT_MAINTENANCE_STATE_CHANGED,
    EVENT_MODIFIER_ENDED,
    EVENT_MODIFIER_STARTED,
    EVENT_OPERATION_PAUSE,
    EVENT_OPERATION_RESUME,
    EVENT_POOL_MEMBERSHIP_CHANGED,
    EVENT_POWER_STATE_CHANGED,
    EVENT_THROTTLE_STATE_CHANGED,
    SimulationBoundaryEvent,
)
from domain.mining.interval_slicer import IntervalBoundaryState, slice_progression_intervals
from shared.time import SystemUtcClock, UtcClock


class NetworkEventPublisher(Protocol):
    def publish(self, *, event_type: str, payload: dict[str, object]) -> object: ...


def _to_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)


def _boundary_sort_key(boundary: IntervalBoundaryState) -> tuple[datetime, int, str]:
    return (boundary.occurred_at, int(boundary.paused), str(boundary.hashrate_multiplier))


@dataclass
class MiningOperationState:
    operation_id: str
    player_id: str
    base_hashrate_hps: Decimal
    last_processed_at: datetime
    current_multiplier: Decimal = Decimal("1")
    current_paused: bool = False
    pending_boundaries: list[IntervalBoundaryState] = field(default_factory=list)


@dataclass
class ActiveBlockState:
    block_number: int
    required_work: Decimal
    accumulated_work: Decimal = Decimal("0")


@dataclass
class TickResult:
    operation_id: str
    active_block_number: int
    contribution_hashes: Decimal
    finalized_block_number: int | None = None


@dataclass(frozen=True)
class OfflineProgressionResult:
    window_started_at: datetime
    window_ended_at: datetime
    simulated_work: Decimal
    credited_work: Decimal
    cap_limit: Decimal
    cap_applied: bool
    cap_amount: Decimal
    offline_cap_tier: int


class MiningSimulationService:
    def __init__(
        self,
        *,
        required_work: Decimal,
        clock: UtcClock | None = None,
        blockchain_state_store: object | None = None,
        ledger_poster: object | None = None,
        reward_settlement_service: RewardSettlementService | None = None,
        network_event_stream: NetworkEventPublisher | None = None,
    ) -> None:
        self.clock = clock or SystemUtcClock()
        self.blockchain_state_store = blockchain_state_store or InMemoryBlockchainStateStore(required_work=required_work)
        self.ledger_poster = ledger_poster or NoOpLedgerPoster()
        self.reward_settlement_service = reward_settlement_service or RewardSettlementService()
        self.network_event_stream = network_event_stream or get_network_event_stream()
        self.operations: dict[str, MiningOperationState] = {}
        self.finalized_block_numbers: list[int] = []
        self._block_contributions: dict[int, dict[str, Decimal]] = {}
        self._lock = Lock()

    def register_operation(
        self,
        *,
        operation_id: str,
        player_id: str | None = None,
        base_hashrate_hps: Decimal,
        started_at: datetime | None = None,
    ) -> None:
        at = _to_utc(started_at or self.clock.now())
        self.operations[operation_id] = MiningOperationState(
            operation_id=operation_id,
            player_id=player_id or operation_id,
            base_hashrate_hps=base_hashrate_hps,
            last_processed_at=at,
        )

    def get_operation_state(self, *, operation_id: str) -> MiningOperationState | None:
        return self.operations.get(operation_id)

    def stop_operation(self, *, operation_id: str) -> bool:
        if operation_id not in self.operations:
            return False
        del self.operations[operation_id]
        return True

    def apply_boundary_event(self, event: SimulationBoundaryEvent) -> None:
        operation = self.operations.get(event.operation_id)
        if operation is None:
            raise ValueError("Operation not found for boundary event")

        occurred_at = _to_utc(event.occurred_at)
        multiplier = operation.current_multiplier
        paused = operation.current_paused

        if event.event_type == EVENT_OPERATION_PAUSE:
            paused = True
        elif event.event_type == EVENT_OPERATION_RESUME:
            paused = False
        elif event.event_type in {
            EVENT_HARDWARE_CHANGED,
            EVENT_POWER_STATE_CHANGED,
            EVENT_COOLING_STATE_CHANGED,
            EVENT_POOL_MEMBERSHIP_CHANGED,
            EVENT_MODIFIER_STARTED,
            EVENT_MODIFIER_ENDED,
            EVENT_MAINTENANCE_STATE_CHANGED,
            EVENT_THROTTLE_STATE_CHANGED,
        }:
            raw_multiplier = event.payload.get("hashrate_multiplier", operation.current_multiplier)
            multiplier = Decimal(str(raw_multiplier))
            if "paused" in event.payload:
                paused = bool(event.payload["paused"])

        operation.pending_boundaries.append(
            IntervalBoundaryState(
                occurred_at=occurred_at,
                hashrate_multiplier=multiplier,
                paused=paused,
            )
        )

    @staticmethod
    def simulate_offline_progress(
        *,
        window_started_at: datetime,
        window_ended_at: datetime,
        effective_hashrate_hps: Decimal,
        cap_limit: Decimal,
        offline_cap_tier: int,
    ) -> OfflineProgressionResult:
        started_at = _to_utc(window_started_at)
        ended_at = _to_utc(window_ended_at)
        if ended_at <= started_at:
            return OfflineProgressionResult(
                window_started_at=started_at,
                window_ended_at=ended_at,
                simulated_work=Decimal("0"),
                credited_work=Decimal("0"),
                cap_limit=max(cap_limit, Decimal("0")),
                cap_applied=False,
                cap_amount=Decimal("0"),
                offline_cap_tier=max(1, offline_cap_tier),
            )

        slices = slice_progression_intervals(
            window_started_at=started_at,
            window_ended_at=ended_at,
            base_hashrate_hps=max(effective_hashrate_hps, Decimal("0")),
            boundary_states=[],
        )
        simulated_work = sum((segment.contribution_hashes for segment in slices), Decimal("0"))
        resolved_cap_limit = max(cap_limit, Decimal("0"))
        credited_work = min(simulated_work, resolved_cap_limit)
        cap_applied = simulated_work > resolved_cap_limit
        cap_amount = simulated_work - credited_work

        return OfflineProgressionResult(
            window_started_at=started_at,
            window_ended_at=ended_at,
            simulated_work=simulated_work,
            credited_work=credited_work,
            cap_limit=resolved_cap_limit,
            cap_applied=cap_applied,
            cap_amount=cap_amount,
            offline_cap_tier=max(1, offline_cap_tier),
        )

    def process_tick(self, *, operation_id: str, ended_at: datetime | None = None) -> TickResult:
        operation = self.operations.get(operation_id)
        if operation is None:
            raise ValueError("Operation not registered")

        tick_end = _to_utc(ended_at or self.clock.now())
        if tick_end <= operation.last_processed_at:
            return TickResult(
                operation_id=operation_id,
                active_block_number=self.blockchain_state_store.get_active_block().block_number,
                contribution_hashes=Decimal("0"),
            )

        boundaries_for_window = [
            item
            for item in operation.pending_boundaries
            if operation.last_processed_at <= item.occurred_at < tick_end
        ]
        boundaries_for_window.sort(key=_boundary_sort_key)
        retained_boundaries = [item for item in operation.pending_boundaries if item.occurred_at >= tick_end]

        slices = slice_progression_intervals(
            window_started_at=operation.last_processed_at,
            window_ended_at=tick_end,
            base_hashrate_hps=operation.base_hashrate_hps,
            boundary_states=boundaries_for_window,
            starting_multiplier=operation.current_multiplier,
            starting_paused=operation.current_paused,
        )

        contribution = sum((segment.contribution_hashes for segment in slices), Decimal("0"))
        operation.last_processed_at = tick_end
        operation.pending_boundaries = retained_boundaries
        if boundaries_for_window:
            latest_boundary = boundaries_for_window[-1]
            operation.current_multiplier = latest_boundary.hashrate_multiplier
            operation.current_paused = latest_boundary.paused

        with self._lock:
            active_before = self.blockchain_state_store.get_active_block()
            work_remaining_for_block = max(active_before.required_work - active_before.accumulated_work, Decimal("0"))
            outcome = self.blockchain_state_store.add_work(contribution=contribution, finalized_at=tick_end)

            finalized_contribution = contribution
            carryover_contribution = Decimal("0")
            if outcome.finalized_block_number is not None:
                finalized_contribution = min(contribution, work_remaining_for_block)
                carryover_contribution = contribution - finalized_contribution

            self._add_player_contribution(
                block_number=active_before.block_number,
                player_id=operation.player_id,
                amount=finalized_contribution,
            )
            if carryover_contribution > 0:
                self._add_player_contribution(
                    block_number=active_before.block_number + 1,
                    player_id=operation.player_id,
                    amount=carryover_contribution,
                )

            finalized_block_number = outcome.finalized_block_number
            if finalized_block_number is not None:
                self.finalized_block_numbers.append(finalized_block_number)
                finalized_contributions = self._block_contributions.pop(finalized_block_number, {})
                reward_amount = self.reward_settlement_service.compute_block_reward(
                    required_work=outcome.required_work,
                    total_work=outcome.total_work,
                )
                rewards_by_player = self.reward_settlement_service.allocate_player_rewards(
                    total_reward=reward_amount,
                    contributions_by_player=finalized_contributions,
                )
                self.ledger_poster.post_block_finalization(
                    block_number=finalized_block_number,
                    required_work=outcome.required_work,
                    total_work=outcome.total_work,
                    reward_amount=reward_amount,
                    posted_at=tick_end,
                )
                self.ledger_poster.post_player_reward_entries(
                    block_number=finalized_block_number,
                    rewards_by_player=rewards_by_player,
                    contributions_by_player=finalized_contributions,
                    posted_at=tick_end,
                )
                for player_id, player_reward in rewards_by_player.items():
                    self.network_event_stream.publish(
                        event_type="network.player_reward.v1",
                        payload={
                            "block_number": finalized_block_number,
                            "player_id": player_id,
                            "reward_amount": str(player_reward),
                            "contribution_hashes": str(finalized_contributions.get(player_id, Decimal("0"))),
                        },
                    )
                self.network_event_stream.publish(
                    event_type="network.block_finalized.v1",
                    payload={
                        "block_number": finalized_block_number,
                        "required_work": str(outcome.required_work),
                        "total_work": str(outcome.total_work),
                        "reward_pool_amount": str(reward_amount),
                        "player_count": len(rewards_by_player),
                    },
                )

            active_after = self.blockchain_state_store.get_active_block()
            self.network_event_stream.publish(
                event_type="network.block_progress.v1",
                payload={
                    "block_number": active_after.block_number,
                    "required_work": str(active_after.required_work),
                    "accumulated_work": str(active_after.accumulated_work),
                    "operation_id": operation.operation_id,
                    "player_id": operation.player_id,
                    "contribution_hashes": str(contribution),
                },
            )

            return TickResult(
                operation_id=operation_id,
                active_block_number=outcome.active_block_number_before,
                contribution_hashes=contribution,
                finalized_block_number=finalized_block_number,
            )

    def _add_player_contribution(self, *, block_number: int, player_id: str, amount: Decimal) -> None:
        if amount <= 0:
            return
        block_bucket = self._block_contributions.setdefault(block_number, {})
        block_bucket[player_id] = block_bucket.get(player_id, Decimal("0")) + amount
