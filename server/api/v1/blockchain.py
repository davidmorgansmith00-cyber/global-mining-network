import asyncio
import time
from datetime import UTC, datetime
from decimal import Decimal
from threading import Lock
from uuid import UUID, uuid4

from fastapi import APIRouter, Query, Request, status
from fastapi import HTTPException
from fastapi.responses import PlainTextResponse
from starlette.websockets import WebSocket, WebSocketDisconnect

from domain.blockchain.client_sessions import ClientSessionService
from domain.blockchain.read_models import BlockchainReadModelService
from domain.blockchain.retention import BlockchainRetentionService
from domain.blockchain.schemas import (
    BlockchainStatusResponse,
    ClientCheckpointResponse,
    ClientCheckpointUpdateRequest,
    CleanupResponse,
    MaintenanceMetricsResponse,
    OperationIntentResponse,
    OperationRuntimeStatusResponse,
    OperationStartIntentRequest,
    OperationStopIntentRequest,
    NetworkEventsResponse,
    NetworkSnapshotContract,
    PlayerRewardBalancesResponse,
    PlayerRewardHistoryResponse,
)
from domain.blockchain.store import PostgresBlockchainStateStore
from domain.difficulty.service import DifficultyAdjustmentService
from domain.economy.ledger import PostgresLedgerPoster
from domain.economy.read_models import project_player_reward_balances
from domain.genesis.service import get_genesis_service
from domain.mining.service import MiningSimulationService
from domain.mining.contracts import SimulationBoundaryEvent
from psycopg.types.json import Jsonb
from shared.database import database_is_configured, open_connection
from shared.logging import get_logger
from shared.settings import settings


router = APIRouter(prefix="/blockchain", tags=["blockchain"])
service = BlockchainReadModelService()
client_sessions = ClientSessionService()
retention = BlockchainRetentionService()
logger = get_logger("gmn.blockchain.realtime")


def _build_runtime_mining_service() -> MiningSimulationService:
    difficulty_adjuster = DifficultyAdjustmentService()
    if database_is_configured():
        return MiningSimulationService(
            required_work=Decimal("100"),
            blockchain_state_store=PostgresBlockchainStateStore(
                required_work=Decimal("100"),
                difficulty_adjuster=difficulty_adjuster,
            ),
            ledger_poster=PostgresLedgerPoster(),
        )
    return MiningSimulationService(required_work=Decimal("100"))

_metrics_lock = Lock()
_cleanup_runs_total = 0
_cleanup_deleted_network_events_total = 0
_cleanup_deleted_client_checkpoints_total = 0
_websocket_stale_evictions_total = 0
_cleanup_rate_limit_rejections_total = 0
_cleanup_request_timestamps: list[float] = []
_maintenance_auth_scope_requests_total: dict[str, int] = {}
_operation_intent_transport_requests_total: dict[str, int] = {}
_runtime_mining_service = _build_runtime_mining_service()
_operation_runtime_lock = Lock()
_genesis_service = get_genesis_service()
_runtime_recovery_complete = False


def recover_runtime_operations() -> None:
    """Replay durable operation history before serving runtime state."""
    _recover_runtime_operations()


def _persist_operation_runtime_event(
    *,
    operation_id: str,
    player_id: str,
    event_type: str,
    occurred_at: datetime,
    base_hashrate_hps: Decimal | None = None,
    payload: dict[str, object] | None = None,
) -> None:
    if not database_is_configured():
        return
    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO mining_operation_runtime_events (
                    event_id, operation_id, player_id, event_type,
                    base_hashrate_hps, payload, occurred_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid4(),
                    operation_id,
                    UUID(player_id),
                    event_type,
                    base_hashrate_hps,
                    Jsonb(payload or {}),
                    occurred_at,
                ),
            )


