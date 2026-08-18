from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, Field


class MarketCatalogItemResponse(BaseModel):
    item_id: str
    name: str
    description: str
    item_type: str
    price: Decimal
    inventory: str | int
    available_stock: int | None
    restock_rate_per_day: int | None = None
    unlock_condition: str | None = None


class MarketCatalogResponse(BaseModel):
    schema_version: str = "market.catalog.v1"
    items: list[MarketCatalogItemResponse]


class MarketItemResponse(BaseModel):
    schema_version: str = "market.item.v1"
    item: MarketCatalogItemResponse


class MarketPurchaseRequest(BaseModel):
    item_id: str
    quantity: int = Field(ge=1)


class MarketPurchaseReceiptResponse(BaseModel):
    player_id: str
    item_id: str
    quantity: int
    unit_price: Decimal
    total_cost: Decimal
    new_balance: Decimal


class MarketPurchaseResponse(BaseModel):
    success: bool = True
    receipt: MarketPurchaseReceiptResponse
    new_balance: Decimal


class MarketPurchaseErrorResponse(BaseModel):
    success: bool = False
    error: str
