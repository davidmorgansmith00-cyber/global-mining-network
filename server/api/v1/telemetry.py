from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, Field

from domain.auth.repository import AuthRepository
from domain.telemetry.service import get_telemetry_service

router = APIRouter(prefix="/telemetry", tags=["telemetry"])
auth_repository = AuthRepository()
telemetry_service = get_telemetry_service()


class ClientTelemetryRequest(BaseModel):
    event_type: str = Field(min_length=1, max_length=80)
    client_version: str = Field(min_length=1, max_length=40)
    properties: dict[str, object] = Field(default_factory=dict)


def _resolve_session(session_id: str) -> tuple[str, str]:
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session") from exc
    credentials = auth_repository.get_active_session_credentials(session_uuid)
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")
    return str(credentials[0]), str(session_uuid)


@router.post("/client", status_code=status.HTTP_202_ACCEPTED)
def ingest_client_telemetry(
    payload: ClientTelemetryRequest,
    session_id: str = Query(...),
) -> dict[str, object]:
    player_id, resolved_session_id = _resolve_session(session_id)
    accepted = telemetry_service.emit_client_event(
        event_type=payload.event_type,
        player_id=player_id,
        session_id=resolved_session_id,
        properties={
            "client_version": payload.client_version,
            **payload.properties,
        },
    )
    if not accepted:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="unsupported_event_type")
    return {"accepted": True, "event_type": f"client.{payload.event_type}"}