def _recover_runtime_operations() -> None:
    global _runtime_recovery_complete
    if _runtime_recovery_complete or not database_is_configured():
        return
    with _operation_runtime_lock:
        if _runtime_recovery_complete:
            return
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT operation_id, player_id::text, event_type,
                           base_hashrate_hps, payload, occurred_at
                    FROM mining_operation_runtime_events
                    ORDER BY occurred_at, created_at, event_id
                    """
                )
                events = cursor.fetchall()

        for operation_id, player_id, event_type, base_hashrate, payload, occurred_at in events:
            try:
                if event_type == "mining.operation.start.v1":
                    if operation_id not in _runtime_mining_service.operations:
                        if base_hashrate is None or Decimal(str(base_hashrate)) <= 0:
                            continue
                        _runtime_mining_service.register_operation(
                            operation_id=operation_id,
                            player_id=player_id,
                            base_hashrate_hps=Decimal(str(base_hashrate)),
                            started_at=occurred_at,
                        )
                elif event_type == "mining.operation.stop.v1":
                    _runtime_mining_service.stop_operation(operation_id=operation_id)
                elif operation_id in _runtime_mining_service.operations:
                    _runtime_mining_service.apply_boundary_event(
                        SimulationBoundaryEvent(
                            event_type=event_type,
                            player_id=player_id,
                            operation_id=operation_id,
                            occurred_at=occurred_at,
                            payload=payload or {},
                        )
                    )
            except (ValueError, TypeError):
                # Malformed histories stay offline; recovery never invents work.
                _runtime_mining_service.stop_operation(operation_id=operation_id)
        _runtime_recovery_complete = True


def _advance_operation_runtime_once() -> None:
    _recover_runtime_operations()
    with _operation_runtime_lock:
        operation_ids = list(_runtime_mining_service.operations.keys())
        for operation_id in operation_ids:
            # Process each active operation using authoritative server time.
            _runtime_mining_service.process_tick(operation_id=operation_id)


def _get_runtime_global_hashrate() -> Decimal:
    with _operation_runtime_lock:
        return sum(
            (
                operation.base_hashrate_hps * operation.current_multiplier
                for operation in _runtime_mining_service.operations.values()
                if not operation.current_paused
            ),
            Decimal("0"),
        )


def _extract_request_source_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first = forwarded_for.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


def _record_operation_intent_transport_mode(mode: str) -> None:
    with _metrics_lock:
        _operation_intent_transport_requests_total[mode] = (
            _operation_intent_transport_requests_total.get(mode, 0) + 1
        )


def _resolve_operation_intent_session_id(request: Request, session_id_query: str | None) -> str:
    header_name = settings.operation_intent_session_header
    session_id_header = request.headers.get(header_name)

    if session_id_query and session_id_header and session_id_query != session_id_header:
        _record_operation_intent_transport_mode("mismatch")
        raise HTTPException(
            status_code=400,
            detail=f"Session binding mismatch between query and {header_name} header",
        )

    if (
        settings.operation_intent_require_header_binding
        and session_id_query
        and not session_id_header
    ):
        _record_operation_intent_transport_mode("query_rejected_strict")
        raise HTTPException(
            status_code=400,
            detail=f"Session binding must be provided via {header_name} header",
        )

    if session_id_query and session_id_header:
        _record_operation_intent_transport_mode("dual_match")
    elif session_id_header:
        _record_operation_intent_transport_mode("header")
    elif session_id_query:
        _record_operation_intent_transport_mode("query")

    resolved = session_id_header or session_id_query
    if not resolved:
        _record_operation_intent_transport_mode("missing")
        raise HTTPException(status_code=401, detail="Invalid session binding")
    return resolved


def _maintenance_scope_labels() -> tuple[str, str, str]:
    current = settings.maintenance_auth_current_token_scope_label or "current"
    previous = settings.maintenance_auth_previous_token_scope_label or "previous"
    unknown = settings.maintenance_auth_unknown_token_scope_label or "unknown"
    return current, previous, unknown


def _resolve_maintenance_request_auth_scope(request: Request) -> tuple[bool, str]:
    current_label, previous_label, unknown_label = _maintenance_scope_labels()
    current_token = settings.maintenance_auth_token
    previous_token = settings.maintenance_auth_previous_token
    provided_token = request.headers.get(settings.maintenance_auth_header)

    if current_token and provided_token == current_token:
        return True, current_label
    if previous_token and provided_token == previous_token:
        return True, previous_label
    if not current_token and not previous_token:
        return True, current_label
    return False, unknown_label


def _enforce_persisted_cleanup_rate_limit(*, window_seconds: int, max_requests: int) -> tuple[bool, int]:
    with open_connection() as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                INSERT INTO maintenance_cleanup_rate_limit_state (state_key, window_started_at, request_count, updated_at)
                VALUES ('cleanup', NOW(), 0, NOW())
                ON CONFLICT (state_key) DO NOTHING
                """
            )
            cursor.execute(
                """
                SELECT
                    EXTRACT(EPOCH FROM (NOW() - window_started_at))::INT,
                    request_count
                FROM maintenance_cleanup_rate_limit_state
                WHERE state_key = 'cleanup'
                FOR UPDATE
                """
            )
            row = cursor.fetchone()
            elapsed_seconds = int(row[0])
            request_count = int(row[1])

            if elapsed_seconds >= window_seconds:
                cursor.execute(
                    """
                    UPDATE maintenance_cleanup_rate_limit_state
                    SET window_started_at = NOW(),
                        request_count = 1,
                        updated_at = NOW()
                    WHERE state_key = 'cleanup'
                    """
                )
                connection.commit()
                return True, window_seconds

            if request_count >= max_requests:
                connection.commit()
                retry_after = max(1, window_seconds - elapsed_seconds)
                return False, retry_after

            cursor.execute(
                """
                UPDATE maintenance_cleanup_rate_limit_state
                SET request_count = request_count + 1,
                    updated_at = NOW()
                WHERE state_key = 'cleanup'
                """
            )
            connection.commit()

    return True, window_seconds


