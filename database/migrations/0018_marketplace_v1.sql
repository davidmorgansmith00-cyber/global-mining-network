-- GMN-SC-03: Player Marketplace v1
CREATE TABLE IF NOT EXISTS equipment_listings (
    listing_id          UUID           NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    seller_id           TEXT           NOT NULL,
    hardware_id         TEXT           NOT NULL,
    quantity_total      INTEGER        NOT NULL,
    quantity_remaining  INTEGER        NOT NULL,
    price_per_unit      NUMERIC(38,6)  NOT NULL,
    listed_at           TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    expires_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW() + INTERVAL '30 days',
    status              TEXT           NOT NULL DEFAULT 'active'
);

CREATE TABLE IF NOT EXISTS player_reputation (
    player_id             TEXT          NOT NULL PRIMARY KEY,
    successful_sales      INTEGER       NOT NULL DEFAULT 0,
    successful_purchases  INTEGER       NOT NULL DEFAULT 0,
    dispute_count         INTEGER       NOT NULL DEFAULT 0,
    reputation_score      NUMERIC(5,2)  NOT NULL DEFAULT 0
);

CREATE INDEX IF NOT EXISTS idx_equipment_listings_seller ON equipment_listings (seller_id);
CREATE INDEX IF NOT EXISTS idx_equipment_listings_hardware ON equipment_listings (hardware_id) WHERE status = 'active';
