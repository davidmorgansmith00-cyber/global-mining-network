from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
import json
from pathlib import Path
import re
from uuid import UUID, uuid4

from psycopg.errors import SerializationFailure

from domain.hardware.upgrade_service import HardwareUpgradeService
from domain.market.schemas import MarketCatalogItemResponse
from domain.telemetry.service import get_telemetry_service
from shared.database import database_is_configured, open_connection


CATALOG_PATH = Path(__file__).resolve().parents[3] / "content" / "market_catalog.json"
ALLOWED_ITEM_TYPES = {"hardware_upgrade", "facility_upgrade", "consumable", "cosmetic"}
CREDIT_LEDGER_ENTRY_TYPES = ("block.finalized.player_reward.v1", "market.purchase.v1", "hardware.upgrade.v1")
PURCHASE_ENTRY_TYPE = "market.purchase.v1"
UPGRADE_ENTRY_TYPE = "hardware.upgrade.v1"
TIER_UNLOCK_PATTERN = re.compile(r"^\s*tier\s*>=\s*(\d+)\s*$")


@dataclass(frozen=True)
class MarketCatalogItem:
    item_id: str
    name: str
    description: str
    item_type: str
    price: Decimal
    inventory: str | int
    restock_rate_per_day: int | None
    unlock_condition: str | None


@dataclass(frozen=True)
class PurchaseReceipt:
    player_id: str
    item_id: str
    quantity: int
    unit_price: Decimal
    total_cost: Decimal
    new_balance: Decimal


@dataclass(frozen=True)
class PurchaseResult:
    success: bool
    receipt: PurchaseReceipt | None = None
    error: str | None = None


