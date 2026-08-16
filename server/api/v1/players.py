from fastapi import APIRouter, status

from domain.players.schemas import BootstrapResponse
from domain.players.service import PlayerBootstrapService


router = APIRouter(prefix="/player", tags=["player"])
service = PlayerBootstrapService()


@router.get("/bootstrap", response_model=BootstrapResponse, status_code=status.HTTP_200_OK)
def bootstrap_player(player_id: str | None = None) -> BootstrapResponse:
    return service.bootstrap(player_id=player_id)