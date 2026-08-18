from fastapi import APIRouter, status

from domain.players.schemas import BootstrapResponse, PlayerProfileResponse
from domain.players.service import PlayerBootstrapService, PlayerProfileService


router = APIRouter(tags=["player"])
bootstrap_service = PlayerBootstrapService()
profile_service = PlayerProfileService()


@router.get("/player/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_200_OK)
def bootstrap_player(player_id: str | None = None) -> BootstrapResponse:
    return bootstrap_service.bootstrap(player_id=player_id)


@router.get("/players/profile", response_model=PlayerProfileResponse, status_code=status.HTTP_200_OK)
def get_player_profile(player_id: str | None = None) -> PlayerProfileResponse:
    return profile_service.get_profile(player_id=player_id)