from __future__ import annotations

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field
from uuid import UUID

from domain.auth.repository import AuthRepository
from domain.hardware.upgrade_runtime import HardwareUpgradeRuntimeService

router = APIRouter(prefix="/hardware/upgrades", tags=["hardware upgrades"])
service = HardwareUpgradeRuntimeService()
auth_repository = AuthRepository()


class StartUpgradeRequest(BaseModel):
    hardware_id: str = Field(min_length=1)
    idempotency_key: str = Field(min_length=1)


def _resolve_player(session_id: str) -> str:
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session") from exc
    credentials = auth_repository.get_active_session_credentials(session_uuid)
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")
    return str(credentials[0])


@router.post("/start", status_code=status.HTTP_200_OK)
def start_upgrade(payload: StartUpgradeRequest, session_id: str = Query(...)) -> dict[str, object]:
    player_id = _resolve_player(session_id)
    return service.start(player_id=player_id, hardware_id=payload.hardware_id, idempotency_key=payload.idempotency_key)


@router.get("/current", status_code=status.HTTP_200_OK)
def current_upgrade(player_id: str, session_id: str = Query(...)) -> dict[str, object]:
    resolved_player_id = _resolve_player(session_id)
    if resolved_player_id != player_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="player_session_mismatch")
    return service.current(player_id=player_id)