class NpcMarketService:
    def __init__(self) -> None:
        self._catalog_cache: dict[str, MarketCatalogItem] | None = None
        self._upgrade_service = HardwareUpgradeService()

    def get_market_catalog(self, *, player_tier: int | None = None) -> list[MarketCatalogItemResponse]:
        catalog_items = list(self._load_catalog().values())
        stock_by_item = self._build_stock_snapshot(catalog_items)
        items = []
        for item in catalog_items:
            if player_tier is not None and not self._is_unlocked(item, player_tier):
                continue
            available_stock = stock_by_item.get(item.item_id)
            items.append(self._to_response_item(item=item, available_stock=available_stock))
        return items

    def get_item(self, item_id: str, *, player_tier: int | None = None) -> MarketCatalogItemResponse | None:
        item = self._load_catalog().get(item_id)
        if item is None:
            return None
        if player_tier is not None and not self._is_unlocked(item, player_tier):
            return None
        available_stock = self._get_available_stock(item)
        return self._to_response_item(item=item, available_stock=available_stock)

    def calculate_purchase_total(self, item_id: str, quantity: int) -> Decimal:
        if quantity <= 0:
            raise ValueError("quantity_must_be_positive")
        item = self._load_catalog().get(item_id)
        if item is None:
            raise ValueError("item_not_found")
        return (item.price * Decimal(quantity)).quantize(Decimal("0.000001"))

    def execute_purchase(self, player_id: str, item_id: str, quantity: int) -> PurchaseResult:
        if quantity <= 0:
            return PurchaseResult(success=False, error="invalid_quantity")
        item = self._load_catalog().get(item_id)
        if item is None:
            return PurchaseResult(success=False, error="item_not_found")
        if not database_is_configured():
            return PurchaseResult(success=False, error="database_unavailable")

        now = datetime.now(tz=UTC)
        total_cost = self.calculate_purchase_total(item_id, quantity)
        try:
            player_uuid = UUID(player_id)
        except ValueError:
            return PurchaseResult(success=False, error="player_not_found")

        for _ in range(3):
            try:
                with open_connection() as connection:
                    connection.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                    with connection.cursor() as cursor:
                        cursor.execute(
                            """
                            SELECT player_id, COALESCE(player_tier, 1), COALESCE(hardware_id, 'starter_rusty_home_computer')
                            FROM players
                            WHERE player_id = %s
                            FOR UPDATE
                            """,
                            (player_uuid,),
                        )
                        player_row = cursor.fetchone()
                        if player_row is None:
                            connection.rollback()
                            return PurchaseResult(success=False, error="player_not_found")
                        player_tier = int(player_row[1])
                        current_hardware_id: str = str(player_row[2])
                        if not self._is_unlocked(item, player_tier):
                            connection.rollback()
                            return PurchaseResult(success=False, error="item_locked")

                        balance = self._get_player_credit_balance(cursor=cursor, player_id=player_id)
                        if balance < total_cost:
                            connection.rollback()
                            return PurchaseResult(success=False, error="insufficient_balance")

                        available_stock = self._lock_and_get_stock(cursor=cursor, item=item, now=now)
                        if available_stock is not None and available_stock < quantity:
                            connection.rollback()
                            return PurchaseResult(success=False, error="out_of_stock")

                        if available_stock is not None:
                            cursor.execute(
                                """
                                UPDATE npc_market_inventory_state
                                SET current_stock = %s,
                                    updated_at = %s
                                WHERE item_id = %s
                                """,
                                (available_stock - quantity, now, item.item_id),
                            )

                        is_hw_upgrade = (
                            item.item_type == "hardware_upgrade"
                            and self._upgrade_service.is_hardware_tier_upgrade(item.item_id)
                        )
                        previous_hardware_id: str | None = current_hardware_id if is_hw_upgrade else None

                        cursor.execute(
                            """
                            INSERT INTO player_inventory (player_id, item_id, quantity, acquired_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (player_id, item_id)
                            DO UPDATE SET quantity = player_inventory.quantity + EXCLUDED.quantity,
                                          acquired_at = EXCLUDED.acquired_at
                            """,
                            (player_uuid, item.item_id, quantity, now),
                        )

                        if is_hw_upgrade:
                            hw_def = self._upgrade_service.get_definition(item.item_id)
                            new_power_consumed = (
                                hw_def.base_power_consumption if hw_def is not None else None
                            )
                            cursor.execute(
                                """
                                UPDATE players
                                SET hardware_id = %s,
                                    power_consumed = COALESCE(%s, power_consumed),
                                    heat_generated = 0,
                                    updated_at = %s
                                WHERE player_id = %s
                                """,
                                (item.item_id, new_power_consumed, now, player_uuid),
                            )
                            if previous_hardware_id and previous_hardware_id != item.item_id:
                                cursor.execute(
                                    """
                                    DELETE FROM player_inventory
                                    WHERE player_id = %s AND item_id = %s
                                    """,
                                    (player_uuid, previous_hardware_id),
                                )

                        entry_type = UPGRADE_ENTRY_TYPE if is_hw_upgrade else PURCHASE_ENTRY_TYPE
                        ledger_metadata: dict[str, object] = {
                            "item_id": item.item_id,
                            "quantity": quantity,
                            "unit_price": str(item.price),
                        }
                        if is_hw_upgrade and previous_hardware_id:
                            ledger_metadata["previous_item_id"] = previous_hardware_id

                        cursor.execute(
                            """
                            INSERT INTO economy_player_ledger_entries (
                                ledger_entry_id,
                                block_number,
                                player_id,
                                amount,
                                contribution_hashes,
                                currency,
                                entry_type,
                                item_id,
                                previous_item_id,
                                quantity,
                                unit_price,
                                total_cost,
                                metadata,
                                created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                            """,
                            (
                                uuid4(),
                                None,
                                player_id,
                                -total_cost,
                                Decimal("0"),
                                "credits",
                                entry_type,
                                item.item_id,
                                previous_hardware_id,
                                quantity,
                                item.price,
                                total_cost,
                                json.dumps(ledger_metadata),
                                now,
                            ),
                        )
                    connection.commit()
            except SerializationFailure:
                continue

            new_balance = (balance - total_cost).quantize(Decimal("0.000001"))
            receipt = PurchaseReceipt(
                player_id=player_id,
                item_id=item.item_id,
                quantity=quantity,
                unit_price=item.price,
                total_cost=total_cost,
                new_balance=new_balance,
            )
            if is_hw_upgrade:
                try:
                    get_telemetry_service().emit_hardware_purchased(
                        player_id=player_id,
                        hardware_id=item.item_id,
                        previous_hardware_id=previous_hardware_id,
                        cost=total_cost,
                        player_tier=player_tier,
                    )
                except Exception:
                    pass  # telemetry must never affect player experience
            return PurchaseResult(success=True, receipt=receipt)
        return PurchaseResult(success=False, error="transaction_conflict")

    def get_player_inventory(self, player_id: str) -> list[dict[str, object]]:
        if not database_is_configured():
            return []
        with open_connection() as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    SELECT item_id, quantity
                    FROM player_inventory
                    WHERE player_id = %s
                    ORDER BY item_id ASC
                    """,
                    (UUID(player_id),),
                )
                rows = cursor.fetchall()
        inventory = []
        catalog = self._load_catalog()
        for item_id, quantity in rows:
            catalog_item = catalog.get(item_id)
            inventory.append(
                {
                    "item_id": item_id,
                    "name": None if catalog_item is None else catalog_item.name,
                    "item_type": None if catalog_item is None else catalog_item.item_type,
                    "quantity": int(quantity),
                }
            )
        return inventory

    def get_player_reward_balance(self, player_id: str) -> Decimal:
        if not database_is_configured():
            return Decimal("0")
        with open_connection() as connection:
            with connection.cursor() as cursor:
                return self._get_player_credit_balance(cursor=cursor, player_id=player_id)

    def get_available_for_purchase(self, player_id: str, *, player_tier: int) -> list[MarketCatalogItemResponse]:
        balance = self.get_player_reward_balance(player_id)
        catalog_items = list(self._load_catalog().values())
        stock_by_item = self._build_stock_snapshot(catalog_items)
        available: list[MarketCatalogItemResponse] = []
        for item in catalog_items:
            if not self._is_unlocked(item, player_tier):
                continue
            if balance < item.price:
                continue
            stock = stock_by_item.get(item.item_id)
            if stock is not None and stock <= 0:
                continue
            available.append(self._to_response_item(item=item, available_stock=stock))
        return available

    def _load_catalog(self) -> dict[str, MarketCatalogItem]:
        if self._catalog_cache is not None:
            return self._catalog_cache

        data = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, list):
            raise ValueError("market_catalog_must_be_array")

        catalog: dict[str, MarketCatalogItem] = {}
        for entry in data:
            if not isinstance(entry, dict):
                raise ValueError("market_catalog_item_must_be_object")

            item_id = str(entry.get("item_id", "")).strip()
            if not item_id:
                raise ValueError("item_id_required")
            if item_id in catalog:
                raise ValueError(f"duplicate_item_id:{item_id}")

            item_type = str(entry.get("item_type", "")).strip()
            if item_type not in ALLOWED_ITEM_TYPES:
                raise ValueError(f"invalid_item_type:{item_type}")

            try:
                price = Decimal(str(entry.get("price")))
            except (InvalidOperation, TypeError):
                raise ValueError(f"invalid_price:{item_id}") from None
            if price <= 0:
                raise ValueError(f"non_positive_price:{item_id}")

            inventory_raw = entry.get("inventory")
            if inventory_raw == "unlimited":
                inventory: str | int = "unlimited"
            elif isinstance(inventory_raw, int) and inventory_raw > 0:
                inventory = inventory_raw
            else:
                raise ValueError(f"invalid_inventory:{item_id}")

            restock_rate_per_day = entry.get("restock_rate_per_day")
            if restock_rate_per_day is not None:
                if not isinstance(restock_rate_per_day, int) or restock_rate_per_day <= 0:
                    raise ValueError(f"invalid_restock_rate:{item_id}")
                if inventory == "unlimited":
                    raise ValueError(f"restock_not_allowed_for_unlimited:{item_id}")

            unlock_condition = entry.get("unlock_condition")
            if unlock_condition is not None:
                unlock_condition = str(unlock_condition).strip()
                if not unlock_condition:
                    raise ValueError(f"invalid_unlock_condition:{item_id}")
                if TIER_UNLOCK_PATTERN.match(unlock_condition) is None:
                    raise ValueError(f"unsupported_unlock_condition:{item_id}")

            catalog[item_id] = MarketCatalogItem(
                item_id=item_id,
                name=str(entry.get("name", "")).strip(),
                description=str(entry.get("description", "")).strip(),
                item_type=item_type,
                price=price.quantize(Decimal("0.000001")),
                inventory=inventory,
                restock_rate_per_day=restock_rate_per_day,
                unlock_condition=unlock_condition,
            )
        self._catalog_cache = catalog
        return catalog

    def _to_response_item(self, *, item: MarketCatalogItem, available_stock: int | None) -> MarketCatalogItemResponse:
        inventory = item.inventory if item.inventory == "unlimited" else int(item.inventory)
        return MarketCatalogItemResponse(
            item_id=item.item_id,
            name=item.name,
            description=item.description,
            item_type=item.item_type,
            price=item.price,
            inventory=inventory,
            available_stock=available_stock,
            restock_rate_per_day=item.restock_rate_per_day,
            unlock_condition=item.unlock_condition,
        )

    def _is_unlocked(self, item: MarketCatalogItem, player_tier: int) -> bool:
        if not item.unlock_condition:
            return True
        match = TIER_UNLOCK_PATTERN.match(item.unlock_condition)
        if match is None:
            return False
        required_tier = int(match.group(1))
        return player_tier >= required_tier

    def _get_available_stock(self, item: MarketCatalogItem) -> int | None:
        if item.inventory == "unlimited":
            return None
        if not database_is_configured():
            return int(item.inventory)
        now = datetime.now(tz=UTC)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                return self._lock_and_get_stock(cursor=cursor, item=item, now=now, lock_for_update=False)

    def _build_stock_snapshot(self, items: list[MarketCatalogItem]) -> dict[str, int | None]:
        snapshot: dict[str, int | None] = {}
        if not items:
            return snapshot
        if not database_is_configured():
            for item in items:
                snapshot[item.item_id] = None if item.inventory == "unlimited" else int(item.inventory)
            return snapshot

        now = datetime.now(tz=UTC)
        with open_connection() as connection:
            with connection.cursor() as cursor:
                for item in items:
                    snapshot[item.item_id] = self._lock_and_get_stock(
                        cursor=cursor,
                        item=item,
                        now=now,
                        lock_for_update=False,
                    )
            connection.commit()
        return snapshot

    def _lock_and_get_stock(
        self,
        *,
        cursor: object,
        item: MarketCatalogItem,
        now: datetime,
        lock_for_update: bool = True,
    ) -> int | None:
        if item.inventory == "unlimited":
            return None

        cursor.execute(
            """
            INSERT INTO npc_market_inventory_state (item_id, current_stock, last_restocked_at, updated_at)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (item_id) DO NOTHING
            """,
            (item.item_id, int(item.inventory), now, now),
        )
        lock_clause = "FOR UPDATE" if lock_for_update else ""
        cursor.execute(
            f"""
            SELECT current_stock, last_restocked_at
            FROM npc_market_inventory_state
            WHERE item_id = %s
            {lock_clause}
            """,
            (item.item_id,),
        )
        row = cursor.fetchone()
        if row is None:
            return int(item.inventory)
        current_stock = int(row[0]) if row[0] is not None else int(item.inventory)
        last_restocked_at = row[1]
        next_stock = current_stock

        if item.restock_rate_per_day and last_restocked_at is not None:
            elapsed_seconds = (now - last_restocked_at.astimezone(UTC)).total_seconds()
            if elapsed_seconds > 0:
                restock_units = int((Decimal(str(elapsed_seconds)) / Decimal("86400")) * Decimal(item.restock_rate_per_day))
                if restock_units > 0:
                    next_stock = min(int(item.inventory), current_stock + restock_units)
                    cursor.execute(
                        """
                        UPDATE npc_market_inventory_state
                        SET current_stock = %s,
                            last_restocked_at = %s,
                            updated_at = %s
                        WHERE item_id = %s
                        """,
                        (next_stock, now, now, item.item_id),
                    )
        return next_stock

    @staticmethod
    def _get_player_credit_balance(*, cursor: object, player_id: str) -> Decimal:
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM economy_player_ledger_entries
            WHERE player_id = %s
              AND currency = 'credits'
              AND entry_type = ANY(%s)
            """,
            (player_id, list(CREDIT_LEDGER_ENTRY_TYPES)),
        )
        row = cursor.fetchone()
        return Decimal("0") if row is None or row[0] is None else Decimal(row[0])
