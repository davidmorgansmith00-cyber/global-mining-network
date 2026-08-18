from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.moderation.service import ModerationService


router = APIRouter(tags=["moderation"])
_service = ModerationService()


class ActionRequest(BaseModel):
    player_id: str
    action_type: str
    reason: str
    staff_id: str
    duration_seconds: int | None = None
    source_ticket_id: str | None = None


class AppealRequest(BaseModel):
    player_id: str
    moderation_action_id: str
    appeal_reason: str
    evidence_json: dict | None = None


class ReviewAppealRequest(BaseModel):
    approved: bool
    staff_id: str
    denial_reason: str | None = None


@router.get("/moderation/queue")
def get_queue(sort_by: str = "priority", limit: int = 50) -> dict:
    actions = _service.get_moderation_queue(sort_by=sort_by, limit=limit)
    return {
        "queue": [
            {
                "action_id": a.action_id,
                "player_id": a.player_id,
                "action_type": a.action_type,
                "reason": a.reason,
                "created_at": a.created_at.isoformat(),
                "source_ticket_id": a.source_ticket_id,
            }
            for a in actions
        ]
    }


@router.post("/moderation/action", status_code=status.HTTP_201_CREATED)
def take_action(req: ActionRequest) -> dict:
    action_id = _service.take_moderation_action(
        player_id=req.player_id,
        action_type=req.action_type,
        reason=req.reason,
        staff_id=req.staff_id,
        duration_seconds=req.duration_seconds,
        source_ticket_id=req.source_ticket_id,
    )
    return {"action_id": action_id}


@router.get("/moderation/player/{player_id}/history")
def player_history(player_id: str) -> dict:
    actions = _service.get_player_history(player_id)
    return {
        "player_id": player_id,
        "actions": [
            {
                "action_id": a.action_id,
                "action_type": a.action_type,
                "reason": a.reason,
                "created_at": a.created_at.isoformat(),
                "expires_at": a.expires_at.isoformat() if a.expires_at else None,
            }
            for a in actions
        ],
    }


@router.post("/moderation/appeal", status_code=status.HTTP_201_CREATED)
def submit_appeal(req: AppealRequest) -> dict:
    appeal_id = _service.submit_appeal(
        player_id=req.player_id,
        moderation_action_id=req.moderation_action_id,
        appeal_reason=req.appeal_reason,
        evidence_json=req.evidence_json,
    )
    return {"appeal_id": appeal_id}


@router.get("/moderation/appeals")
def list_appeals(status_filter: str | None = None, limit: int = 50) -> dict:
    appeals = _service.get_appeals(status_filter=status_filter, limit=limit)
    return {
        "appeals": [
            {
                "appeal_id": a.appeal_id,
                "player_id": a.player_id,
                "moderation_action_id": a.moderation_action_id,
                "status": a.status,
                "created_at": a.created_at.isoformat(),
            }
            for a in appeals
        ]
    }


@router.post("/moderation/appeal/{appeal_id}/review")
def review_appeal(appeal_id: str, req: ReviewAppealRequest) -> dict:
    outcome = _service.review_appeal(
        appeal_id=appeal_id,
        approved=req.approved,
        staff_id=req.staff_id,
        denial_reason=req.denial_reason,
    )
    return {"outcome": outcome}


@router.get("/moderation/stats")
def moderation_stats(staff_id: str | None = None) -> dict:
    stats = _service.get_moderator_stats(staff_id=staff_id)
    return {
        "actions_taken": stats.actions_taken,
        "appeals_reviewed": stats.appeals_reviewed,
        "queue_depth": stats.queue_depth,
    }
