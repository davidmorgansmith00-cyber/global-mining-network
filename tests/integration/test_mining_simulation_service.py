from __future__ import annotations

import sys
import threading
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from domain.blockchain.network_stream import get_network_event_stream, reset_network_event_stream
from domain.blockchain.store import InMemoryBlockchainStateStore
from domain.difficulty.service import DifficultyAdjustmentService, DifficultyConfig
from domain.economy.ledger import NoOpLedgerPoster
from domain.mining.contracts import (
    EVENT_BLOCK_FINALIZED,
    EVENT_COOLING_STATE_CHANGED,
    EVENT_HARDWARE_CHANGED,
    EVENT_MAINTENANCE_STATE_CHANGED,
    EVENT_MODIFIER_ENDED,
    EVENT_MODIFIER_STARTED,
    EVENT_OPERATION_PAUSE,
    EVENT_POOL_MEMBERSHIP_CHANGED,
    EVENT_OPERATION_RESUME,
    EVENT_POWER_STATE_CHANGED,
    EVENT_THROTTLE_STATE_CHANGED,
    SimulationBoundaryEvent,
)
from domain.mining.service import MiningSimulationService


class MiningSimulationServiceIntegrationTests(unittest.TestCase):
    def setUp(self) -> None:
        reset_network_event_stream()

    def test_multiple_operations_contribute_to_same_active_block(self) -> None:
        started_at = datetime(2026, 8, 15, 13, 0, tzinfo=UTC)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("12"), started_at=started_at)
        service.register_operation(operation_id="op_b", base_hashrate_hps=Decimal("8"), started_at=started_at)

        result_a = service.process_tick(operation_id="op_a", ended_at=tick_end)
        result_b = service.process_tick(operation_id="op_b", ended_at=tick_end)

        self.assertEqual(result_a.active_block_number, 1)
        self.assertEqual(result_b.active_block_number, 1)
        self.assertIsNone(result_a.finalized_block_number)
        self.assertIsNone(result_b.finalized_block_number)

        expected = Decimal("120.000000") + Decimal("80.000000")
        self.assertEqual(service.blockchain_state_store.get_active_block().accumulated_work, expected)

    def test_operation_last_processed_timestamp_advances_and_boundaries_apply(self) -> None:
        started_at = datetime(2026, 8, 15, 14, 0, tzinfo=UTC)
        pause_at = started_at + timedelta(seconds=4)
        resume_at = started_at + timedelta(seconds=7)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_OPERATION_PAUSE,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=pause_at,
            )
        )
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_OPERATION_RESUME,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=resume_at,
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("70.000000"))
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_hardware_upgrade_boundary_updates_effective_hashrate_multiplier(self) -> None:
        started_at = datetime(2026, 8, 15, 14, 30, tzinfo=UTC)
        upgrade_at = started_at + timedelta(seconds=5)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_HARDWARE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=upgrade_at,
                payload={"hashrate_multiplier": "2"},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("150.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("2"))
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_throttle_and_maintenance_boundaries_update_multiplier_and_pause_state(self) -> None:
        started_at = datetime(2026, 8, 15, 14, 45, tzinfo=UTC)
        throttle_at = started_at + timedelta(seconds=3)
        maintenance_at = started_at + timedelta(seconds=6)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_THROTTLE_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=throttle_at,
                payload={"hashrate_multiplier": "0.5", "paused": False},
            )
        )
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_MAINTENANCE_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=maintenance_at,
                payload={"hashrate_multiplier": "0.5", "paused": True},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("45.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("0.5"))
        self.assertTrue(service.operations["op_a"].current_paused)
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_power_state_boundary_updates_effective_hashrate_multiplier(self) -> None:
        started_at = datetime(2026, 8, 15, 14, 50, tzinfo=UTC)
        reduced_power_at = started_at + timedelta(seconds=2)
        recovered_power_at = started_at + timedelta(seconds=6)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_POWER_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=reduced_power_at,
                payload={"hashrate_multiplier": "0.6"},
            )
        )
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_POWER_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=recovered_power_at,
                payload={"hashrate_multiplier": "1.0"},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("84.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("1.0"))
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_modifier_start_and_end_boundaries_update_multiplier_state(self) -> None:
        started_at = datetime(2026, 8, 15, 14, 55, tzinfo=UTC)
        boost_start_at = started_at + timedelta(seconds=3)
        boost_end_at = started_at + timedelta(seconds=8)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_MODIFIER_STARTED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=boost_start_at,
                payload={"hashrate_multiplier": "1.8"},
            )
        )
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_MODIFIER_ENDED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=boost_end_at,
                payload={"hashrate_multiplier": "1.0"},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("140.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("1.0"))
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_cooling_state_boundary_updates_effective_hashrate_multiplier(self) -> None:
        started_at = datetime(2026, 8, 15, 15, 0, tzinfo=UTC)
        thermal_throttle_at = started_at + timedelta(seconds=4)
        cooling_recovered_at = started_at + timedelta(seconds=9)
        tick_end = started_at + timedelta(seconds=12)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_COOLING_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=thermal_throttle_at,
                payload={"hashrate_multiplier": "0.7"},
            )
        )
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_COOLING_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=cooling_recovered_at,
                payload={"hashrate_multiplier": "1.0"},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("105.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("1.0"))
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_pool_membership_boundary_updates_effective_hashrate_multiplier(self) -> None:
        started_at = datetime(2026, 8, 15, 15, 5, tzinfo=UTC)
        joined_pool_at = started_at + timedelta(seconds=5)
        tick_end = started_at + timedelta(seconds=12)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_POOL_MEMBERSHIP_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=joined_pool_at,
                payload={"hashrate_multiplier": "1.2"},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("134.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("1.2"))
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_block_finalized_boundary_event_is_safe_noop_for_multiplier_state(self) -> None:
        started_at = datetime(2026, 8, 15, 15, 10, tzinfo=UTC)
        finalized_event_at = started_at + timedelta(seconds=4)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("1000"))
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_BLOCK_FINALIZED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=finalized_event_at,
                payload={"ignored": True},
            )
        )

        result = service.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result.contribution_hashes, Decimal("100.000000"))
        self.assertEqual(service.operations["op_a"].current_multiplier, Decimal("1"))
        self.assertFalse(service.operations["op_a"].current_paused)
        self.assertEqual(service.operations["op_a"].last_processed_at, tick_end)

    def test_same_timestamp_boundary_order_produces_deterministic_outcome(self) -> None:
        started_at = datetime(2026, 8, 15, 15, 15, tzinfo=UTC)
        collision_at = started_at + timedelta(seconds=4)
        tick_end = started_at + timedelta(seconds=10)

        service_a = MiningSimulationService(required_work=Decimal("1000"))
        service_b = MiningSimulationService(required_work=Decimal("1000"))
        service_a.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)
        service_b.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("10"), started_at=started_at)

        # Same boundary set, opposite insertion order.
        service_a.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_POWER_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=collision_at,
                payload={"hashrate_multiplier": "0.5"},
            )
        )
        service_a.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_COOLING_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=collision_at,
                payload={"hashrate_multiplier": "1.5"},
            )
        )

        service_b.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_COOLING_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=collision_at,
                payload={"hashrate_multiplier": "1.5"},
            )
        )
        service_b.apply_boundary_event(
            SimulationBoundaryEvent(
                event_type=EVENT_POWER_STATE_CHANGED,
                player_id="player_a",
                operation_id="op_a",
                occurred_at=collision_at,
                payload={"hashrate_multiplier": "0.5"},
            )
        )

        result_a = service_a.process_tick(operation_id="op_a", ended_at=tick_end)
        result_b = service_b.process_tick(operation_id="op_a", ended_at=tick_end)

        self.assertEqual(result_a.contribution_hashes, result_b.contribution_hashes)
        self.assertEqual(service_a.operations["op_a"].current_multiplier, service_b.operations["op_a"].current_multiplier)
        self.assertEqual(service_a.operations["op_a"].current_paused, service_b.operations["op_a"].current_paused)

    def test_atomic_finalization_under_concurrency(self) -> None:
        started_at = datetime(2026, 8, 15, 15, 0, tzinfo=UTC)
        tick_end = started_at + timedelta(seconds=10)

        service = MiningSimulationService(required_work=Decimal("150"))
        operation_ids = [f"op_{i}" for i in range(5)]
        for operation_id in operation_ids:
            service.register_operation(operation_id=operation_id, base_hashrate_hps=Decimal("5"), started_at=started_at)

        results: list[tuple[str, int | None]] = []
        results_lock = threading.Lock()

        def run_tick(operation_id: str) -> None:
            tick_result = service.process_tick(operation_id=operation_id, ended_at=tick_end)
            with results_lock:
                results.append((operation_id, tick_result.finalized_block_number))

        threads = [threading.Thread(target=run_tick, args=(operation_id,)) for operation_id in operation_ids]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join()

        finalized = [item for _, item in results if item is not None]
        self.assertEqual(finalized, [1])
        self.assertEqual(service.finalized_block_numbers, [1])
        self.assertEqual(service.blockchain_state_store.get_active_block().block_number, 2)
        self.assertEqual(service.blockchain_state_store.get_active_block().accumulated_work, Decimal("100.000000"))

    def test_difficulty_adjusts_next_required_work_from_finalized_history(self) -> None:
        started_at = datetime(2026, 8, 15, 19, 0, tzinfo=UTC)
        difficulty_service = DifficultyAdjustmentService(
            DifficultyConfig(
                target_block_seconds=10,
                history_window_size=10,
                max_upward_adjustment_pct=Decimal("0.20"),
                max_downward_adjustment_pct=Decimal("0.20"),
            )
        )
        block_store = InMemoryBlockchainStateStore(
            required_work=Decimal("100"),
            difficulty_adjuster=difficulty_service,
        )
        ledger = NoOpLedgerPoster()
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=block_store,
            ledger_poster=ledger,
        )
        service.register_operation(operation_id="op_a", base_hashrate_hps=Decimal("50"), started_at=started_at)

        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=2))
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=4))

        self.assertEqual(block_store.get_active_block().required_work, Decimal("120.000000"))
        self.assertEqual(len(ledger.entries), 2)
        self.assertEqual(ledger.entries[0].reward_amount, Decimal("100.000000"))
        self.assertEqual(ledger.entries[1].reward_amount, Decimal("100.000000"))

    def test_player_rewards_allocate_by_contribution_share(self) -> None:
        started_at = datetime(2026, 8, 15, 20, 0, tzinfo=UTC)
        ledger = NoOpLedgerPoster()
        service = MiningSimulationService(required_work=Decimal("100"), ledger_poster=ledger)
        service.register_operation(
            operation_id="op_a",
            player_id="player_a",
            base_hashrate_hps=Decimal("8"),
            started_at=started_at,
        )
        service.register_operation(
            operation_id="op_b",
            player_id="player_b",
            base_hashrate_hps=Decimal("2"),
            started_at=started_at,
        )

        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=10))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=10))

        by_player = {entry.player_id: entry.reward_amount for entry in ledger.player_entries if entry.block_number == 1}
        self.assertEqual(by_player["player_a"], Decimal("80.000000"))
        self.assertEqual(by_player["player_b"], Decimal("20.000000"))
        by_player_contribution = {
            entry.player_id: entry.contribution_hashes for entry in ledger.player_entries if entry.block_number == 1
        }
        self.assertEqual(by_player_contribution["player_a"], Decimal("80.000000"))
        self.assertEqual(by_player_contribution["player_b"], Decimal("20.000000"))

    def test_tick_publishes_progress_and_finalization_events(self) -> None:
        started_at = datetime(2026, 8, 15, 20, 30, tzinfo=UTC)
        service = MiningSimulationService(required_work=Decimal("100"), ledger_poster=NoOpLedgerPoster())
        service.register_operation(
            operation_id="op_a",
            player_id="player_a",
            base_hashrate_hps=Decimal("20"),
            started_at=started_at,
        )

        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        events = get_network_event_stream().list_after(after_sequence=None, limit=10)
        event_types = [item.event_type for item in events]
        self.assertIn("network.block_progress.v1", event_types)
        self.assertIn("network.block_finalized.v1", event_types)

    def test_deterministic_replay_produces_identical_settlement_outcomes(self) -> None:
        started_at = datetime(2026, 8, 15, 21, 0, tzinfo=UTC)

        def run_sequence() -> tuple[tuple[int, Decimal, Decimal], list[int], list[tuple[int, Decimal]], list[tuple[int, str, Decimal, Decimal]]]:
            ledger = NoOpLedgerPoster()
            service = MiningSimulationService(required_work=Decimal("100"), ledger_poster=ledger)
            service.register_operation(
                operation_id="op_a",
                player_id="player_a",
                base_hashrate_hps=Decimal("12"),
                started_at=started_at,
            )
            service.register_operation(
                operation_id="op_b",
                player_id="player_b",
                base_hashrate_hps=Decimal("8"),
                started_at=started_at,
            )
            service.apply_boundary_event(
                SimulationBoundaryEvent(
                    event_type=EVENT_OPERATION_PAUSE,
                    player_id="player_a",
                    operation_id="op_a",
                    occurred_at=started_at + timedelta(seconds=4),
                )
            )
            service.apply_boundary_event(
                SimulationBoundaryEvent(
                    event_type=EVENT_OPERATION_RESUME,
                    player_id="player_a",
                    operation_id="op_a",
                    occurred_at=started_at + timedelta(seconds=7),
                )
            )

            for tick_offset in (5, 10, 15):
                tick_end = started_at + timedelta(seconds=tick_offset)
                service.process_tick(operation_id="op_a", ended_at=tick_end)
                service.process_tick(operation_id="op_b", ended_at=tick_end)

            active = service.blockchain_state_store.get_active_block()
            active_snapshot = (active.block_number, active.required_work, active.accumulated_work)
            finalized_blocks = list(service.finalized_block_numbers)
            reward_pool_entries = [(entry.block_number, entry.reward_amount) for entry in ledger.entries]
            player_reward_entries = [
                (
                    entry.block_number,
                    entry.player_id,
                    entry.reward_amount,
                    entry.contribution_hashes,
                )
                for entry in ledger.player_entries
            ]
            return active_snapshot, finalized_blocks, reward_pool_entries, player_reward_entries

        first_run = run_sequence()
        second_run = run_sequence()

        self.assertEqual(first_run, second_run)


if __name__ == "__main__":
    unittest.main(verbosity=2)