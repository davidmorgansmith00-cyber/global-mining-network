from __future__ import annotations

from decimal import Decimal, InvalidOperation

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from domain.marketplace.service import PlayerMarketplaceService


router = APIRouter(tags=["marketplace"])
marketplace_service = PlayerMarketplaceService()


class ListEquipmentRequest(BaseModel):
    player_id: str
    hardware_id: str
    quantity: int
    price_per_unit: str


class PurchaseRequest(BaseModel):
    buyer_id: str
    listing_id: str
    quantity: int


@router.post("/marketplace/list", status_code=status.HTTP_201_CREATED)
def list_equipment(req: ListEquipmentRequest) -> dict:
    try:
        price = Decimal(req.price_per_unit)
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail="invalid_price") from exc

    try:
        listing_id = marketplace_service.list_equipment(
            player_id=req.player_id,
            hardware_id=req.hardware_id,
            quantity=req.quantity,
            price_per_unit=price,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"listing_id": listing_id}


@router.delete("/marketplace/listing/{listing_id}", status_code=status.HTTP_200_OK)
def unlist_equipment(listing_id: str, player_id: str) -> dict:
    try:
        marketplace_service.unlist_equipment(player_id=player_id, listing_id=listing_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"status": "unlisted"}


@router.get("/marketplace/listings")
def browse_listings(
    hardware_id: str | None = None,
    price_min: str | None = None,
    price_max: str | None = None,
    sort: str = "price_asc",
    limit: int = 50,
    offset: int = 0,
) -> dict:
    try:
        price_min_d = Decimal(price_min) if price_min else None
        price_max_d = Decimal(price_max) if price_max else None
    except InvalidOperation as exc:
        raise HTTPException(status_code=400, detail="invalid_price_filter") from exc

    listings = marketplace_service.browse_listings(
        hardware_id=hardware_id,
        price_min=price_min_d,
        price_max=price_max_d,
        sort=sort,
        limit=limit,
        offset=offset,
    )
    return {
        "listings": [
            {
                "listing_id": listing.listing_id,
                "seller_id": listing.seller_id,
                "hardware_id": listing.hardware_id,
                "quantity_remaining": listing.quantity_remaining,
                "price_per_unit": str(listing.price_per_unit),
                "expires_at": listing.expires_at.isoformat(),
            }
            for listing in listings
        ]
    }


@router.get("/marketplace/listing/{listing_id}")
def get_listing(listing_id: str) -> dict:
    listing = marketplace_service.get_listing(listing_id)
    if listing is None:
        raise HTTPException(status_code=404, detail="listing_not_found")
    return {
        "listing_id": listing.listing_id,
        "seller_id": listing.seller_id,
        "hardware_id": listing.hardware_id,
        "quantity_total": listing.quantity_total,
        "quantity_remaining": listing.quantity_remaining,
        "price_per_unit": str(listing.price_per_unit),
        "listed_at": listing.listed_at.isoformat(),
        "expires_at": listing.expires_at.isoformat(),
        "status": listing.status,
    }


@router.post("/marketplace/purchase", status_code=status.HTTP_200_OK)
def purchase_equipment(req: PurchaseRequest) -> dict:
    result = marketplace_service.purchase_equipment(
        buyer_id=req.buyer_id,
        listing_id=req.listing_id,
        quantity=req.quantity,
    )
    if not result.success or result.receipt is None:
        raise HTTPException(status_code=400, detail=result.error)
    receipt = result.receipt
    return {
        "status": "purchased",
        "buyer_id": receipt.buyer_id,
        "seller_id": receipt.seller_id,
        "hardware_id": receipt.hardware_id,
        "quantity": receipt.quantity,
        "purchase_price": str(receipt.purchase_price),
        "marketplace_fee": str(receipt.marketplace_fee),
        "seller_proceeds": str(receipt.seller_proceeds),
    }


@router.get("/players/{player_id}/reputation")
def get_reputation(player_id: str) -> dict:
    reputation = marketplace_service.get_player_reputation(player_id)
    return {
        "player_id": reputation.player_id,
        "successful_sales": reputation.successful_sales,
        "successful_purchases": reputation.successful_purchases,
        "dispute_count": reputation.dispute_count,
        "reputation_score": str(reputation.reputation_score),
    }
