from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from decimal import Decimal
import json
from uuid import UUID, uuid4

from psycopg.errors import SerializationFailure

from shared.database import database_is_configured, open_connection


MARKETPLACE_FEE_PERCENTAGE = Decimal("5")
EQUIPMENT_TRADE_ENTRY_TYPE = "player.equipment_trade.v1"
LISTING_EXPIRY_DAYS = 30
_CREDIT_LEDGER_ENTRY_TYPES = (
    "block.finalized.player_reward.v1",
    "market.purchase.v1",
    "hardware.upgrade.v1",
    "player.equipment_trade.v1",
    "pool.reward_distribution.v1",
)


@dataclass(frozen=True)
class EquipmentListing:
    listing_id: str
    seller_id: str
    hardware_id: str
    quantity_total: int
    quantity_remaining: int
    price_per_unit: Decimal
    listed_at: datetime
    expires_at: datetime
    status: str


@dataclass(frozen=True)
class TradeReceipt:
    buyer_id: str
    seller_id: str
    listing_id: str
    hardware_id: str
    quantity: int
    purchase_price: Decimal
    marketplace_fee: Decimal
    seller_proceeds: Decimal


@dataclass(frozen=True)
class TradeResult:
    success: bool
    receipt: TradeReceipt | None = None
    error: str | None = None


@dataclass(frozen=True)
class PlayerReputation:
    player_id: str
    successful_sales: int
    successful_purchases: int
    dispute_count: int
    reputation_score: Decimal


