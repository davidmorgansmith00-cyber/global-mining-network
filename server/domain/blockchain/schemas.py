from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict
from pydantic import Field
from pydantic import StringConstraints
from domain.market.schemas import MarketCatalogItemResponse


class RecentBlockOutcome(BaseModel):
    block_number: int
    required_work: Decimal
    total_work: Decimal
    finalized_at: datetime
    reward_pool_amount: Decimal
    player_reward_amount: Decimal


class BlockchainStatusResponse(BaseModel):
    active_block_number: int
    active_required_work: Decimal
    active_accumulated_work: Decimal
    active_progress_ratio: Decimal
    recent_outcomes: list[RecentBlockOutcome]
    market_catalog: list[MarketCatalogItemResponse]


class PlayerRewardHistoryItem(BaseModel):
    block_number: int
    reward_amount: Decimal
    contribution_hashes: Decimal
    finalized_at: datetime


class PlayerRewardHistoryResponse(BaseModel):
    player_id: str
    total_rewards: Decimal
    total_contribution_hashes: Decimal
    entries: list[PlayerRewardHistoryItem]


class PlayerRewardBalanceItem(BaseModel):
    player_id: str
    reward_balance: Decimal


class PlayerRewardBalancesResponse(BaseModel):
    total_reward_balance: Decimal
    entries: list[PlayerRewardBalanceItem]


class NetworkFinalizationSnapshot(BaseModel):
    block_number: int
    required_work: Decimal
    total_work: Decimal
    reward_pool_amount: Decimal
    player_reward_amount: Decimal
    finalized_at: datetime


class NetworkSnapshotContract(BaseModel):
    schema_version: str
    generated_at: datetime
    snapshot_sequence: int
    reconnect_cursor: int
    active_block_number: int
    active_required_work: Decimal
    active_accumulated_work: Decimal
    active_progress_ratio: Decimal
    recent_finalizations: list[NetworkFinalizationSnapshot]


class NetworkEventEnvelope(BaseModel):
    sequence: int
    event_type: str
    occurred_at: datetime
    payload: dict[str, object]


class NetworkEventsResponse(BaseModel):
    schema_version: str
    reconnect_cursor: int
    latest_sequence: int
    events: list[NetworkEventEnvelope]


class ClientCheckpointResponse(BaseModel):
    player_id: str
    session_id: str
    channel: str
    reconnect_cursor: int


class ClientCheckpointUpdateRequest(BaseModel):
    reconnect_cursor: int = Field(ge=0)


class OperationStartIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
    base_hashrate_hps: Decimal


class OperationStopIntentRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operation_id: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class OperationIntentResponse(BaseModel):
    operation_id: str
    player_id: str
    accepted: bool
    status: str
    detail: str


class CleanupResponse(BaseModel):
    deleted_network_events_by_age: int
    deleted_network_events_by_count: int
    deleted_client_checkpoints: int


class MaintenanceMetricsResponse(BaseModel):
    schema_version: str
    generated_at: datetime
    cleanup_runs_total: int
    cleanup_deleted_network_events_total: int
    cleanup_deleted_client_checkpoints_total: int
    cleanup_rate_limit_rejections_total: int
    websocket_stale_evictions_total: int
    cleanup_rate_limit_mode: str
    cleanup_rate_limit_requests_in_window: int
    maintenance_auth_current_token_scope_label: str
    maintenance_auth_previous_token_scope_label: str
    maintenance_auth_unknown_token_scope_label: str
    maintenance_auth_scope_requests_total: dict[str, int]
    operation_intent_session_header_name: str
    operation_intent_transport_requests_total: dict[str, int]