def reset_blockchain_runtime_counters_for_tests(
    *,
    include_persisted_rate_limit_state: bool = True,
    include_operation_runtime_state: bool = True,
) -> None:
    global _cleanup_runs_total
    global _cleanup_deleted_network_events_total
    global _cleanup_deleted_client_checkpoints_total
    global _websocket_stale_evictions_total
    global _cleanup_rate_limit_rejections_total
    global _maintenance_auth_scope_requests_total
    global _operation_intent_transport_requests_total
    global _runtime_recovery_complete

    with _metrics_lock:
        _cleanup_runs_total = 0
        _cleanup_deleted_network_events_total = 0
        _cleanup_deleted_client_checkpoints_total = 0
        _websocket_stale_evictions_total = 0
        _cleanup_rate_limit_rejections_total = 0
        _maintenance_auth_scope_requests_total = {}
        _operation_intent_transport_requests_total = {}
        _cleanup_request_timestamps.clear()

    if include_persisted_rate_limit_state and database_is_configured():
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM maintenance_cleanup_rate_limit_state WHERE state_key = 'cleanup'")
            connection.commit()

    if include_operation_runtime_state:
        _runtime_mining_service.operations.clear()
        _runtime_recovery_complete = False
        if database_is_configured():
            with open_connection() as connection:
                with connection.cursor() as cursor:
                    cursor.execute("DELETE FROM mining_operation_runtime_events")
                connection.commit()


@router.get("/status", response_model=BlockchainStatusResponse, status_code=status.HTTP_200_OK)
def get_blockchain_status(recent_limit: int = Query(default=10, ge=1, le=100)) -> BlockchainStatusResponse:
    _advance_operation_runtime_once()
    response = service.get_status(recent_limit=recent_limit)
    return response.model_copy(update={"global_hashrate": _get_runtime_global_hashrate()})


@router.get("/genesis/status", status_code=status.HTTP_200_OK)
def get_genesis_status() -> dict[str, object]:
    return _genesis_service.get_status_payload()


@router.get("/genesis", status_code=status.HTTP_200_OK)
def get_genesis_block_details() -> dict[str, object]:
    record = _genesis_service.get_current_genesis_block(include_archived=False)
    if record is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="genesis_not_found")
    return _genesis_service.serialize_genesis_block(record, include_admin_identity=False)


@router.get(
    "/players/{player_id}/rewards",
    response_model=PlayerRewardHistoryResponse,
    status_code=status.HTTP_200_OK,
)
def get_player_reward_history(
    player_id: str,
    recent_limit: int = Query(default=20, ge=1, le=200),
) -> PlayerRewardHistoryResponse:
    return service.get_player_reward_history(player_id=player_id, recent_limit=recent_limit)


@router.get(
    "/reward-balances",
    response_model=PlayerRewardBalancesResponse,
    status_code=status.HTTP_200_OK,
)
def get_player_reward_balances() -> PlayerRewardBalancesResponse:
    entries = project_player_reward_balances()
    total = sum((entry.reward_balance for entry in entries), Decimal("0"))
    serialized_entries = [
        {
            "player_id": entry.player_id,
            "reward_balance": entry.reward_balance,
        }
        for entry in entries
    ]
    return PlayerRewardBalancesResponse(
        total_reward_balance=total,
        entries=serialized_entries,
    )