class PlayerMarketplaceService:
    def list_equipment(
        self,
        player_id: str,
        hardware_id: str,
        quantity: int,
        price_per_unit: Decimal,
    ) -> str:
        if quantity <= 0:
            raise ValueError("quantity_must_be_positive")
        if price_per_unit <= Decimal("0"):
            raise ValueError("price_must_be_positive")
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        seller_uuid = self._parse_player_uuid(player_id, error="seller_not_found")
        now = datetime.now(tz=UTC)
        expires_at = now + timedelta(days=LISTING_EXPIRY_DAYS)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT quantity
                    FROM player_inventory
                    WHERE player_id = %s AND item_id = %s
                    FOR UPDATE
                    """,
                    (seller_uuid, hardware_id),
                )
                inventory_row = cur.fetchone()
                if inventory_row is None or int(inventory_row[0]) < quantity:
                    raise ValueError("insufficient_inventory")

                if int(inventory_row[0]) == quantity:
                    cur.execute(
                        "DELETE FROM player_inventory WHERE player_id = %s AND item_id = %s",
                        (seller_uuid, hardware_id),
                    )
                else:
                    cur.execute(
                        """
                        UPDATE player_inventory
                        SET quantity = quantity - %s
                        WHERE player_id = %s AND item_id = %s
                        """,
                        (quantity, seller_uuid, hardware_id),
                    )

                cur.execute(
                    """
                    INSERT INTO equipment_listings
                        (seller_id, hardware_id, quantity_total, quantity_remaining,
                         price_per_unit, listed_at, expires_at, status)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                    RETURNING listing_id::text
                    """,
                    (player_id, hardware_id, quantity, quantity, str(price_per_unit), now, expires_at),
                )
                listing_id = str(cur.fetchone()[0])
            conn.commit()
        return listing_id

    def unlist_equipment(self, player_id: str, listing_id: str) -> None:
        if not database_is_configured():
            raise RuntimeError("database_unavailable")

        seller_uuid = self._parse_player_uuid(player_id, error="seller_not_found")
        now = datetime.now(tz=UTC)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT hardware_id, quantity_remaining
                    FROM equipment_listings
                    WHERE listing_id = %s AND seller_id = %s AND status = 'active'
                    FOR UPDATE
                    """,
                    (listing_id, player_id),
                )
                row = cur.fetchone()
                if row is None:
                    raise ValueError("listing_not_found_or_not_owner")

                cur.execute(
                    "UPDATE equipment_listings SET status = 'unlisted' WHERE listing_id = %s",
                    (listing_id,),
                )
                quantity_remaining = int(row[1])
                if quantity_remaining > 0:
                    cur.execute(
                        """
                        INSERT INTO player_inventory (player_id, item_id, quantity, acquired_at)
                        VALUES (%s, %s, %s, %s)
                        ON CONFLICT (player_id, item_id)
                        DO UPDATE SET quantity = player_inventory.quantity + EXCLUDED.quantity,
                                      acquired_at = EXCLUDED.acquired_at
                        """,
                        (seller_uuid, row[0], quantity_remaining, now),
                    )
            conn.commit()

    def browse_listings(
        self,
        hardware_id: str | None = None,
        price_min: Decimal | None = None,
        price_max: Decimal | None = None,
        sort: str = "price_asc",
        limit: int = 50,
        offset: int = 0,
    ) -> list[EquipmentListing]:
        if not database_is_configured():
            return []

        conditions = ["status = 'active'", "expires_at > NOW()"]
        params: list[object] = []
        if hardware_id:
            conditions.append("hardware_id = %s")
            params.append(hardware_id)
        if price_min is not None:
            conditions.append("price_per_unit >= %s")
            params.append(str(price_min))
        if price_max is not None:
            conditions.append("price_per_unit <= %s")
            params.append(str(price_max))

        order = "price_per_unit ASC, listing_id ASC" if sort == "price_asc" else "price_per_unit DESC, listing_id ASC"
        params.extend([limit, offset])
        where = " AND ".join(conditions)
        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    f"""
                    SELECT listing_id::text, seller_id, hardware_id,
                           quantity_total, quantity_remaining, price_per_unit,
                           listed_at, expires_at, status
                    FROM equipment_listings
                    WHERE {where}
                    ORDER BY {order}
                    LIMIT %s OFFSET %s
                    """,
                    params,
                )
                rows = cur.fetchall()

        return [
            EquipmentListing(
                listing_id=row[0],
                seller_id=row[1],
                hardware_id=row[2],
                quantity_total=int(row[3]),
                quantity_remaining=int(row[4]),
                price_per_unit=Decimal(str(row[5])),
                listed_at=row[6],
                expires_at=row[7],
                status=row[8],
            )
            for row in rows
        ]

    def get_listing(self, listing_id: str) -> EquipmentListing | None:
        if not database_is_configured():
            return None

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT listing_id::text, seller_id, hardware_id,
                           quantity_total, quantity_remaining, price_per_unit,
                           listed_at, expires_at, status
                    FROM equipment_listings
                    WHERE listing_id = %s
                    """,
                    (listing_id,),
                )
                row = cur.fetchone()
        if row is None:
            return None
        return EquipmentListing(
            listing_id=row[0],
            seller_id=row[1],
            hardware_id=row[2],
            quantity_total=int(row[3]),
            quantity_remaining=int(row[4]),
            price_per_unit=Decimal(str(row[5])),
            listed_at=row[6],
            expires_at=row[7],
            status=row[8],
        )

    def purchase_equipment(
        self,
        buyer_id: str,
        listing_id: str,
        quantity: int,
    ) -> TradeResult:
        if quantity <= 0:
            return TradeResult(success=False, error="invalid_quantity")
        if not database_is_configured():
            return TradeResult(success=False, error="database_unavailable")

        try:
            buyer_uuid = UUID(buyer_id)
        except ValueError:
            return TradeResult(success=False, error="buyer_not_found")

        for _ in range(3):
            try:
                with open_connection() as conn:
                    conn.execute("SET TRANSACTION ISOLATION LEVEL SERIALIZABLE")
                    with conn.cursor() as cur:
                        cur.execute(
                            """
                            SELECT listing_id::text, seller_id, hardware_id,
                                   quantity_remaining, price_per_unit, status, expires_at
                            FROM equipment_listings
                            WHERE listing_id = %s
                            FOR UPDATE
                            """,
                            (listing_id,),
                        )
                        listing_row = cur.fetchone()
                        if listing_row is None:
                            conn.rollback()
                            return TradeResult(success=False, error="listing_not_found")
                        if listing_row[5] != "active":
                            conn.rollback()
                            return TradeResult(success=False, error="listing_not_active")
                        if listing_row[6] <= datetime.now(tz=UTC):
                            cur.execute(
                                "UPDATE equipment_listings SET status = 'expired' WHERE listing_id = %s",
                                (listing_id,),
                            )
                            conn.commit()
                            return TradeResult(success=False, error="listing_expired")
                        if int(listing_row[3]) < quantity:
                            conn.rollback()
                            return TradeResult(success=False, error="not_enough_stock")

                        seller_id = str(listing_row[1])
                        if seller_id == buyer_id:
                            conn.rollback()
                            return TradeResult(success=False, error="cannot_purchase_own_listing")

                        hardware_id = str(listing_row[2])
                        price_per_unit = Decimal(str(listing_row[4]))
                        purchase_price = (price_per_unit * Decimal(quantity)).quantize(Decimal("0.000001"))
                        marketplace_fee = (purchase_price * MARKETPLACE_FEE_PERCENTAGE / Decimal("100")).quantize(
                            Decimal("0.000001")
                        )
                        seller_proceeds = (purchase_price - marketplace_fee).quantize(Decimal("0.000001"))

                        buyer_balance = self._get_player_credit_balance(cur, buyer_id)
                        if buyer_balance < purchase_price:
                            conn.rollback()
                            return TradeResult(success=False, error="insufficient_balance")

                        new_remaining = int(listing_row[3]) - quantity
                        new_status = "sold_out" if new_remaining == 0 else "active"
                        now = datetime.now(tz=UTC)

                        cur.execute(
                            """
                            UPDATE equipment_listings
                            SET quantity_remaining = %s,
                                status = %s
                            WHERE listing_id = %s
                            """,
                            (new_remaining, new_status, listing_id),
                        )
                        cur.execute(
                            """
                            INSERT INTO player_inventory (player_id, item_id, quantity, acquired_at)
                            VALUES (%s, %s, %s, %s)
                            ON CONFLICT (player_id, item_id)
                            DO UPDATE SET quantity = player_inventory.quantity + EXCLUDED.quantity,
                                          acquired_at = EXCLUDED.acquired_at
                            """,
                            (buyer_uuid, hardware_id, quantity, now),
                        )

                        metadata = json.dumps(
                            {
                                "listing_id": listing_id,
                                "hardware_id": hardware_id,
                                "quantity": quantity,
                                "purchase_price": str(purchase_price),
                                "marketplace_fee": str(marketplace_fee),
                                "seller_proceeds": str(seller_proceeds),
                                "buyer_id": buyer_id,
                                "seller_id": seller_id,
                            }
                        )
                        cur.execute(
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
                                quantity,
                                unit_price,
                                total_cost,
                                metadata,
                                created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                            """,
                            (
                                uuid4(),
                                None,
                                buyer_id,
                                -purchase_price,
                                Decimal("0"),
                                "credits",
                                EQUIPMENT_TRADE_ENTRY_TYPE,
                                hardware_id,
                                quantity,
                                price_per_unit,
                                purchase_price,
                                metadata,
                                now,
                            ),
                        )
                        cur.execute(
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
                                quantity,
                                unit_price,
                                total_cost,
                                metadata,
                                created_at
                            )
                            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s)
                            """,
                            (
                                uuid4(),
                                None,
                                seller_id,
                                seller_proceeds,
                                Decimal("0"),
                                "credits",
                                EQUIPMENT_TRADE_ENTRY_TYPE,
                                hardware_id,
                                quantity,
                                price_per_unit,
                                purchase_price,
                                metadata,
                                now,
                            ),
                        )
                        cur.execute(
                            """
                            INSERT INTO player_reputation (player_id, successful_sales, reputation_score)
                            VALUES (%s, 1, 1)
                            ON CONFLICT (player_id) DO UPDATE
                              SET successful_sales = player_reputation.successful_sales + 1,
                                  reputation_score = player_reputation.reputation_score + 1,
                                  dispute_count = player_reputation.dispute_count
                            """,
                            (seller_id,),
                        )
                        cur.execute(
                            """
                            INSERT INTO player_reputation (player_id, successful_purchases)
                            VALUES (%s, 1)
                            ON CONFLICT (player_id) DO UPDATE
                              SET successful_purchases = player_reputation.successful_purchases + 1,
                                  dispute_count = player_reputation.dispute_count
                            """,
                            (buyer_id,),
                        )
                    conn.commit()
                receipt = TradeReceipt(
                    buyer_id=buyer_id,
                    seller_id=seller_id,
                    listing_id=listing_id,
                    hardware_id=hardware_id,
                    quantity=quantity,
                    purchase_price=purchase_price,
                    marketplace_fee=marketplace_fee,
                    seller_proceeds=seller_proceeds,
                )
                return TradeResult(success=True, receipt=receipt)
            except SerializationFailure:
                continue
        return TradeResult(success=False, error="concurrent_modification_retry")

    def get_player_reputation(self, player_id: str) -> PlayerReputation:
        if not database_is_configured():
            return PlayerReputation(
                player_id=player_id,
                successful_sales=0,
                successful_purchases=0,
                dispute_count=0,
                reputation_score=Decimal("0"),
            )

        with open_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT player_id, successful_sales, successful_purchases,
                           dispute_count, reputation_score
                    FROM player_reputation
                    WHERE player_id = %s
                    """,
                    (player_id,),
                )
                row = cur.fetchone()
        if row is None:
            return PlayerReputation(
                player_id=player_id,
                successful_sales=0,
                successful_purchases=0,
                dispute_count=0,
                reputation_score=Decimal("0"),
            )
        return PlayerReputation(
            player_id=row[0],
            successful_sales=int(row[1]),
            successful_purchases=int(row[2]),
            dispute_count=int(row[3]),
            reputation_score=Decimal(str(row[4])),
        )

    @staticmethod
    def _parse_player_uuid(player_id: str, *, error: str) -> UUID:
        try:
            return UUID(player_id)
        except ValueError as exc:
            raise ValueError(error) from exc

    @staticmethod
    def _get_player_credit_balance(cursor: object, player_id: str) -> Decimal:
        cursor.execute(
            """
            SELECT COALESCE(SUM(amount), 0)
            FROM economy_player_ledger_entries
            WHERE player_id = %s
              AND currency = 'credits'
              AND entry_type = ANY(%s)
            """,
            (player_id, list(_CREDIT_LEDGER_ENTRY_TYPES)),
        )
        row = cursor.fetchone()
        return Decimal("0") if row is None or row[0] is None else Decimal(str(row[0]))
