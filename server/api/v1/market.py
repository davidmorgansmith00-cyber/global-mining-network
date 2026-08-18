from uuid import UUID

from fastapi import APIRouter, HTTPException, status

from domain.auth.repository import AuthRepository
from domain.market.schemas import (
    MarketCatalogResponse,
    MarketItemResponse,
    MarketPurchaseErrorResponse,
    MarketPurchaseRequest,
    MarketPurchaseResponse,
)
from domain.market.service import NpcMarketService


router = APIRouter(prefix="/market", tags=["market"])
market_service = NpcMarketService()
auth_repository = AuthRepository()


@router.get("/catalog", response_model=MarketCatalogResponse, status_code=status.HTTP_200_OK)
def get_market_catalog(player_tier: int | None = None) -> MarketCatalogResponse:
    return MarketCatalogResponse(items=market_service.get_market_catalog(player_tier=player_tier))


@router.get("/item/{item_id}", response_model=MarketItemResponse, status_code=status.HTTP_200_OK)
def get_market_item(item_id: str, player_tier: int | None = None) -> MarketItemResponse:
    item = market_service.get_item(item_id=item_id, player_tier=player_tier)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="item_not_found")
    return MarketItemResponse(item=item)


@router.post(
    "/purchase",
    response_model=MarketPurchaseResponse | MarketPurchaseErrorResponse,
    status_code=status.HTTP_200_OK,
)
def purchase_market_item(session_id: str, payload: MarketPurchaseRequest) -> MarketPurchaseResponse | MarketPurchaseErrorResponse:
    try:
        session_uuid = UUID(session_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session") from exc
    session_credentials = auth_repository.get_active_session_credentials(session_uuid)
    if session_credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="invalid_session")
    player_id = str(session_credentials[0])

    result = market_service.execute_purchase(
        player_id=player_id,
        item_id=payload.item_id,
        quantity=payload.quantity,
    )
    if not result.success or result.receipt is None:
        return MarketPurchaseErrorResponse(error=result.error or "purchase_failed")
    return MarketPurchaseResponse(
        receipt={
            "player_id": result.receipt.player_id,
            "item_id": result.receipt.item_id,
            "quantity": result.receipt.quantity,
            "unit_price": result.receipt.unit_price,
            "total_cost": result.receipt.total_cost,
            "new_balance": result.receipt.new_balance,
        },
        new_balance=result.receipt.new_balance,
    )
