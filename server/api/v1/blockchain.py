import asyncio
import time
from datetime import UTC, datetime
from threading import Lock

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
    NetworkEventsResponse,
    NetworkSnapshotContract,
    PlayerRewardHistoryResponse,
)
from shared.database import database_is_configured, open_connection
from shared.logging import get_logger
from shared.settings import settings


router = APIRouter(prefix="/blockchain", tags=["blockchain"])
service = BlockchainReadModelService()
client_sessions = ClientSessionService()
retention = BlockchainRetentionService()
logger = get_logger("gmn.blockchain.realtime")

_metrics_lock = Lock()
_cleanup_runs_total = 0
_cleanup_deleted_network_events_total = 0
_cleanup_deleted_client_checkpoints_total = 0
_websocket_stale_evictions_total = 0
_cleanup_rate_limit_rejections_total = 0
_cleanup_request_timestamps: list[float] = []
_maintenance_auth_scope_requests_total: dict[str, int] = {}


def _extract_request_source_ip(request: Request) -> str:
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        first = forwarded_for.split(",", 1)[0].strip()
        if first:
            return first
    if request.client and request.client.host:
        return request.client.host
    return "unknown"


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


def reset_blockchain_runtime_counters_for_tests(*, include_persisted_rate_limit_state: bool = True) -> None:
    global _cleanup_runs_total
    global _cleanup_deleted_network_events_total
    global _cleanup_deleted_client_checkpoints_total
    global _websocket_stale_evictions_total
    global _cleanup_rate_limit_rejections_total
    global _maintenance_auth_scope_requests_total

    with _metrics_lock:
        _cleanup_runs_total = 0
        _cleanup_deleted_network_events_total = 0
        _cleanup_deleted_client_checkpoints_total = 0
        _websocket_stale_evictions_total = 0
        _cleanup_rate_limit_rejections_total = 0
        _maintenance_auth_scope_requests_total = {}
        _cleanup_request_timestamps.clear()

    if include_persisted_rate_limit_state and database_is_configured():
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute("DELETE FROM maintenance_cleanup_rate_limit_state WHERE state_key = 'cleanup'")
            connection.commit()


@router.get("/status", response_model=BlockchainStatusResponse, status_code=status.HTTP_200_OK)
def get_blockchain_status(recent_limit: int = Query(default=10, ge=1, le=100)) -> BlockchainStatusResponse:
    return service.get_status(recent_limit=recent_limit)


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
    "/network-snapshot",
    response_model=NetworkSnapshotContract,
    status_code=status.HTTP_200_OK,
)
def get_network_snapshot(recent_limit: int = Query(default=10, ge=1, le=100)) -> NetworkSnapshotContract:
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
    ]
    lines.extend(auth_scope_lines)
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
