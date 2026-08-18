from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.leaderboards.service import LeaderboardService


router = APIRouter(tags=["leaderboards"])
leaderboard_service = LeaderboardService()


class ToggleVisibilityRequest(BaseModel):
    player_id: str


@router.get("/leaderboards/hashrate")
def get_hashrate_leaderboard(limit: int = 100, offset: int = 0) -> dict:
    ranks = leaderboard_service.get_hashrate_leaderboard(limit=limit, offset=offset)
    return {
        "leaderboard": [
            {
                "rank": rank.rank,
                "player_id": rank.player_id,
                "player_name": rank.player_name,
                "effective_hashrate": str(rank.effective_hashrate),
            }
            for rank in ranks
        ]
    }


@router.get("/leaderboards/pools")
def get_pool_leaderboard(limit: int = 50, offset: int = 0) -> dict:
    ranks = leaderboard_service.get_pool_leaderboard(limit=limit, offset=offset)
    return {
        "leaderboard": [
            {
                "rank": rank.rank,
                "pool_id": rank.pool_id,
                "pool_name": rank.pool_name,
                "total_hashrate": str(rank.total_hashrate),
                "member_count": rank.member_count,
            }
            for rank in ranks
        ]
    }


@router.get("/leaderboards/weekly-earnings")
def get_weekly_earnings_leaderboard(limit: int = 50, offset: int = 0) -> dict:
    ranks = leaderboard_service.get_weekly_earnings_leaderboard(limit=limit, offset=offset)
    return {
        "leaderboard": [
            {
                "rank": rank.rank,
                "player_id": rank.player_id,
                "player_name": rank.player_name,
                "earnings_7d": str(rank.earnings_7d),
            }
            for rank in ranks
        ]
    }


@router.get("/leaderboards/wealth")
def get_wealth_leaderboard(limit: int = 50, offset: int = 0) -> dict:
    ranks = leaderboard_service.get_wealth_leaderboard(limit=limit, offset=offset)
    return {
        "leaderboard": [
            {
                "rank": rank.rank,
                "player_id": rank.player_id,
                "player_name": rank.player_name,
                "total_wealth": str(rank.total_wealth),
            }
            for rank in ranks
        ]
    }


@router.get("/players/{player_id}/leaderboard-position")
def get_player_leaderboard_position(player_id: str) -> dict:
    position = leaderboard_service.get_player_leaderboard_position(player_id)
    return {
        "player_id": position.player_id,
        "hashrate_rank": position.hashrate_rank,
        "weekly_earnings_rank": position.weekly_earnings_rank,
        "wealth_rank": position.wealth_rank,
        "total_players": position.total_players,
        "percentile": str(position.percentile) if position.percentile is not None else None,
    }


@router.post("/players/leaderboard-visibility", status_code=status.HTTP_200_OK)
def toggle_leaderboard_visibility(req: ToggleVisibilityRequest) -> dict:
    try:
        new_hidden = leaderboard_service.toggle_leaderboard_visibility(req.player_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"player_id": req.player_id, "is_hidden": new_hidden}
