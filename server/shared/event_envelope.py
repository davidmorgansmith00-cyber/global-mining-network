from datetime import datetime, UTC
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class DomainEventEnvelope(BaseModel):
    event_id: UUID = Field(default_factory=uuid4)
    event_type: str
    schema_version: str = "v1"
    aggregate_id: str
    occurred_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    correlation_id: UUID = Field(default_factory=uuid4)
    causation_id: UUID | None = None
    payload: dict[str, object] = Field(default_factory=dict)