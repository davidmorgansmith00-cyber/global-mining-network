from __future__ import annotations

import os
import sys
import time
import unittest
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from pathlib import Path
from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SERVER_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVER_ROOT))

from app.main import app
from api.v1.blockchain import reset_blockchain_runtime_counters_for_tests
from domain.auth.schemas import RegisterRequest
from domain.auth.service import AuthService
from domain.blockchain.network_stream import reset_network_event_stream
from domain.blockchain.store import PostgresBlockchainStateStore
from domain.economy.ledger import PostgresLedgerPoster
from domain.mining.service import MiningSimulationService
from shared.settings import settings
from tools.apply_migrations import apply_migrations


DEFAULT_DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/global_mining_network"


class BlockchainStatusApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        os.environ.setdefault("DATABASE_URL", DEFAULT_DATABASE_URL)
        cls.database_url = os.environ["DATABASE_URL"]
        apply_migrations()

    def setUp(self) -> None:
        reset_network_event_stream()
        reset_blockchain_runtime_counters_for_tests()
        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM client_event_checkpoints")
                cursor.execute("DELETE FROM economy_player_ledger_entries")
                cursor.execute("DELETE FROM economy_ledger_entries")
                cursor.execute("DELETE FROM blockchain_finalized_blocks")
                cursor.execute("DELETE FROM blockchain_active_block")
            connection.commit()

    def _create_player_session_binding(self) -> tuple[str, str]:
        email = f"ws_bind_{datetime.now(UTC).timestamp()}@example.com"
        auth = AuthService()
        registered = auth.register(RegisterRequest(email=email, password="password123"))
        player_id = registered.player_id

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT session_id
                    FROM auth_sessions
                    WHERE player_id = %s
                    ORDER BY created_at DESC
                    LIMIT 1
                    """,
                    (UUID(player_id),),
                )
                row = cursor.fetchone()
        return player_id, str(row[0])

    def test_status_endpoint_returns_active_progress_and_recent_outcomes(self) -> None:
        started_at = datetime(2026, 8, 15, 21, 0, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            response = client.get("/api/v1/blockchain/status?recent_limit=5")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["active_block_number"], 2)
        self.assertEqual(payload["active_required_work"], "100.000000")
        self.assertEqual(payload["active_accumulated_work"], "0.000000")
        self.assertEqual(payload["active_progress_ratio"], "0.000000")
        self.assertEqual(len(payload["recent_outcomes"]), 1)
        self.assertEqual(payload["recent_outcomes"][0]["block_number"], 1)
        self.assertEqual(payload["recent_outcomes"][0]["reward_pool_amount"], "100.000000")
        self.assertEqual(payload["recent_outcomes"][0]["player_reward_amount"], "100.000000")

    def test_status_endpoint_rejects_out_of_range_recent_limit(self) -> None:
        with TestClient(app) as client:
            below_min = client.get("/api/v1/blockchain/status?recent_limit=0")
            above_max = client.get("/api/v1/blockchain/status?recent_limit=101")

        self.assertEqual(below_min.status_code, 422)
        self.assertEqual(above_max.status_code, 422)

    def test_finalized_reward_pool_amount_is_consistent_across_status_events_and_ledger(self) -> None:
        started_at = datetime(2026, 8, 15, 21, 10, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("25"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=4))

        with TestClient(app) as client:
            status_response = client.get("/api/v1/blockchain/status?recent_limit=5")
            events_response = client.get("/api/v1/blockchain/network-events?limit=50")

        self.assertEqual(status_response.status_code, 200)
        self.assertEqual(events_response.status_code, 200)

        status_payload = status_response.json()
        latest_status_outcome = status_payload["recent_outcomes"][0]

        event_payload = events_response.json()
        finalized_events = [
            item for item in event_payload["events"]
            if item.get("event_type") == "network.block_finalized.v1"
        ]
        self.assertGreaterEqual(len(finalized_events), 1)
        latest_finalized_event = finalized_events[-1]["payload"]

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT reference_block_number, amount
                    FROM economy_ledger_entries
                    WHERE entry_type = 'block.finalized.reward_pool.v1'
                    ORDER BY created_at DESC
                    LIMIT 1
                    """
                )
                ledger_row = cursor.fetchone()

        self.assertIsNotNone(ledger_row)
        ledger_block_number = ledger_row[0]
        ledger_amount = ledger_row[1]

        self.assertEqual(int(latest_status_outcome["block_number"]), ledger_block_number)
        self.assertEqual(int(latest_finalized_event["block_number"]), ledger_block_number)
        self.assertEqual(Decimal(latest_status_outcome["reward_pool_amount"]), ledger_amount)
        self.assertEqual(Decimal(latest_finalized_event["reward_pool_amount"]), ledger_amount)

    def test_player_reward_history_endpoint_returns_contribution_transparency(self) -> None:
        started_at = datetime(2026, 8, 15, 21, 30, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            response = client.get("/api/v1/blockchain/players/player_a/rewards?recent_limit=10")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["player_id"], "player_a")
        self.assertEqual(payload["total_rewards"], "100.000000")
        self.assertEqual(payload["total_contribution_hashes"], "100.000000")
        self.assertEqual(len(payload["entries"]), 1)
        self.assertEqual(payload["entries"][0]["block_number"], 1)
        self.assertEqual(payload["entries"][0]["reward_amount"], "100.000000")
        self.assertEqual(payload["entries"][0]["contribution_hashes"], "100.000000")

    def test_player_reward_history_endpoint_rejects_out_of_range_recent_limit(self) -> None:
        with TestClient(app) as client:
            below_min = client.get("/api/v1/blockchain/players/player_a/rewards?recent_limit=0")
            above_max = client.get("/api/v1/blockchain/players/player_a/rewards?recent_limit=201")

        self.assertEqual(below_min.status_code, 422)
        self.assertEqual(above_max.status_code, 422)

    def test_player_reward_balances_endpoint_replays_immutable_ledger_totals(self) -> None:
        started_at = datetime(2026, 8, 15, 21, 45, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("8"), started_at=started_at)
        service.register_operation(operation_id="op_b", player_id="player_b", base_hashrate_hps=Decimal("2"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=10))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=10))

        with TestClient(app) as client:
            response = client.get("/api/v1/blockchain/reward-balances")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_reward_balance"], "100.000000")
        self.assertEqual(len(payload["entries"]), 2)

        by_player = {item["player_id"]: item["reward_balance"] for item in payload["entries"]}
        self.assertEqual(by_player["player_a"], "80.000000")
        self.assertEqual(by_player["player_b"], "20.000000")

    def test_player_reward_balances_endpoint_returns_empty_projection_when_no_rewards_exist(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/blockchain/reward-balances")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["total_reward_balance"], "0")
        self.assertEqual(payload["entries"], [])

    def test_reward_balances_are_consistent_with_player_reward_history_totals(self) -> None:
        started_at = datetime(2026, 8, 15, 21, 50, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("7"), started_at=started_at)
        service.register_operation(operation_id="op_b", player_id="player_b", base_hashrate_hps=Decimal("3"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=10))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=10))

        with TestClient(app) as client:
            balances_response = client.get("/api/v1/blockchain/reward-balances")
            history_a = client.get("/api/v1/blockchain/players/player_a/rewards?recent_limit=10")
            history_b = client.get("/api/v1/blockchain/players/player_b/rewards?recent_limit=10")

        self.assertEqual(balances_response.status_code, 200)
        self.assertEqual(history_a.status_code, 200)
        self.assertEqual(history_b.status_code, 200)

        balances_payload = balances_response.json()
        by_player = {item["player_id"]: item["reward_balance"] for item in balances_payload["entries"]}
        self.assertEqual(by_player["player_a"], history_a.json()["total_rewards"])
        self.assertEqual(by_player["player_b"], history_b.json()["total_rewards"])

        expected_total = Decimal(history_a.json()["total_rewards"]) + Decimal(history_b.json()["total_rewards"])
        self.assertEqual(Decimal(balances_payload["total_reward_balance"]), expected_total)

    def test_network_snapshot_endpoint_returns_websocket_ready_contract(self) -> None:
        started_at = datetime(2026, 8, 15, 22, 0, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            response = client.get("/api/v1/blockchain/network-snapshot?recent_limit=5")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "network.snapshot.v1")
        self.assertEqual(payload["active_block_number"], 2)
        self.assertEqual(payload["active_progress_ratio"], "0.000000")
        self.assertGreaterEqual(payload["snapshot_sequence"], 2)
        self.assertEqual(payload["reconnect_cursor"], payload["snapshot_sequence"])
        self.assertEqual(len(payload["recent_finalizations"]), 1)
        self.assertEqual(payload["recent_finalizations"][0]["block_number"], 1)
        self.assertEqual(payload["recent_finalizations"][0]["reward_pool_amount"], "100.000000")

    def test_network_snapshot_endpoint_rejects_out_of_range_recent_limit(self) -> None:
        with TestClient(app) as client:
            below_min = client.get("/api/v1/blockchain/network-snapshot?recent_limit=0")
            above_max = client.get("/api/v1/blockchain/network-snapshot?recent_limit=101")

        self.assertEqual(below_min.status_code, 422)
        self.assertEqual(above_max.status_code, 422)

    def test_network_events_endpoint_supports_cursor_based_reconnect(self) -> None:
        started_at = datetime(2026, 8, 15, 22, 30, tzinfo=UTC)
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id="player_a", base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            first = client.get("/api/v1/blockchain/network-events?limit=10")
            self.assertEqual(first.status_code, 200)
            first_payload = first.json()
            self.assertEqual(first_payload["schema_version"], "network.events.v1")
            self.assertGreaterEqual(first_payload["latest_sequence"], 2)
            self.assertGreaterEqual(len(first_payload["events"]), 2)

            reconnect_cursor = first_payload["reconnect_cursor"]
            second = client.get(f"/api/v1/blockchain/network-events?after_sequence={reconnect_cursor}&limit=10")

        self.assertEqual(second.status_code, 200)
        second_payload = second.json()
        self.assertEqual(second_payload["events"], [])
        self.assertEqual(second_payload["reconnect_cursor"], reconnect_cursor)

    def test_network_events_endpoint_rejects_negative_after_sequence(self) -> None:
        with TestClient(app) as client:
            response = client.get("/api/v1/blockchain/network-events?after_sequence=-1&limit=10")

        self.assertEqual(response.status_code, 422)

    def test_network_events_endpoint_rejects_out_of_range_limit(self) -> None:
        with TestClient(app) as client:
            below_min = client.get("/api/v1/blockchain/network-events?after_sequence=0&limit=0")
            above_max = client.get("/api/v1/blockchain/network-events?after_sequence=0&limit=501")

        self.assertEqual(below_min.status_code, 422)
        self.assertEqual(above_max.status_code, 422)

    def test_network_events_websocket_streams_cursor_based_payloads(self) -> None:
        started_at = datetime(2026, 8, 15, 23, 0, tzinfo=UTC)
        player_id, session_id = self._create_player_session_binding()
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id=player_id, base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=10"
                f"&player_id={player_id}&session_id={session_id}&channel=global"
            ) as websocket:
                payload = websocket.receive_json()

        self.assertEqual(payload["schema_version"], "network.events.v1")
        self.assertGreaterEqual(payload["latest_sequence"], 2)
        self.assertGreaterEqual(len(payload["events"]), 2)

    def test_operation_intent_progress_events_stream_over_authenticated_global_websocket(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_ws_runtime_1",
                    "base_hashrate_hps": "35",
                },
            )
            self.assertEqual(started.status_code, 200)

            # Operation progress is emitted on integer-second slices.
            time.sleep(1.1)
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=100"
                f"&player_id={player_id}&session_id={session_id}&channel=global"
            ) as websocket:
                payload = websocket.receive_json()

        self.assertEqual(payload["schema_version"], "network.events.v1")
        progress_events = [
            item for item in payload["events"]
            if item.get("event_type") == "network.block_progress.v1"
            and item.get("payload", {}).get("operation_id") == "op_ws_runtime_1"
            and item.get("payload", {}).get("player_id") == player_id
        ]
        self.assertGreaterEqual(len(progress_events), 1)

    def test_operation_stop_prevents_new_progress_events_on_websocket_reconnect(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_ws_stop_1",
                    "base_hashrate_hps": "30",
                },
            )
            self.assertEqual(started.status_code, 200)

            time.sleep(1.1)
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=100"
                f"&player_id={player_id}&session_id={session_id}&channel=global"
            ) as websocket:
                first_payload = websocket.receive_json()

            progress_events = [
                item for item in first_payload["events"]
                if item.get("event_type") == "network.block_progress.v1"
                and item.get("payload", {}).get("operation_id") == "op_ws_stop_1"
                and item.get("payload", {}).get("player_id") == player_id
            ]
            self.assertGreaterEqual(len(progress_events), 1)

            reconnect_cursor = int(first_payload["reconnect_cursor"])
            stopped = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                json={
                    "operation_id": "op_ws_stop_1",
                },
            )
            self.assertEqual(stopped.status_code, 200)

            time.sleep(1.1)
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence={reconnect_cursor}&limit=100"
                f"&player_id={player_id}&session_id={session_id}&channel=global"
            ) as websocket:
                second_payload = websocket.receive_json()

        self.assertEqual(second_payload["schema_version"], "network.events.v1")
        self.assertEqual(second_payload["events"], [])
        self.assertEqual(second_payload["reconnect_cursor"], reconnect_cursor)

    def test_cleanup_endpoint_applies_retention_policies(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO network_events (event_type, payload, occurred_at)
                    VALUES
                        (%s, %s::jsonb, NOW() - INTERVAL '3 days'),
                        (%s, %s::jsonb, NOW() - INTERVAL '2 days'),
                        (%s, %s::jsonb, NOW() - INTERVAL '1 hour')
                    """,
                    (
                        "network.block_progress.v1",
                        '{"a":1}',
                        "network.block_progress.v1",
                        '{"a":2}',
                        "network.block_progress.v1",
                        '{"a":3}',
                    ),
                )
                cursor.execute(
                    """
                    INSERT INTO client_event_checkpoints
                        (checkpoint_id, player_id, session_id, channel, reconnect_cursor, updated_at)
                    VALUES
                        (%s, %s, %s, %s, %s, NOW() - INTERVAL '20 days'),
                        (%s, %s, %s, %s, %s, NOW())
                    """,
                    (
                        str(uuid4()),
                        player_id,
                        session_id,
                        "global",
                        1,
                        str(uuid4()),
                        player_id,
                        session_id,
                        "player_rewards",
                        2,
                    ),
                )
            connection.commit()

        with TestClient(app) as client:
            response = client.post(
                "/api/v1/blockchain/maintenance/cleanup"
                "?event_retention_seconds=172800"
                "&checkpoint_retention_seconds=604800"
                "&max_network_events=1",
                headers={settings.maintenance_auth_header: settings.maintenance_auth_token},
            )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertGreaterEqual(payload["deleted_network_events_by_age"], 1)
        self.assertGreaterEqual(payload["deleted_network_events_by_count"], 0)
        self.assertEqual(payload["deleted_client_checkpoints"], 1)

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute("SELECT COUNT(*) FROM network_events")
                self.assertEqual(cursor.fetchone()[0], 1)
                cursor.execute("SELECT COUNT(*) FROM client_event_checkpoints")
                self.assertEqual(cursor.fetchone()[0], 1)

    def test_cleanup_endpoint_rejects_unauthorized_requests(self) -> None:
        with TestClient(app) as client:
            unauthorized = client.post("/api/v1/blockchain/maintenance/cleanup")
            headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
            authorized_metrics = client.get("/api/v1/blockchain/maintenance/metrics", headers=headers)

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized_metrics.status_code, 200)
        payload = authorized_metrics.json()
        self.assertGreaterEqual(
            payload["maintenance_auth_scope_requests_total"].get(
                settings.maintenance_auth_unknown_token_scope_label,
                0,
            ),
            1,
        )

    def test_cleanup_endpoint_rejects_out_of_range_query_parameters(self) -> None:
        headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
        with TestClient(app) as client:
            event_retention_too_low = client.post(
                "/api/v1/blockchain/maintenance/cleanup?event_retention_seconds=59",
                headers=headers,
            )
            checkpoint_retention_too_low = client.post(
                "/api/v1/blockchain/maintenance/cleanup?checkpoint_retention_seconds=59",
                headers=headers,
            )
            max_network_events_too_low = client.post(
                "/api/v1/blockchain/maintenance/cleanup?max_network_events=0",
                headers=headers,
            )

        self.assertEqual(event_retention_too_low.status_code, 422)
        self.assertEqual(checkpoint_retention_too_low.status_code, 422)
        self.assertEqual(max_network_events_too_low.status_code, 422)

    def test_operation_start_intent_endpoint_enforces_server_authoritative_binding(self) -> None:
        player_a, session_a = self._create_player_session_binding()
        _, session_b = self._create_player_session_binding()

        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_client_1",
                    "base_hashrate_hps": "25",
                },
            )
            started_again = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_client_1",
                    "base_hashrate_hps": "99",
                },
            )
            player_conflict = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_b}",
                json={
                    "operation_id": "op_client_1",
                    "base_hashrate_hps": "25",
                },
            )
            forbidden_extra = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_client_2",
                    "base_hashrate_hps": "25",
                    "authoritative_accumulated_work": "99999",
                },
            )
            invalid_session = client.post(
                "/api/v1/blockchain/operations/intents/start?session_id=not-a-session",
                json={
                    "operation_id": "op_client_3",
                    "base_hashrate_hps": "25",
                },
            )

        self.assertEqual(started.status_code, 200)
        started_payload = started.json()
        self.assertEqual(started_payload["operation_id"], "op_client_1")
        self.assertEqual(started_payload["player_id"], player_a)
        self.assertTrue(started_payload["accepted"])
        self.assertEqual(started_payload["status"], "started")
        self.assertEqual(started_payload["detail"], "Operation start intent accepted")
        self.assertEqual(started_again.status_code, 200)
        started_again_payload = started_again.json()
        self.assertEqual(started_again_payload["operation_id"], "op_client_1")
        self.assertEqual(started_again_payload["player_id"], player_a)
        self.assertTrue(started_again_payload["accepted"])
        self.assertEqual(started_again_payload["status"], "already_running")
        self.assertEqual(started_again_payload["detail"], "Operation intent accepted; operation is already active")
        self.assertEqual(player_conflict.status_code, 409)
        self.assertEqual(forbidden_extra.status_code, 422)
        self.assertEqual(invalid_session.status_code, 401)

    def test_operation_start_intent_rejects_non_positive_hashrate(self) -> None:
        _, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            zero_hashrate = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_invalid_hashrate_zero",
                    "base_hashrate_hps": "0",
                },
            )
            negative_hashrate = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_invalid_hashrate_negative",
                    "base_hashrate_hps": "-5",
                },
            )

        self.assertEqual(zero_hashrate.status_code, 400)
        self.assertEqual(negative_hashrate.status_code, 400)
        self.assertEqual(zero_hashrate.json()["detail"], "base_hashrate_hps must be positive")
        self.assertEqual(negative_hashrate.json()["detail"], "base_hashrate_hps must be positive")

    def test_operation_start_intent_rejects_missing_required_fields(self) -> None:
        _, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            missing_operation_id = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "base_hashrate_hps": "25",
                },
            )
            missing_base_hashrate = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_missing_hashrate",
                },
            )

        self.assertEqual(missing_operation_id.status_code, 422)
        self.assertEqual(missing_base_hashrate.status_code, 422)

    def test_operation_stop_intent_endpoint_enforces_player_binding_and_state_transition(self) -> None:
        _, session_a = self._create_player_session_binding()
        _, session_b = self._create_player_session_binding()

        with TestClient(app) as client:
            not_found = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_a}",
                json={
                    "operation_id": "op_missing",
                },
            )
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_stop_1",
                    "base_hashrate_hps": "40",
                },
            )
            wrong_player_stop = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_b}",
                json={
                    "operation_id": "op_stop_1",
                },
            )
            stopped = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_a}",
                json={
                    "operation_id": "op_stop_1",
                },
            )
            stopped_again = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_a}",
                json={
                    "operation_id": "op_stop_1",
                },
            )
            invalid_session = client.post(
                "/api/v1/blockchain/operations/intents/stop?session_id=not-a-session",
                json={
                    "operation_id": "op_stop_1",
                },
            )

        self.assertEqual(not_found.status_code, 404)
        self.assertEqual(started.status_code, 200)
        self.assertEqual(wrong_player_stop.status_code, 409)
        self.assertEqual(stopped.status_code, 200)
        stopped_payload = stopped.json()
        self.assertEqual(stopped_payload["operation_id"], "op_stop_1")
        self.assertTrue(stopped_payload["accepted"])
        self.assertEqual(stopped_payload["status"], "stopped")
        self.assertEqual(stopped_payload["detail"], "Operation stop intent accepted")
        self.assertEqual(stopped_again.status_code, 404)
        self.assertEqual(invalid_session.status_code, 401)

    def test_operation_stop_intent_rejects_missing_required_fields(self) -> None:
        _, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            missing_operation_id = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                json={},
            )

        self.assertEqual(missing_operation_id.status_code, 422)

    def test_operation_intents_reject_expired_session_bindings(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_expire_1",
                    "base_hashrate_hps": "15",
                },
            )
            self.assertEqual(started.status_code, 200)

            with psycopg.connect(self.database_url) as connection:
                with connection.cursor() as cursor:
                    cursor.execute(
                        """
                        UPDATE auth_sessions
                        SET expires_at = NOW() - INTERVAL '1 second'
                        WHERE session_id = %s
                        """,
                        (UUID(session_id),),
                    )
                connection.commit()

            expired_start = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_expire_2",
                    "base_hashrate_hps": "15",
                },
            )
            expired_stop = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                json={
                    "operation_id": "op_expire_1",
                },
            )

        self.assertEqual(expired_start.status_code, 401)
        self.assertEqual(expired_start.json().get("detail"), "Invalid session binding")
        self.assertEqual(expired_stop.status_code, 401)
        self.assertEqual(expired_stop.json().get("detail"), "Invalid session binding")

    def test_operation_intents_accept_header_based_session_binding(self) -> None:
        player_id, session_id = self._create_player_session_binding()
        header_name = settings.operation_intent_session_header

        with TestClient(app) as client:
            started = client.post(
                "/api/v1/blockchain/operations/intents/start",
                json={
                    "operation_id": "op_header_1",
                    "base_hashrate_hps": "20",
                },
                headers={header_name: session_id},
            )
            stopped = client.post(
                "/api/v1/blockchain/operations/intents/stop",
                json={
                    "operation_id": "op_header_1",
                },
                headers={header_name: session_id},
            )

        self.assertEqual(started.status_code, 200)
        self.assertEqual(started.json().get("player_id"), player_id)
        self.assertEqual(stopped.status_code, 200)
        self.assertEqual(stopped.json().get("player_id"), player_id)

    def test_operation_intents_reject_mismatched_query_and_header_session_binding(self) -> None:
        _, session_a = self._create_player_session_binding()
        _, session_b = self._create_player_session_binding()
        header_name = settings.operation_intent_session_header

        with TestClient(app) as client:
            mismatch_start = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_header_mismatch",
                    "base_hashrate_hps": "20",
                },
                headers={header_name: session_b},
            )
            mismatch_stop = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_a}",
                json={
                    "operation_id": "op_header_mismatch",
                },
                headers={header_name: session_b},
            )

        self.assertEqual(mismatch_start.status_code, 400)
        self.assertIn("Session binding mismatch", mismatch_start.json().get("detail", ""))
        self.assertEqual(mismatch_stop.status_code, 400)
        self.assertIn("Session binding mismatch", mismatch_stop.json().get("detail", ""))

    def test_operation_intent_transport_metrics_track_query_header_and_mismatch_modes(self) -> None:
        _, session_a = self._create_player_session_binding()
        _, session_b = self._create_player_session_binding()
        header_name = settings.operation_intent_session_header

        with TestClient(app) as client:
            query_start = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_transport_metrics_query",
                    "base_hashrate_hps": "25",
                },
            )
            header_start = client.post(
                "/api/v1/blockchain/operations/intents/start",
                json={
                    "operation_id": "op_transport_metrics_header",
                    "base_hashrate_hps": "25",
                },
                headers={header_name: session_a},
            )
            dual_start = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_transport_metrics_dual",
                    "base_hashrate_hps": "25",
                },
                headers={header_name: session_a},
            )
            mismatch_start = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_a}",
                json={
                    "operation_id": "op_transport_metrics_mismatch",
                    "base_hashrate_hps": "25",
                },
                headers={header_name: session_b},
            )
            missing_start = client.post(
                "/api/v1/blockchain/operations/intents/start",
                json={
                    "operation_id": "op_transport_metrics_missing",
                    "base_hashrate_hps": "25",
                },
            )
            metrics_headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
            metrics_json = client.get("/api/v1/blockchain/maintenance/metrics", headers=metrics_headers)
            metrics_plaintext = client.get("/api/v1/blockchain/maintenance/metrics/plaintext", headers=metrics_headers)

        self.assertEqual(query_start.status_code, 200)
        self.assertEqual(header_start.status_code, 200)
        self.assertEqual(dual_start.status_code, 200)
        self.assertEqual(mismatch_start.status_code, 400)
        self.assertEqual(missing_start.status_code, 401)
        self.assertEqual(metrics_json.status_code, 200)
        self.assertEqual(metrics_plaintext.status_code, 200)

        counters = metrics_json.json().get("operation_intent_transport_requests_total", {})
        self.assertEqual(counters.get("query", 0), 1)
        self.assertEqual(counters.get("header", 0), 1)
        self.assertEqual(counters.get("dual_match", 0), 1)
        self.assertEqual(counters.get("mismatch", 0), 1)
        self.assertEqual(counters.get("missing", 0), 1)

        plaintext = metrics_plaintext.text
        self.assertIn('gmn_operation_intent_transport_requests_total{mode="query"} 1', plaintext)
        self.assertIn('gmn_operation_intent_transport_requests_total{mode="header"} 1', plaintext)
        self.assertIn('gmn_operation_intent_transport_requests_total{mode="dual_match"} 1', plaintext)
        self.assertIn('gmn_operation_intent_transport_requests_total{mode="mismatch"} 1', plaintext)
        self.assertIn('gmn_operation_intent_transport_requests_total{mode="missing"} 1', plaintext)

    def test_operation_intents_strict_header_mode_rejects_query_only_transport(self) -> None:
        _, session_id = self._create_player_session_binding()
        header_name = settings.operation_intent_session_header
        original_strict_mode = settings.operation_intent_require_header_binding
        settings.operation_intent_require_header_binding = True

        try:
            with TestClient(app) as client:
                query_only_start = client.post(
                    f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                    json={
                        "operation_id": "op_strict_query_reject",
                        "base_hashrate_hps": "20",
                    },
                )
                header_start = client.post(
                    "/api/v1/blockchain/operations/intents/start",
                    json={
                        "operation_id": "op_strict_header_ok",
                        "base_hashrate_hps": "20",
                    },
                    headers={header_name: session_id},
                )
                query_only_stop = client.post(
                    f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                    json={
                        "operation_id": "op_strict_header_ok",
                    },
                )
                header_stop = client.post(
                    "/api/v1/blockchain/operations/intents/stop",
                    json={
                        "operation_id": "op_strict_header_ok",
                    },
                    headers={header_name: session_id},
                )
                metrics_headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
                metrics_json = client.get("/api/v1/blockchain/maintenance/metrics", headers=metrics_headers)
                metrics_plaintext = client.get("/api/v1/blockchain/maintenance/metrics/plaintext", headers=metrics_headers)

            self.assertEqual(query_only_start.status_code, 400)
            self.assertIn("Session binding must be provided", query_only_start.json().get("detail", ""))
            self.assertEqual(header_start.status_code, 200)
            self.assertEqual(query_only_stop.status_code, 400)
            self.assertIn("Session binding must be provided", query_only_stop.json().get("detail", ""))
            self.assertEqual(header_stop.status_code, 200)
            self.assertEqual(metrics_json.status_code, 200)
            self.assertEqual(metrics_plaintext.status_code, 200)

            counters = metrics_json.json().get("operation_intent_transport_requests_total", {})
            self.assertGreaterEqual(counters.get("query_rejected_strict", 0), 2)
            plaintext = metrics_plaintext.text
            self.assertIn('gmn_operation_intent_transport_requests_total{mode="query_rejected_strict"}', plaintext)
        finally:
            settings.operation_intent_require_header_binding = original_strict_mode

    @unittest.skipUnless(
        os.getenv("GMN_ENABLE_QUERY_SUNSET_TESTS", "0") in {"1", "true", "TRUE"},
        "Query-sunset tests are gated behind GMN_ENABLE_QUERY_SUNSET_TESTS",
    )
    def test_query_sunset_stage_requires_header_only_transport(self) -> None:
        _, session_id = self._create_player_session_binding()
        header_name = settings.operation_intent_session_header
        original_strict_mode = settings.operation_intent_require_header_binding
        settings.operation_intent_require_header_binding = True

        try:
            with TestClient(app) as client:
                query_start = client.post(
                    f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                    json={
                        "operation_id": "op_sunset_query_start",
                        "base_hashrate_hps": "22",
                    },
                )
                header_start = client.post(
                    "/api/v1/blockchain/operations/intents/start",
                    json={
                        "operation_id": "op_sunset_header_start",
                        "base_hashrate_hps": "22",
                    },
                    headers={header_name: session_id},
                )
                query_stop = client.post(
                    f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                    json={
                        "operation_id": "op_sunset_header_start",
                    },
                )
                header_stop = client.post(
                    "/api/v1/blockchain/operations/intents/stop",
                    json={
                        "operation_id": "op_sunset_header_start",
                    },
                    headers={header_name: session_id},
                )

            self.assertEqual(query_start.status_code, 400)
            self.assertEqual(header_start.status_code, 200)
            self.assertEqual(query_stop.status_code, 400)
            self.assertEqual(header_stop.status_code, 200)
        finally:
            settings.operation_intent_require_header_binding = original_strict_mode

    def test_operation_intents_drive_authoritative_progression_and_reconnect_safe_events(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_runtime_1",
                    "base_hashrate_hps": "50",
                },
            )
            self.assertEqual(started.status_code, 200)
            started_payload = started.json()
            self.assertEqual(started_payload["operation_id"], "op_runtime_1")
            self.assertEqual(started_payload["player_id"], player_id)
            self.assertTrue(started_payload["accepted"])
            self.assertEqual(started_payload["status"], "started")

            # Interval slicer uses integer elapsed seconds; allow a full-second window.
            time.sleep(1.1)
            status_response = client.get("/api/v1/blockchain/status?recent_limit=5")
            self.assertEqual(status_response.status_code, 200)

            events_first = client.get("/api/v1/blockchain/network-events?limit=100")
            self.assertEqual(events_first.status_code, 200)
            first_payload = events_first.json()
            self.assertGreater(first_payload["reconnect_cursor"], 0)

            progress_events = [
                item for item in first_payload["events"]
                if item.get("event_type") == "network.block_progress.v1"
                and item.get("payload", {}).get("operation_id") == "op_runtime_1"
                and item.get("payload", {}).get("player_id") == player_id
            ]
            self.assertGreaterEqual(len(progress_events), 1)

            reconnect_cursor = first_payload["reconnect_cursor"]
            stopped = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                json={
                    "operation_id": "op_runtime_1",
                },
            )
            self.assertEqual(stopped.status_code, 200)
            stopped_payload = stopped.json()
            self.assertEqual(stopped_payload["operation_id"], "op_runtime_1")
            self.assertEqual(stopped_payload["player_id"], player_id)
            self.assertTrue(stopped_payload["accepted"])
            self.assertEqual(stopped_payload["status"], "stopped")

            events_second = client.get(f"/api/v1/blockchain/network-events?after_sequence={reconnect_cursor}&limit=100")
            self.assertEqual(events_second.status_code, 200)
            self.assertEqual(events_second.json()["events"], [])

    def test_operation_stop_intent_halts_further_authoritative_progression(self) -> None:
        _, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            started = client.post(
                f"/api/v1/blockchain/operations/intents/start?session_id={session_id}",
                json={
                    "operation_id": "op_runtime_stop",
                    "base_hashrate_hps": "40",
                },
            )
            self.assertEqual(started.status_code, 200)

            time.sleep(1.1)
            first_status = client.get("/api/v1/blockchain/status?recent_limit=5")
            self.assertEqual(first_status.status_code, 200)
            first_payload = first_status.json()
            first_accumulated = Decimal(first_status.json()["active_accumulated_work"])
            first_block_number = int(first_payload["active_block_number"])

            stopped = client.post(
                f"/api/v1/blockchain/operations/intents/stop?session_id={session_id}",
                json={
                    "operation_id": "op_runtime_stop",
                },
            )
            self.assertEqual(stopped.status_code, 200)

            time.sleep(1.1)
            second_status = client.get("/api/v1/blockchain/status?recent_limit=5")
            self.assertEqual(second_status.status_code, 200)
            second_payload = second_status.json()
            second_accumulated = Decimal(second_payload["active_accumulated_work"])
            second_block_number = int(second_payload["active_block_number"])
            self.assertEqual(second_block_number, first_block_number)
            self.assertEqual(second_accumulated, first_accumulated)

    def test_cleanup_endpoint_accepts_previous_rotation_token(self) -> None:
        original_previous_token = settings.maintenance_auth_previous_token
        original_current_label = settings.maintenance_auth_current_token_scope_label
        original_previous_label = settings.maintenance_auth_previous_token_scope_label
        original_unknown_label = settings.maintenance_auth_unknown_token_scope_label
        settings.maintenance_auth_previous_token = "rotation-overlap-token"
        settings.maintenance_auth_current_token_scope_label = "primary"
        settings.maintenance_auth_previous_token_scope_label = "overlap"
        settings.maintenance_auth_unknown_token_scope_label = "invalid"

        try:
            with TestClient(app) as client:
                headers = {settings.maintenance_auth_header: "rotation-overlap-token"}
                response = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
                metrics = client.get("/api/v1/blockchain/maintenance/metrics", headers=headers)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(metrics.status_code, 200)
            payload = metrics.json()
            self.assertEqual(payload["maintenance_auth_current_token_scope_label"], "primary")
            self.assertEqual(payload["maintenance_auth_previous_token_scope_label"], "overlap")
            self.assertEqual(payload["maintenance_auth_unknown_token_scope_label"], "invalid")
            self.assertGreaterEqual(payload["maintenance_auth_scope_requests_total"].get("overlap", 0), 2)
        finally:
            settings.maintenance_auth_previous_token = original_previous_token
            settings.maintenance_auth_current_token_scope_label = original_current_label
            settings.maintenance_auth_previous_token_scope_label = original_previous_label
            settings.maintenance_auth_unknown_token_scope_label = original_unknown_label

    def test_maintenance_metrics_endpoints_record_previous_scope_during_overlap_window(self) -> None:
        original_previous_token = settings.maintenance_auth_previous_token
        original_previous_label = settings.maintenance_auth_previous_token_scope_label
        settings.maintenance_auth_previous_token = "rotation-overlap-token"
        settings.maintenance_auth_previous_token_scope_label = "overlap"

        try:
            with TestClient(app) as client:
                overlap_headers = {settings.maintenance_auth_header: "rotation-overlap-token"}
                cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=overlap_headers)
                json_metrics = client.get("/api/v1/blockchain/maintenance/metrics", headers=overlap_headers)
                plaintext_metrics = client.get(
                    "/api/v1/blockchain/maintenance/metrics/plaintext",
                    headers=overlap_headers,
                )

            self.assertEqual(cleanup.status_code, 200)
            self.assertEqual(json_metrics.status_code, 200)
            self.assertEqual(plaintext_metrics.status_code, 200)

            payload = json_metrics.json()
            self.assertGreaterEqual(payload["maintenance_auth_scope_requests_total"].get("overlap", 0), 2)
            body = plaintext_metrics.text
            self.assertIn('token_scope="overlap"', body)
            self.assertIn("gmn_maintenance_auth_requests_total", body)
        finally:
            settings.maintenance_auth_previous_token = original_previous_token
            settings.maintenance_auth_previous_token_scope_label = original_previous_label

    def test_maintenance_scope_counters_accumulate_deterministically_for_mixed_requests(self) -> None:
        original_previous_token = settings.maintenance_auth_previous_token
        previous_label = settings.maintenance_auth_previous_token_scope_label
        unknown_label = settings.maintenance_auth_unknown_token_scope_label
        current_label = settings.maintenance_auth_current_token_scope_label
        settings.maintenance_auth_previous_token = "rotation-overlap-token"

        try:
            with TestClient(app) as client:
                unauthorized_cleanup = client.post("/api/v1/blockchain/maintenance/cleanup")
                current_headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
                previous_headers = {settings.maintenance_auth_header: "rotation-overlap-token"}
                current_cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=current_headers)
                previous_cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=previous_headers)
                metrics = client.get("/api/v1/blockchain/maintenance/metrics", headers=current_headers)
                plaintext_metrics = client.get("/api/v1/blockchain/maintenance/metrics/plaintext", headers=current_headers)

            self.assertEqual(unauthorized_cleanup.status_code, 401)
            self.assertEqual(current_cleanup.status_code, 200)
            self.assertEqual(previous_cleanup.status_code, 200)
            self.assertEqual(metrics.status_code, 200)
            self.assertEqual(plaintext_metrics.status_code, 200)

            payload = metrics.json()
            counters = payload["maintenance_auth_scope_requests_total"]

            # One unknown cleanup attempt, one current cleanup, one previous cleanup,
            # and one current metrics request used to read counters.
            self.assertEqual(counters.get(unknown_label, 0), 1)
            self.assertEqual(counters.get(current_label, 0), 2)
            self.assertEqual(counters.get(previous_label, 0), 1)

            plaintext = plaintext_metrics.text
            self.assertIn(f'token_scope="{unknown_label}"', plaintext)
            self.assertIn(f'token_scope="{current_label}"', plaintext)
            self.assertIn(f'token_scope="{previous_label}"', plaintext)
        finally:
            settings.maintenance_auth_previous_token = original_previous_token

    def test_maintenance_scope_counters_are_consistent_between_persisted_and_in_memory_rate_limit_modes(self) -> None:
        original_previous_token = settings.maintenance_auth_previous_token
        original_window = settings.maintenance_cleanup_rate_limit_window_seconds
        original_max = settings.maintenance_cleanup_rate_limit_max_requests
        original_persistence = settings.maintenance_cleanup_rate_limit_persistence_enabled
        previous_label = settings.maintenance_auth_previous_token_scope_label
        unknown_label = settings.maintenance_auth_unknown_token_scope_label
        current_label = settings.maintenance_auth_current_token_scope_label
        settings.maintenance_auth_previous_token = "rotation-overlap-token"
        settings.maintenance_cleanup_rate_limit_window_seconds = 300
        settings.maintenance_cleanup_rate_limit_max_requests = 50

        def run_mixed_sequence(*, persistence_enabled: bool) -> dict[str, int]:
            settings.maintenance_cleanup_rate_limit_persistence_enabled = persistence_enabled
            reset_blockchain_runtime_counters_for_tests(include_persisted_rate_limit_state=True)

            with TestClient(app) as client:
                unauthorized_cleanup = client.post("/api/v1/blockchain/maintenance/cleanup")
                current_headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
                previous_headers = {settings.maintenance_auth_header: "rotation-overlap-token"}
                current_cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=current_headers)
                previous_cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=previous_headers)
                metrics = client.get("/api/v1/blockchain/maintenance/metrics", headers=current_headers)

            self.assertEqual(unauthorized_cleanup.status_code, 401)
            self.assertEqual(current_cleanup.status_code, 200)
            self.assertEqual(previous_cleanup.status_code, 200)
            self.assertEqual(metrics.status_code, 200)

            payload = metrics.json()
            counters = payload["maintenance_auth_scope_requests_total"]
            return {
                unknown_label: counters.get(unknown_label, 0),
                current_label: counters.get(current_label, 0),
                previous_label: counters.get(previous_label, 0),
            }

        try:
            persisted_counters = run_mixed_sequence(persistence_enabled=True)
            in_memory_counters = run_mixed_sequence(persistence_enabled=False)

            expected_counters = {
                unknown_label: 1,
                current_label: 2,
                previous_label: 1,
            }
            self.assertEqual(persisted_counters, expected_counters)
            self.assertEqual(in_memory_counters, expected_counters)
            self.assertEqual(persisted_counters, in_memory_counters)
        finally:
            settings.maintenance_auth_previous_token = original_previous_token
            settings.maintenance_cleanup_rate_limit_window_seconds = original_window
            settings.maintenance_cleanup_rate_limit_max_requests = original_max
            settings.maintenance_cleanup_rate_limit_persistence_enabled = original_persistence

    def test_cleanup_endpoint_rate_limits_excess_requests(self) -> None:
        original_window = settings.maintenance_cleanup_rate_limit_window_seconds
        original_max = settings.maintenance_cleanup_rate_limit_max_requests
        original_persistence = settings.maintenance_cleanup_rate_limit_persistence_enabled
        settings.maintenance_cleanup_rate_limit_window_seconds = 60
        settings.maintenance_cleanup_rate_limit_max_requests = 2
        settings.maintenance_cleanup_rate_limit_persistence_enabled = False

        try:
            with TestClient(app) as client:
                headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
                first = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
                second = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
                third = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(third.status_code, 429)
            self.assertEqual(third.headers.get("Retry-After"), "60")
        finally:
            settings.maintenance_cleanup_rate_limit_window_seconds = original_window
            settings.maintenance_cleanup_rate_limit_max_requests = original_max
            settings.maintenance_cleanup_rate_limit_persistence_enabled = original_persistence

    def test_cleanup_rate_limit_persistence_survives_in_memory_counter_reset(self) -> None:
        original_window = settings.maintenance_cleanup_rate_limit_window_seconds
        original_max = settings.maintenance_cleanup_rate_limit_max_requests
        original_persistence = settings.maintenance_cleanup_rate_limit_persistence_enabled
        settings.maintenance_cleanup_rate_limit_window_seconds = 120
        settings.maintenance_cleanup_rate_limit_max_requests = 2
        settings.maintenance_cleanup_rate_limit_persistence_enabled = True

        try:
            with TestClient(app) as client:
                headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
                first = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
                second = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)

                # Simulate process-level in-memory metric reset; persisted limiter should still enforce.
                reset_blockchain_runtime_counters_for_tests(include_persisted_rate_limit_state=False)
                third = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)

            self.assertEqual(first.status_code, 200)
            self.assertEqual(second.status_code, 200)
            self.assertEqual(third.status_code, 429)
        finally:
            settings.maintenance_cleanup_rate_limit_window_seconds = original_window
            settings.maintenance_cleanup_rate_limit_max_requests = original_max
            settings.maintenance_cleanup_rate_limit_persistence_enabled = original_persistence

    def test_cleanup_rate_limit_persistence_retry_after_near_window_boundary(self) -> None:
        original_window = settings.maintenance_cleanup_rate_limit_window_seconds
        original_max = settings.maintenance_cleanup_rate_limit_max_requests
        original_persistence = settings.maintenance_cleanup_rate_limit_persistence_enabled
        settings.maintenance_cleanup_rate_limit_window_seconds = 5
        settings.maintenance_cleanup_rate_limit_max_requests = 1
        settings.maintenance_cleanup_rate_limit_persistence_enabled = True

        try:
            with TestClient(app) as client:
                headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
                first = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
                self.assertEqual(first.status_code, 200)

                with psycopg.connect(self.database_url) as connection:
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            UPDATE maintenance_cleanup_rate_limit_state
                            SET window_started_at = NOW() - INTERVAL '4 seconds',
                                request_count = 1,
                                updated_at = NOW()
                            WHERE state_key = 'cleanup'
                            """
                        )
                    connection.commit()

                second = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)

            self.assertEqual(second.status_code, 429)
            retry_after = int(second.headers.get("Retry-After", "0"))
            self.assertGreaterEqual(retry_after, 1)
            self.assertLessEqual(retry_after, 2)
        finally:
            settings.maintenance_cleanup_rate_limit_window_seconds = original_window
            settings.maintenance_cleanup_rate_limit_max_requests = original_max
            settings.maintenance_cleanup_rate_limit_persistence_enabled = original_persistence

    def test_cleanup_endpoint_accepts_forwarded_source_headers(self) -> None:
        with TestClient(app) as client:
            headers = {
                settings.maintenance_auth_header: settings.maintenance_auth_token,
                "X-Forwarded-For": "203.0.113.42",
                "User-Agent": "gmn-maintenance-test/1.0",
            }
            response = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)

        self.assertEqual(response.status_code, 200)

    def test_maintenance_metrics_endpoint_returns_contract(self) -> None:
        with TestClient(app) as client:
            headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
            cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
            self.assertEqual(cleanup.status_code, 200)

            response = client.get("/api/v1/blockchain/maintenance/metrics", headers=headers)

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["schema_version"], "maintenance.metrics.v1")
        self.assertIn(payload["cleanup_rate_limit_mode"], {"persisted", "in_memory"})
        self.assertGreaterEqual(payload["cleanup_runs_total"], 1)
        self.assertEqual(payload["maintenance_auth_current_token_scope_label"], settings.maintenance_auth_current_token_scope_label)
        self.assertEqual(payload["maintenance_auth_previous_token_scope_label"], settings.maintenance_auth_previous_token_scope_label)
        self.assertEqual(payload["maintenance_auth_unknown_token_scope_label"], settings.maintenance_auth_unknown_token_scope_label)
        self.assertIn(settings.maintenance_auth_current_token_scope_label, payload["maintenance_auth_scope_requests_total"])
        self.assertEqual(payload["operation_intent_session_header_name"], settings.operation_intent_session_header)
        self.assertIn("operation_intent_transport_requests_total", payload)
        self.assertIn("generated_at", payload)

    def test_maintenance_metrics_endpoint_rejects_unauthorized_requests(self) -> None:
        with TestClient(app) as client:
            unauthorized = client.get("/api/v1/blockchain/maintenance/metrics")
            headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
            authorized = client.get("/api/v1/blockchain/maintenance/metrics", headers=headers)

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized.status_code, 200)
        payload = authorized.json()
        self.assertGreaterEqual(
            payload["maintenance_auth_scope_requests_total"].get(
                settings.maintenance_auth_unknown_token_scope_label,
                0,
            ),
            1,
        )

    def test_maintenance_metrics_plaintext_endpoint_returns_prometheus_style_payload(self) -> None:
        with TestClient(app) as client:
            headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
            cleanup = client.post("/api/v1/blockchain/maintenance/cleanup", headers=headers)
            self.assertEqual(cleanup.status_code, 200)

            response = client.get("/api/v1/blockchain/maintenance/metrics/plaintext", headers=headers)

        self.assertEqual(response.status_code, 200)
        self.assertIn("text/plain", response.headers.get("content-type", ""))
        body = response.text
        self.assertIn("gmn_maintenance_cleanup_runs_total", body)
        self.assertIn("gmn_maintenance_cleanup_rate_limit_requests_in_window", body)
        self.assertIn("gmn_maintenance_auth_requests_total", body)
        self.assertIn("gmn_operation_intent_transport_requests_total", body)
        self.assertIn(f'token_scope="{settings.maintenance_auth_current_token_scope_label}"', body)

    def test_maintenance_metrics_plaintext_endpoint_rejects_unauthorized_requests(self) -> None:
        with TestClient(app) as client:
            unauthorized = client.get("/api/v1/blockchain/maintenance/metrics/plaintext")
            headers = {settings.maintenance_auth_header: settings.maintenance_auth_token}
            authorized_metrics = client.get("/api/v1/blockchain/maintenance/metrics", headers=headers)

        self.assertEqual(unauthorized.status_code, 401)
        self.assertEqual(authorized_metrics.status_code, 200)
        payload = authorized_metrics.json()
        self.assertGreaterEqual(
            payload["maintenance_auth_scope_requests_total"].get(
                settings.maintenance_auth_unknown_token_scope_label,
                0,
            ),
            1,
        )

    def test_websocket_stale_connections_are_evicted(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect(
                    "/api/v1/blockchain/network-events/ws"
                    f"?player_id={player_id}&session_id={session_id}&channel=global"
                    "&heartbeat_seconds=1&stale_timeout_seconds=2"
                ) as ws:
                    while True:
                        ws.receive_json()

    def test_network_events_websocket_requires_valid_session_binding(self) -> None:
        with TestClient(app) as client:
            with self.assertRaises(WebSocketDisconnect):
                with client.websocket_connect(
                    "/api/v1/blockchain/network-events/ws?player_id=bad&session_id=bad&channel=global"
                ) as websocket:
                    websocket.receive_json()

    def test_checkpoint_endpoints_persist_and_return_reconnect_cursor(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}",
                json={"reconnect_cursor": 42},
            )
            self.assertEqual(put_response.status_code, 200)

            get_response = client.get(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}"
            )

        self.assertEqual(get_response.status_code, 200)
        payload = get_response.json()
        self.assertEqual(payload["reconnect_cursor"], 42)

    def test_checkpoint_player_rewards_channel_persists_and_returns_reconnect_cursor(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/player_rewards?player_id={player_id}&session_id={session_id}",
                json={"reconnect_cursor": 7},
            )
            self.assertEqual(put_response.status_code, 200)

            get_response = client.get(
                f"/api/v1/blockchain/checkpoints/player_rewards?player_id={player_id}&session_id={session_id}"
            )

        self.assertEqual(get_response.status_code, 200)
        payload = get_response.json()
        self.assertEqual(payload["player_id"], player_id)
        self.assertEqual(payload["session_id"], session_id)
        self.assertEqual(payload["channel"], "player_rewards")
        self.assertEqual(payload["reconnect_cursor"], 7)

    def test_checkpoint_get_bootstraps_reconnect_cursor_without_existing_checkpoint(self) -> None:
        started_at = datetime(2026, 8, 16, 0, 15, tzinfo=UTC)
        player_id, session_id = self._create_player_session_binding()
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(
            operation_id="op_checkpoint_bootstrap_1",
            player_id=player_id,
            base_hashrate_hps=Decimal("20"),
            started_at=started_at,
        )
        service.process_tick(operation_id="op_checkpoint_bootstrap_1", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=50"
                f"&player_id={player_id}&session_id={session_id}&channel=global"
            ) as websocket:
                websocket_payload = websocket.receive_json()

            checkpoint_response = client.get(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}"
            )

        self.assertEqual(checkpoint_response.status_code, 200)

        checkpoint_payload = checkpoint_response.json()
        self.assertEqual(checkpoint_payload["player_id"], player_id)
        self.assertEqual(checkpoint_payload["session_id"], session_id)
        self.assertEqual(checkpoint_payload["channel"], "global")
        self.assertEqual(checkpoint_payload["reconnect_cursor"], websocket_payload["reconnect_cursor"])

    def test_checkpoint_get_bootstraps_player_rewards_cursor_without_existing_checkpoint(self) -> None:
        started_at = datetime(2026, 8, 16, 0, 20, tzinfo=UTC)
        player_a, session_a = self._create_player_session_binding()
        player_b, _ = self._create_player_session_binding()
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(
            operation_id="op_checkpoint_player_rewards_a",
            player_id=player_a,
            base_hashrate_hps=Decimal("20"),
            started_at=started_at,
        )
        service.register_operation(
            operation_id="op_checkpoint_player_rewards_b",
            player_id=player_b,
            base_hashrate_hps=Decimal("20"),
            started_at=started_at,
        )
        service.process_tick(
            operation_id="op_checkpoint_player_rewards_a",
            ended_at=started_at + timedelta(seconds=3),
        )
        service.process_tick(
            operation_id="op_checkpoint_player_rewards_b",
            ended_at=started_at + timedelta(seconds=5),
        )

        with TestClient(app) as client:
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=50"
                f"&player_id={player_a}&session_id={session_a}&channel=player_rewards"
            ) as websocket:
                websocket_payload = websocket.receive_json()

            checkpoint_response = client.get(
                f"/api/v1/blockchain/checkpoints/player_rewards?player_id={player_a}&session_id={session_a}"
            )

        self.assertEqual(checkpoint_response.status_code, 200)
        checkpoint_payload = checkpoint_response.json()
        self.assertEqual(checkpoint_payload["player_id"], player_a)
        self.assertEqual(checkpoint_payload["session_id"], session_a)
        self.assertEqual(checkpoint_payload["channel"], "player_rewards")
        self.assertEqual(checkpoint_payload["reconnect_cursor"], websocket_payload["reconnect_cursor"])

    def test_checkpoint_endpoints_reject_revoked_session_binding(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with psycopg.connect(self.database_url) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    UPDATE auth_sessions
                    SET revoked_at = NOW()
                    WHERE session_id = %s
                    """,
                    (UUID(session_id),),
                )
            connection.commit()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}",
                json={"reconnect_cursor": 99},
            )
            get_response = client.get(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}"
            )

        self.assertEqual(put_response.status_code, 401)
        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.json()["detail"], "Invalid session binding")
        self.assertEqual(get_response.json()["detail"], "Invalid session binding")

    def test_checkpoint_endpoints_reject_mismatched_player_session_binding(self) -> None:
        player_a, _ = self._create_player_session_binding()
        _, session_b = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_a}&session_id={session_b}",
                json={"reconnect_cursor": 55},
            )
            get_response = client.get(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_a}&session_id={session_b}"
            )

        self.assertEqual(put_response.status_code, 401)
        self.assertEqual(get_response.status_code, 401)
        self.assertEqual(put_response.json()["detail"], "Invalid session binding")
        self.assertEqual(get_response.json()["detail"], "Invalid session binding")

    def test_checkpoint_upsert_rejects_negative_reconnect_cursor(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}",
                json={"reconnect_cursor": -1},
            )

        self.assertEqual(put_response.status_code, 422)

    def test_checkpoint_upsert_rejects_missing_reconnect_cursor(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/global?player_id={player_id}&session_id={session_id}",
                json={},
            )

        self.assertEqual(put_response.status_code, 422)

    def test_checkpoint_player_rewards_upsert_rejects_negative_reconnect_cursor(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/player_rewards?player_id={player_id}&session_id={session_id}",
                json={"reconnect_cursor": -1},
            )

        self.assertEqual(put_response.status_code, 422)

    def test_checkpoint_endpoints_reject_unsupported_channel(self) -> None:
        player_id, session_id = self._create_player_session_binding()

        with TestClient(app) as client:
            put_response = client.put(
                f"/api/v1/blockchain/checkpoints/invalid_channel?player_id={player_id}&session_id={session_id}",
                json={"reconnect_cursor": 1},
            )
            get_response = client.get(
                f"/api/v1/blockchain/checkpoints/invalid_channel?player_id={player_id}&session_id={session_id}"
            )

        self.assertEqual(put_response.status_code, 400)
        self.assertEqual(get_response.status_code, 400)
        self.assertEqual(put_response.json()["detail"], "Unsupported channel")
        self.assertEqual(get_response.json()["detail"], "Unsupported channel")

    def test_checkpoint_endpoints_require_player_and_session_query_parameters(self) -> None:
        with TestClient(app) as client:
            get_missing_player = client.get("/api/v1/blockchain/checkpoints/global?session_id=session_only")
            get_missing_session = client.get("/api/v1/blockchain/checkpoints/global?player_id=player_only")
            put_missing_player = client.put(
                "/api/v1/blockchain/checkpoints/global?session_id=session_only",
                json={"reconnect_cursor": 3},
            )
            put_missing_session = client.put(
                "/api/v1/blockchain/checkpoints/global?player_id=player_only",
                json={"reconnect_cursor": 3},
            )

        self.assertEqual(get_missing_player.status_code, 422)
        self.assertEqual(get_missing_session.status_code, 422)
        self.assertEqual(put_missing_player.status_code, 422)
        self.assertEqual(put_missing_session.status_code, 422)

    def test_player_rewards_channel_filters_to_bound_player(self) -> None:
        started_at = datetime(2026, 8, 15, 23, 30, tzinfo=UTC)
        player_a, session_a = self._create_player_session_binding()
        player_b, session_b = self._create_player_session_binding()
        service = MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(required_work=Decimal("100")),
            ledger_poster=PostgresLedgerPoster(),
        )
        service.register_operation(operation_id="op_a", player_id=player_a, base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.register_operation(operation_id="op_b", player_id=player_b, base_hashrate_hps=Decimal("20"), started_at=started_at)
        service.process_tick(operation_id="op_a", ended_at=started_at + timedelta(seconds=3))
        service.process_tick(operation_id="op_b", ended_at=started_at + timedelta(seconds=5))

        with TestClient(app) as client:
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=20"
                f"&player_id={player_a}&session_id={session_a}&channel=player_rewards"
            ) as ws_a:
                payload_a = ws_a.receive_json()
            with client.websocket_connect(
                f"/api/v1/blockchain/network-events/ws?after_sequence=0&limit=20"
                f"&player_id={player_b}&session_id={session_b}&channel=player_rewards"
            ) as ws_b:
                payload_b = ws_b.receive_json()

        self.assertGreaterEqual(len(payload_a["events"]), 1)
        self.assertTrue(all(item["payload"]["player_id"] == player_a for item in payload_a["events"]))
        self.assertGreaterEqual(len(payload_b["events"]), 1)
        self.assertTrue(all(item["payload"]["player_id"] == player_b for item in payload_b["events"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)