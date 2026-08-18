from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.pools.service import PoolService


router = APIRouter(tags=["pools"])
pool_service = PoolService()


class CreatePoolRequest(BaseModel):
    owner_id: str
    pool_name: str
    description: str = ""
    fee_percentage: str = "0"


class JoinPoolRequest(BaseModel):
    player_id: str


class LeavePoolRequest(BaseModel):
    player_id: str
    pool_id: str


class DissolvePoolRequest(BaseModel):
    owner_id: str


@router.post("/pools/create", status_code=status.HTTP_201_CREATED)
def create_pool(req: CreatePoolRequest) -> dict:
    try:
        fee = Decimal(req.fee_percentage)
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail="invalid_fee_percentage") from exc

    try:
        pool_id = pool_service.create_pool(
            owner_id=req.owner_id,
            pool_name=req.pool_name,
            description=req.description,
            fee_percentage=fee,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"pool_id": pool_id}


@router.get("/pools/browse")
def browse_pools(limit: int = 50, offset: int = 0) -> dict:
    pools = pool_service.list_pools(limit=limit, offset=offset)
    return {
        "pools": [
            {
                "pool_id": pool.pool_id,
                "owner_id": pool.owner_id,
                "pool_name": pool.pool_name,
                "description": pool.description,
                "fee_percentage": str(pool.fee_percentage),
                "status": pool.status,
            }
            for pool in pools
        ]
    }


@router.post("/pools/join/{pool_id}", status_code=status.HTTP_200_OK)
def join_pool(pool_id: str, req: JoinPoolRequest) -> dict:
    try:
        pool_service.join_pool(player_id=req.player_id, pool_id=pool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "joined", "pool_id": pool_id}


@router.post("/pools/leave", status_code=status.HTTP_200_OK)
def leave_pool(req: LeavePoolRequest) -> dict:
    try:
        accumulated = pool_service.leave_pool(player_id=req.player_id, pool_id=req.pool_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "left", "accumulated_reward": str(accumulated)}


@router.get("/pools/{pool_id}")
def get_pool(pool_id: str) -> dict:
    stats = pool_service.get_pool_stats(pool_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="pool_not_found")
    return {
        "pool_id": stats.pool_id,
        "pool_name": stats.pool_name,
        "owner_id": stats.owner_id,
        "fee_percentage": str(stats.fee_percentage),
        "status": stats.status,
        "member_count": stats.member_count,
        "blocks_completed": stats.blocks_completed,
        "total_distributed_rewards": str(stats.total_distributed_rewards),
        "members": [
            {
                "player_id": member.player_id,
                "joined_at": member.joined_at.isoformat(),
            }
            for member in stats.members
        ],
    }


@router.post("/pools/{pool_id}/dissolve", status_code=status.HTTP_200_OK)
def dissolve_pool(pool_id: str, req: DissolvePoolRequest) -> dict:
    try:
        pool_service.dissolve_pool(pool_id=pool_id, owner_id=req.owner_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "dissolved", "pool_id": pool_id}
