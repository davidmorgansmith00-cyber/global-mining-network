from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.events.service import EventService


router = APIRouter(prefix="/events", tags=["events"])
service = EventService()


class CreateEventRequest(BaseModel):
    name: str
    type: str
    start_at: datetime
    end_at: datetime
    modifier_type: str | None = None
    modifier_value: Decimal | None = None


class CreateBranchRequest(BaseModel):
    branch_name: str


class ActivateEventRequest(BaseModel):
    rollout_stage: str


class RecordContributionRequest(BaseModel):
    branch_id: str
    player_id: str
    work_contributed: Decimal


class CancelEventRequest(BaseModel):
    reason: str


@router.post("", status_code=status.HTTP_201_CREATED)
def create_event(payload: CreateEventRequest) -> dict:
    event_id = service.create_event(
        name=payload.name,
        type=payload.type,
        start_at=payload.start_at.astimezone(UTC),
        end_at=payload.end_at.astimezone(UTC),
        modifier_type=payload.modifier_type,
        modifier_value=payload.modifier_value,
    )
    return {"event_id": event_id}


@router.post("/{event_id}/activate", status_code=status.HTTP_200_OK)
def activate_event(event_id: str, payload: ActivateEventRequest) -> dict:
    service.activate_event(event_id, payload.rollout_stage)
    return {"event_id": event_id, "status": "active", "rollout_stage": payload.rollout_stage}


@router.post("/{event_id}/branches", status_code=status.HTTP_201_CREATED)
def create_branch(event_id: str, payload: CreateBranchRequest) -> dict:
    branch_id = service.create_fork_event_branch(event_id, payload.branch_name)
    return {"event_id": event_id, "branch_id": branch_id}


@router.post("/branches/contribution", status_code=status.HTTP_200_OK)
def record_branch_contribution(payload: RecordContributionRequest) -> dict:
    service.record_branch_contribution(payload.branch_id, payload.player_id, payload.work_contributed)
    return {"success": True}


@router.post("/{event_id}/resolve", status_code=status.HTTP_200_OK)
def resolve_fork_event(event_id: str) -> dict:
    try:
        return service.resolve_fork_event(event_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.post("/{event_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_event(event_id: str, payload: CancelEventRequest) -> dict:
    service.cancel_event(event_id, payload.reason)
    return {"event_id": event_id, "status": "cancelled"}


@router.get("/active", status_code=status.HTTP_200_OK)
def get_active_events() -> dict:
    events = service.get_active_events()
    return {
        "items": [
            {
                "event_id": item.event_id,
                "event_name": item.event_name,
                "event_type": item.event_type,
                "start_at": item.start_at.astimezone(UTC).isoformat(),
                "end_at": item.end_at.astimezone(UTC).isoformat(),
                "modifier_type": item.modifier_type,
                "modifier_value": None if item.modifier_value is None else str(item.modifier_value),
                "status": item.status,
                "time_remaining_seconds": max(0, int((item.end_at - datetime.now(UTC)).total_seconds())),
            }
            for item in events
        ]
    }


@router.get("/{event_id}/leaderboard", status_code=status.HTTP_200_OK)
def get_event_leaderboard(event_id: str, limit: int = 10) -> dict:
    return {"items": service.get_event_leaderboard(event_id, limit)}