@router.get(
    "/network-snapshot",
    response_model=NetworkSnapshotContract,
    status_code=status.HTTP_200_OK,
)
def get_network_snapshot(recent_limit: int = Query(default=10, ge=1, le=100)) -> NetworkSnapshotContract:
    _advance_operation_runtime_once()
    return service.get_network_snapshot_contract(recent_limit=recent_limit)


@router.get(
    "/network-events",
    response_model=NetworkEventsResponse,
    status_code=status.HTTP_200_OK,
)
def get_network_events(
    after_sequence: int | None = Query(default=None, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
) -> NetworkEventsResponse:
    _advance_operation_runtime_once()
    return service.get_network_events(after_sequence=after_sequence, limit=limit)


@router.get(
    "/checkpoints/{channel}",
    response_model=ClientCheckpointResponse,
    status_code=status.HTTP_200_OK,
)
def get_client_checkpoint(channel: str, player_id: str, session_id: str) -> ClientCheckpointResponse:
    if channel not in {"global", "player_rewards"}:
        raise HTTPException(status_code=400, detail="Unsupported channel")
    if not client_sessions.validate_session_binding(player_id=player_id, session_id=session_id):
        raise HTTPException(status_code=401, detail="Invalid session binding")

    checkpoint = client_sessions.get_checkpoint(player_id=player_id, session_id=session_id, channel=channel)
    if checkpoint is None:
        current = service.get_network_events_for_channel(
            channel=channel,
            player_id=player_id,
            after_sequence=None,
            limit=1,
        )
        return ClientCheckpointResponse(
            player_id=player_id,
            session_id=session_id,
            channel=channel,
            reconnect_cursor=current.reconnect_cursor,
        )

    return ClientCheckpointResponse(
        player_id=checkpoint.player_id,
        session_id=checkpoint.session_id,
        channel=checkpoint.channel,
        reconnect_cursor=checkpoint.reconnect_cursor,
    )


@router.put(
    "/checkpoints/{channel}",
    response_model=ClientCheckpointResponse,
    status_code=status.HTTP_200_OK,
)
def upsert_client_checkpoint(
    channel: str,
    payload: ClientCheckpointUpdateRequest,
    player_id: str,
    session_id: str,
) -> ClientCheckpointResponse:
    if channel not in {"global", "player_rewards"}:
        raise HTTPException(status_code=400, detail="Unsupported channel")
    if not client_sessions.validate_session_binding(player_id=player_id, session_id=session_id):
        raise HTTPException(status_code=401, detail="Invalid session binding")

    client_sessions.upsert_checkpoint(
        player_id=player_id,
        session_id=session_id,
        channel=channel,
        reconnect_cursor=payload.reconnect_cursor,
    )
    return ClientCheckpointResponse(
        player_id=player_id,
        session_id=session_id,
        channel=channel,
        reconnect_cursor=payload.reconnect_cursor,
    )


@router.post(
    "/operations/intents/start",
    response_model=OperationIntentResponse,
    status_code=status.HTTP_200_OK,
)
def start_operation_intent(
    request: Request,
    payload: OperationStartIntentRequest,
    session_id: str | None = Query(default=None),
) -> OperationIntentResponse:
    if payload.base_hashrate_hps <= 0:
        raise HTTPException(status_code=400, detail="base_hashrate_hps must be positive")

    resolved_session_id = _resolve_operation_intent_session_id(request=request, session_id_query=session_id)
    player_id = client_sessions.resolve_player_id_from_session(session_id=resolved_session_id)
    if player_id is None:
        raise HTTPException(status_code=401, detail="Invalid session binding")

    _recover_runtime_operations()
    existing = _runtime_mining_service.get_operation_state(operation_id=payload.operation_id)
    if existing is not None:
        if existing.player_id != player_id:
            raise HTTPException(status_code=409, detail="operation_id already bound to a different player")
        return OperationIntentResponse(
            operation_id=payload.operation_id,
            player_id=player_id,
            accepted=True,
            status="already_running",
            detail="Operation intent accepted; operation is already active",
        )

    started_at = datetime.now(UTC)
    try:
        _persist_operation_runtime_event(
            operation_id=payload.operation_id,
            player_id=player_id,
            event_type="mining.operation.start.v1",
            occurred_at=started_at,
            base_hashrate_hps=payload.base_hashrate_hps,
        )
    except Exception as exc:
        logger.exception("operation_start_persistence_failed operation_id=%s", payload.operation_id)
        raise HTTPException(status_code=503, detail="Operation could not be durably started") from exc

    _runtime_mining_service.register_operation(
        operation_id=payload.operation_id,
        player_id=player_id,
        base_hashrate_hps=payload.base_hashrate_hps,
        started_at=started_at,
    )
    return OperationIntentResponse(
        operation_id=payload.operation_id,
        player_id=player_id,
        accepted=True,
        status="started",
        detail="Operation start intent accepted",
    )


@router.post(
    "/operations/intents/stop",
    response_model=OperationIntentResponse,
    status_code=status.HTTP_200_OK,
)
def stop_operation_intent(
    request: Request,
    payload: OperationStopIntentRequest,
    session_id: str | None = Query(default=None),
) -> OperationIntentResponse:
    resolved_session_id = _resolve_operation_intent_session_id(request=request, session_id_query=session_id)
    player_id = client_sessions.resolve_player_id_from_session(session_id=resolved_session_id)
    if player_id is None:
        raise HTTPException(status_code=401, detail="Invalid session binding")

    _recover_runtime_operations()
    existing = _runtime_mining_service.get_operation_state(operation_id=payload.operation_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="operation_id not found")
    if existing.player_id != player_id:
        raise HTTPException(status_code=409, detail="operation_id is bound to a different player")

    stopped_at = datetime.now(UTC)
    try:
        _persist_operation_runtime_event(
            operation_id=payload.operation_id,
            player_id=player_id,
            event_type="mining.operation.stop.v1",
            occurred_at=stopped_at,
        )
    except Exception as exc:
        logger.exception("operation_stop_persistence_failed operation_id=%s", payload.operation_id)
        raise HTTPException(status_code=503, detail="Operation could not be durably stopped") from exc

    _runtime_mining_service.stop_operation(operation_id=payload.operation_id)
    return OperationIntentResponse(
        operation_id=payload.operation_id,
        player_id=player_id,
        accepted=True,
        status="stopped",
        detail="Operation stop intent accepted",
    )


@router.get(
    "/operations/{operation_id}",
    response_model=OperationRuntimeStatusResponse,
    status_code=status.HTTP_200_OK,
)
def get_operation_runtime_status(
    operation_id: str,
    request: Request,
    session_id: str | None = Query(default=None),
) -> OperationRuntimeStatusResponse:
    resolved_session_id = _resolve_operation_intent_session_id(request=request, session_id_query=session_id)
    player_id = client_sessions.resolve_player_id_from_session(session_id=resolved_session_id)
    if player_id is None:
        raise HTTPException(status_code=401, detail="Invalid session binding")
    _recover_runtime_operations()
    existing = _runtime_mining_service.get_operation_state(operation_id=operation_id)
    if existing is None:
        raise HTTPException(status_code=404, detail="operation_id not found")
    if existing.player_id != player_id:
        raise HTTPException(status_code=403, detail="operation_id is bound to a different player")
    return OperationRuntimeStatusResponse(
        operation_id=existing.operation_id,
        player_id=existing.player_id,
        accepted=True,
        status="paused" if existing.current_paused else "running",
        detail="Operation runtime status is authoritative",
        base_hashrate_hps=existing.base_hashrate_hps,
    )


@router.post(
    "/maintenance/cleanup",
    response_model=CleanupResponse,
    status_code=status.HTTP_200_OK,
)
def cleanup_event_storage(
    request: Request,
    event_retention_seconds: int = Query(default=60 * 60 * 24, ge=60),
    checkpoint_retention_seconds: int = Query(default=60 * 60 * 24 * 7, ge=60),
    max_network_events: int = Query(default=100_000, ge=1),
) -> CleanupResponse:
    global _cleanup_runs_total
    global _cleanup_deleted_network_events_total
    global _cleanup_deleted_client_checkpoints_total
    global _cleanup_rate_limit_rejections_total

    source_ip = _extract_request_source_ip(request)
    user_agent = request.headers.get("User-Agent", "unknown")
    is_authorized, token_scope = _resolve_maintenance_request_auth_scope(request)
    with _metrics_lock:
        _maintenance_auth_scope_requests_total[token_scope] = _maintenance_auth_scope_requests_total.get(token_scope, 0) + 1

    rate_limit_window_seconds = max(1, settings.maintenance_cleanup_rate_limit_window_seconds)
    rate_limit_max_requests = max(1, settings.maintenance_cleanup_rate_limit_max_requests)
    use_persisted_rate_limit = (
        settings.maintenance_cleanup_rate_limit_persistence_enabled and database_is_configured()
    )
    if use_persisted_rate_limit:
        allowed, retry_after = _enforce_persisted_cleanup_rate_limit(
            window_seconds=rate_limit_window_seconds,
            max_requests=rate_limit_max_requests,
        )
    else:
        now = time.monotonic()
        with _metrics_lock:
            _cleanup_request_timestamps[:] = [
                ts for ts in _cleanup_request_timestamps if (now - ts) < rate_limit_window_seconds
            ]
            if len(_cleanup_request_timestamps) >= rate_limit_max_requests:
                allowed = False
                retry_after = rate_limit_window_seconds
            else:
                _cleanup_request_timestamps.append(now)
                allowed = True
                retry_after = rate_limit_window_seconds

    if not allowed:
        with _metrics_lock:
            _cleanup_rate_limit_rejections_total += 1
            rejections_total = _cleanup_rate_limit_rejections_total
        logger.warning(
            "cleanup_rate_limited rate_limit_window_seconds=%s rate_limit_max_requests=%s "
            "cleanup_rate_limit_rejections_total=%s source_ip=%s user_agent=%s token_scope=%s",
            rate_limit_window_seconds,
            rate_limit_max_requests,
            rejections_total,
            source_ip,
            user_agent,
            token_scope,
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Maintenance cleanup rate limit exceeded",
            headers={"Retry-After": str(retry_after)},
        )

    if not is_authorized:
        logger.warning(
            "cleanup_unauthorized_attempt source_ip=%s user_agent=%s token_scope=%s",
            source_ip,
            user_agent,
            token_scope,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized maintenance request")

    result = retention.cleanup(
        event_retention_seconds=event_retention_seconds,
        checkpoint_retention_seconds=checkpoint_retention_seconds,
        max_network_events=max_network_events,
    )

    deleted_network_events_total = result.deleted_network_events_by_age + result.deleted_network_events_by_count
    with _metrics_lock:
        _cleanup_runs_total += 1
        _cleanup_deleted_network_events_total += deleted_network_events_total
        _cleanup_deleted_client_checkpoints_total += result.deleted_client_checkpoints
        runs_total = _cleanup_runs_total
        network_events_total = _cleanup_deleted_network_events_total
        checkpoints_total = _cleanup_deleted_client_checkpoints_total

    logger.info(
        "cleanup_executed deleted_network_events_by_age=%s deleted_network_events_by_count=%s "
        "deleted_client_checkpoints=%s cleanup_runs_total=%s "
        "cleanup_deleted_network_events_total=%s cleanup_deleted_client_checkpoints_total=%s "
        "source_ip=%s user_agent=%s token_scope=%s",
        result.deleted_network_events_by_age,
        result.deleted_network_events_by_count,
        result.deleted_client_checkpoints,
        runs_total,
        network_events_total,
        checkpoints_total,
        source_ip,
        user_agent,
        token_scope,
    )

    return CleanupResponse(
        deleted_network_events_by_age=result.deleted_network_events_by_age,
        deleted_network_events_by_count=result.deleted_network_events_by_count,
        deleted_client_checkpoints=result.deleted_client_checkpoints,
    )


@router.get(
    "/maintenance/metrics",
    response_model=MaintenanceMetricsResponse,
    status_code=status.HTTP_200_OK,
)
def get_maintenance_metrics(request: Request) -> MaintenanceMetricsResponse:
    is_authorized, token_scope = _resolve_maintenance_request_auth_scope(request)
    with _metrics_lock:
        _maintenance_auth_scope_requests_total[token_scope] = _maintenance_auth_scope_requests_total.get(token_scope, 0) + 1

    if not is_authorized:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized maintenance request")

    current_label, previous_label, unknown_label = _maintenance_scope_labels()
    with _metrics_lock:
        runs_total = _cleanup_runs_total
        deleted_network_events_total = _cleanup_deleted_network_events_total
        deleted_client_checkpoints_total = _cleanup_deleted_client_checkpoints_total
        rate_limit_rejections_total = _cleanup_rate_limit_rejections_total
        stale_evictions_total = _websocket_stale_evictions_total
        in_memory_window_count = len(_cleanup_request_timestamps)
        auth_scope_requests_total = dict(_maintenance_auth_scope_requests_total)
        operation_intent_transport_requests_total = dict(_operation_intent_transport_requests_total)

    return MaintenanceMetricsResponse(
        schema_version="maintenance.metrics.v1",
        generated_at=datetime.now(UTC),
        cleanup_runs_total=runs_total,
        cleanup_deleted_network_events_total=deleted_network_events_total,
        cleanup_deleted_client_checkpoints_total=deleted_client_checkpoints_total,
        cleanup_rate_limit_rejections_total=rate_limit_rejections_total,
        websocket_stale_evictions_total=stale_evictions_total,
        cleanup_rate_limit_mode=("persisted" if settings.maintenance_cleanup_rate_limit_persistence_enabled else "in_memory"),
        cleanup_rate_limit_requests_in_window=in_memory_window_count,
        maintenance_auth_current_token_scope_label=current_label,
        maintenance_auth_previous_token_scope_label=previous_label,
        maintenance_auth_unknown_token_scope_label=unknown_label,
        maintenance_auth_scope_requests_total=auth_scope_requests_total,
        operation_intent_session_header_name=settings.operation_intent_session_header,
        operation_intent_transport_requests_total=operation_intent_transport_requests_total,
    )


@router.get(
    "/maintenance/metrics/plaintext",
    response_class=PlainTextResponse,
    status_code=status.HTTP_200_OK,
)
def get_maintenance_metrics_plaintext(request: Request) -> PlainTextResponse:
    metrics = get_maintenance_metrics(request)
    mode_labels = '{mode="%s"}' % metrics.cleanup_rate_limit_mode
    auth_scope_lines: list[str] = []
    for scope, value in metrics.maintenance_auth_scope_requests_total.items():
        auth_scope_lines.append(f'gmn_maintenance_auth_requests_total{{token_scope="{scope}"}} {value}')
    operation_transport_lines: list[str] = []
    for mode, value in metrics.operation_intent_transport_requests_total.items():
        operation_transport_lines.append(f'gmn_operation_intent_transport_requests_total{{mode="{mode}"}} {value}')
    lines = [
        "# HELP gmn_maintenance_cleanup_runs_total Total successful cleanup runs",
        "# TYPE gmn_maintenance_cleanup_runs_total counter",
        f"gmn_maintenance_cleanup_runs_total {metrics.cleanup_runs_total}",
        "# HELP gmn_maintenance_cleanup_deleted_network_events_total Total deleted network events",
        "# TYPE gmn_maintenance_cleanup_deleted_network_events_total counter",
        f"gmn_maintenance_cleanup_deleted_network_events_total {metrics.cleanup_deleted_network_events_total}",
        "# HELP gmn_maintenance_cleanup_deleted_client_checkpoints_total Total deleted client checkpoints",
        "# TYPE gmn_maintenance_cleanup_deleted_client_checkpoints_total counter",
        f"gmn_maintenance_cleanup_deleted_client_checkpoints_total {metrics.cleanup_deleted_client_checkpoints_total}",
        "# HELP gmn_maintenance_cleanup_rate_limit_rejections_total Total cleanup rate-limit rejections",
        "# TYPE gmn_maintenance_cleanup_rate_limit_rejections_total counter",
        f"gmn_maintenance_cleanup_rate_limit_rejections_total {metrics.cleanup_rate_limit_rejections_total}",
        "# HELP gmn_websocket_stale_evictions_total Total websocket stale evictions",
        "# TYPE gmn_websocket_stale_evictions_total counter",
        f"gmn_websocket_stale_evictions_total {metrics.websocket_stale_evictions_total}",
        "# HELP gmn_maintenance_cleanup_rate_limit_requests_in_window Current rate-limit window request count",
        "# TYPE gmn_maintenance_cleanup_rate_limit_requests_in_window gauge",
        f"gmn_maintenance_cleanup_rate_limit_requests_in_window{mode_labels} {metrics.cleanup_rate_limit_requests_in_window}",
        "# HELP gmn_maintenance_auth_requests_total Total maintenance endpoint auth requests by token scope",
        "# TYPE gmn_maintenance_auth_requests_total counter",
        "# HELP gmn_operation_intent_transport_requests_total Total operation-intent requests by session transport mode",
        "# TYPE gmn_operation_intent_transport_requests_total counter",
    ]
    lines.extend(auth_scope_lines)
    lines.extend(operation_transport_lines)
    return PlainTextResponse("\n".join(lines) + "\n")


@router.websocket("/network-events/ws")
async def websocket_network_events(websocket: WebSocket) -> None:
    player_id = websocket.query_params.get("player_id")
    session_id = websocket.query_params.get("session_id")
    channel = websocket.query_params.get("channel", "global")
    if channel not in {"global", "player_rewards"}:
        await websocket.close(code=4400)
        return
    if not player_id or not session_id:
        await websocket.close(code=4401)
        return
    if not client_sessions.validate_session_binding(player_id=player_id, session_id=session_id):
        await websocket.close(code=4401)
        return

    await websocket.accept()

    checkpoint = client_sessions.get_checkpoint(player_id=player_id, session_id=session_id, channel=channel)
    checkpoint_cursor = checkpoint.reconnect_cursor if checkpoint is not None else 0
    after_param = websocket.query_params.get("after_sequence")
    limit_param = websocket.query_params.get("limit")
    heartbeat_param = websocket.query_params.get("heartbeat_seconds")
    stale_param = websocket.query_params.get("stale_timeout_seconds")
    current_cursor = int(after_param) if after_param and after_param.isdigit() else checkpoint_cursor
    limit = int(limit_param) if limit_param and limit_param.isdigit() else 100
    limit = min(max(limit, 1), 500)
    heartbeat_seconds = int(heartbeat_param) if heartbeat_param and heartbeat_param.isdigit() else 15
    stale_timeout_seconds = int(stale_param) if stale_param and stale_param.isdigit() else 45
    heartbeat_seconds = max(1, min(heartbeat_seconds, 120))
    stale_timeout_seconds = max(heartbeat_seconds + 1, min(stale_timeout_seconds, 300))
    last_client_activity = time.monotonic()
    last_heartbeat_sent = time.monotonic()

    _advance_operation_runtime_once()
    initial = service.get_network_events_for_channel(
        channel=channel,
        player_id=player_id,
        after_sequence=current_cursor,
        limit=limit,
    )
    await websocket.send_json(initial.model_dump(mode="json"))
    current_cursor = initial.reconnect_cursor
    client_sessions.upsert_checkpoint(
        player_id=player_id,
        session_id=session_id,
        channel=channel,
        reconnect_cursor=current_cursor,
    )

    while True:
        try:
            try:
                message = await asyncio.wait_for(websocket.receive_text(), timeout=0.5)
                if message.startswith("cursor:"):
                    raw_cursor = message.split(":", 1)[1].strip()
                    if raw_cursor.isdigit():
                        current_cursor = int(raw_cursor)
                        last_client_activity = time.monotonic()
                elif message == "pong":
                    last_client_activity = time.monotonic()
            except TimeoutError:
                pass

            now = time.monotonic()
            if now - last_heartbeat_sent >= heartbeat_seconds:
                await websocket.send_json({"type": "ping", "ts": now})
                last_heartbeat_sent = now

            if now - last_client_activity > stale_timeout_seconds:
                global _websocket_stale_evictions_total
                with _metrics_lock:
                    _websocket_stale_evictions_total += 1
                    evictions_total = _websocket_stale_evictions_total
                logger.info(
                    "websocket_stale_evicted channel=%s player_id=%s inactivity_seconds=%.3f "
                    "stale_timeout_seconds=%s websocket_stale_evictions_total=%s",
                    channel,
                    player_id,
                    now - last_client_activity,
                    stale_timeout_seconds,
                    evictions_total,
                )
                await websocket.close(code=4408)
                break

            _advance_operation_runtime_once()
            response = service.get_network_events_for_channel(
                channel=channel,
                player_id=player_id,
                after_sequence=current_cursor,
                limit=limit,
            )
            if response.events:
                await websocket.send_json(response.model_dump(mode="json"))
                current_cursor = response.reconnect_cursor
                client_sessions.upsert_checkpoint(
                    player_id=player_id,
                    session_id=session_id,
                    channel=channel,
                    reconnect_cursor=current_cursor,
                )
        except WebSocketDisconnect:
            break
