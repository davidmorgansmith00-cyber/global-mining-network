from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field


SCHEMA_VERSION_V1 = "v1"

EVENT_OPERATION_PAUSE = "mining.operation.pause.v1"
EVENT_OPERATION_RESUME = "mining.operation.resume.v1"
EVENT_HARDWARE_CHANGED = "mining.hardware.changed.v1"
EVENT_POWER_STATE_CHANGED = "mining.power.state_changed.v1"
EVENT_COOLING_STATE_CHANGED = "mining.cooling.state_changed.v1"
EVENT_POOL_MEMBERSHIP_CHANGED = "mining.pool.membership_changed.v1"
EVENT_MODIFIER_STARTED = "mining.modifier.started.v1"
EVENT_MODIFIER_ENDED = "mining.modifier.ended.v1"
EVENT_MAINTENANCE_STATE_CHANGED = "mining.maintenance.state_changed.v1"
EVENT_THROTTLE_STATE_CHANGED = "mining.throttle.state_changed.v1"
EVENT_BLOCK_FINALIZED = "blockchain.block.finalized.v1"

BoundaryEventType = Literal[
    "mining.operation.pause.v1",
    "mining.operation.resume.v1",
    "mining.hardware.changed.v1",
    "mining.power.state_changed.v1",
    "mining.cooling.state_changed.v1",
    "mining.pool.membership_changed.v1",
    "mining.modifier.started.v1",
    "mining.modifier.ended.v1",
    "mining.maintenance.state_changed.v1",
    "mining.throttle.state_changed.v1",
    "blockchain.block.finalized.v1",
]


class SimulationBoundaryEvent(BaseModel):
    event_type: BoundaryEventType
    schema_version: str = SCHEMA_VERSION_V1
    player_id: str
    operation_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    payload: dict[str, object] = Field(default_factory=dict)
