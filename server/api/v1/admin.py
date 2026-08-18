from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
import os

from fastapi import APIRouter, HTTPException, Query, Request, status
from pydantic import BaseModel, Field

from domain.admin.service import AdminService
from domain.genesis.service import get_genesis_service
from domain.admin.totp import verify_totp_code


router = APIRouter(prefix="/admin", tags=["admin"])
service = AdminService()
genesis_service = get_genesis_service()


class UpdateConfigRequest(BaseModel):
    value: object
    reason: str = ""


class ResetBalanceRequest(BaseModel):
    amount: Decimal
    reason: str


class CancelEventRequest(BaseModel):
    reason: str


class ToggleEmergencyRequest(BaseModel):
    enabled: bool
    reason: str = ""


class ApproveContentRequest(BaseModel):
    version_id: str
    approver_role: str
    comments: str = ""


class Verify2FARequest(BaseModel):
    code: str


class CreateGenesisRequest(BaseModel):
    starting_balance: Decimal
    player_snapshot: list[dict[str, object]]
    tier_assignments: dict[str, int] = Field(default_factory=dict)
    launch_date: datetime | None = None


class AnnounceGenesisRequest(BaseModel):
    public_message: str


class RollbackGenesisRequest(BaseModel):
    reason: str


def _require_role(request: Request, allowed_roles: set[str]) -> str:
    admin_id = request.headers.get("X-Admin-Id", "").strip()
    if not admin_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="admin_id_required")
    roles = service.get_roles(admin_id=admin_id)
    if not roles.intersection(allowed_roles):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="forbidden")
    return admin_id


def _require_password(request: Request) -> None:
    admin_passcode = request.headers.get("X-Admin-Password", "")
    if not service.verify_password(admin_passcode):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="password_verification_failed")


def _require_2fa(request: Request) -> None:
    code = request.headers.get("X-Admin-2FA-Code", "").strip()
    secret = os.getenv("ADMIN_TOTP_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="twofa_not_configured")
    if not verify_totp_code(secret=secret, code=code):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="twofa_verification_failed")


@router.get("/dashboard", status_code=status.HTTP_200_OK)
def get_dashboard(request: Request) -> dict:
    _require_role(request, {"admin", "moderator", "analyst"})
    return service.get_dashboard_metrics()


@router.get("/config", status_code=status.HTTP_200_OK)
def get_config(request: Request) -> dict:
    _require_role(request, {"admin"})
    return {"config": service.get_config()}


@router.post("/config/{key}", status_code=status.HTTP_200_OK)
def update_config(key: str, payload: UpdateConfigRequest, request: Request) -> dict:
    admin_id = _require_role(request, {"admin"})
    _require_password(request)
    service.set_config(key=key, value=payload.value, admin_id=admin_id, reason=payload.reason)
    return {"success": True}


@router.post("/content/approve", status_code=status.HTTP_200_OK)
def approve_content(payload: ApproveContentRequest, request: Request) -> dict:
    del payload
    _require_role(request, {"admin"})
    _require_password(request)
    return {"approved": True}


@router.get("/players/{player_id}", status_code=status.HTTP_200_OK)
def get_player_state(player_id: str, request: Request) -> dict:
    _require_role(request, {"admin", "moderator"})
    player = service.get_player_state(player_id=player_id)
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="player_not_found")
    return player


@router.post("/players/{player_id}/reset-balance", status_code=status.HTTP_200_OK)
def reset_balance(player_id: str, payload: ResetBalanceRequest, request: Request) -> dict:
    admin_id = _require_role(request, {"admin", "moderator"})
    _require_password(request)
    _require_2fa(request)
    service.reset_player_balance(player_id=player_id, amount=payload.amount, admin_id=admin_id, reason=payload.reason)
    return {"success": True}


@router.post("/events/{event_id}/cancel", status_code=status.HTTP_200_OK)
def cancel_event(event_id: str, payload: CancelEventRequest, request: Request) -> dict:
    admin_id = _require_role(request, {"admin"})
    _require_password(request)
    _require_2fa(request)
    service.cancel_event(event_id=event_id, reason=payload.reason, admin_id=admin_id)
    return {"success": True}


@router.post("/emergency/pause-blocks", status_code=status.HTTP_200_OK)
def pause_blocks(payload: ToggleEmergencyRequest, request: Request) -> dict:
    admin_id = _require_role(request, {"admin"})
    _require_password(request)
    _require_2fa(request)
    service.set_emergency_control(key="pause_blocks", enabled=payload.enabled, admin_id=admin_id, reason=payload.reason)
    return {"success": True, "pause_blocks": payload.enabled}


@router.post("/emergency/maintenance-mode", status_code=status.HTTP_200_OK)
def maintenance_mode(payload: ToggleEmergencyRequest, request: Request) -> dict:
    admin_id = _require_role(request, {"admin"})
    _require_password(request)
    _require_2fa(request)
    service.set_emergency_control(
        key="maintenance_mode",
        enabled=payload.enabled,
        admin_id=admin_id,
        reason=payload.reason,
    )
    return {"success": True, "maintenance_mode": payload.enabled}


@router.get("/audit-log", status_code=status.HTTP_200_OK)
def get_audit_log(
    request: Request,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
) -> dict:
    _require_role(request, {"admin", "analyst"})
    return {"items": service.get_audit_log(limit=limit, offset=offset), "limit": limit, "offset": offset}


@router.post("/2fa-verify", status_code=status.HTTP_200_OK)
def verify_2fa(payload: Verify2FARequest, request: Request) -> dict:
    _require_role(request, {"admin", "moderator", "analyst"})
    secret = os.getenv("ADMIN_TOTP_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="twofa_not_configured")
    verified = verify_totp_code(secret=secret, code=payload.code, now=int(datetime.now(UTC).timestamp()))
    if not verified:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="twofa_verification_failed")
    return {"verified": True}


@router.get("/launch/genesis-status", status_code=status.HTTP_200_OK)
def get_genesis_launch_status(request: Request) -> dict:
    _require_role(request, {"admin", "analyst"})
    return genesis_service.get_status_payload()


@router.post("/launch/genesis", status_code=status.HTTP_200_OK)
def create_genesis(payload: CreateGenesisRequest, request: Request) -> dict:
    admin_id = _require_role(request, {"admin"})
    _require_password(request)
    _require_2fa(request)
    genesis_id = genesis_service.create_genesis_block(
        payload.starting_balance,
        payload.tier_assignments,
        payload.player_snapshot,
        created_by_admin_id=admin_id,
        launch_date=payload.launch_date,
    )
    record = genesis_service.get_genesis_block(genesis_id)
    return {"success": True, "genesis": genesis_service.serialize_genesis_block(record)}


@router.post("/launch/genesis/{genesis_id}/announce", status_code=status.HTTP_200_OK)
def announce_genesis(genesis_id: str, payload: AnnounceGenesisRequest, request: Request) -> dict:
    _require_role(request, {"admin"})
    _require_password(request)
    _require_2fa(request)
    record = genesis_service.announce_genesis(genesis_id, payload.public_message)
    return {"success": True, "genesis": genesis_service.serialize_genesis_block(record)}


@router.post("/launch/genesis/{genesis_id}/rollback", status_code=status.HTTP_200_OK)
def rollback_genesis(genesis_id: str, payload: RollbackGenesisRequest, request: Request) -> dict:
    _require_role(request, {"admin"})
    _require_password(request)
    _require_2fa(request)
    record = genesis_service.rollback_genesis(genesis_id, payload.reason)
    return {"success": True, "genesis": genesis_service.serialize_genesis_block(record)}
