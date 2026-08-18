from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.anticheat.service import AntiCheatService


router = APIRouter(tags=["anticheat"])
anticheat_service = AntiCheatService()


class AppealRequest(BaseModel):
    player_id: str
    action_id: str
    appeal_reason: str


@router.get("/anticheat/check/{player_id}")
def check_player(player_id: str, event_type: str = "general") -> dict:
    result = anticheat_service.calculate_anomaly_score(player_id, event_type, {})
    return {
        "player_id": result.player_id,
        "total_score": result.total_score,
        "action": result.action,
        "reasons": result.reasons,
    }


@router.get("/anticheat/actions/{player_id}")
def get_active_actions(player_id: str) -> dict:
    actions = anticheat_service.get_active_actions(player_id)
    return {
        "actions": [
            {
                "action_id": action.action_id,
                "action_type": action.action_type,
                "reason": action.reason,
                "created_at": action.created_at.isoformat(),
                "expires_at": action.expires_at.isoformat() if action.expires_at else None,
                "appeal_status": action.appeal_status,
            }
            for action in actions
        ]
    }


@router.post("/anticheat/appeal", status_code=status.HTTP_201_CREATED)
def appeal_action(req: AppealRequest) -> dict:
    try:
        status_value = anticheat_service.appeal_action(
            player_id=req.player_id,
            action_id=req.action_id,
            appeal_reason=req.appeal_reason,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": status_value}
