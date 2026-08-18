CREATE TABLE IF NOT EXISTS npc_market_inventory_state (
    item_id TEXT PRIMARY KEY,
    current_stock BIGINT,
    last_restocked_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS player_inventory (
    player_id UUID NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    item_id TEXT NOT NULL,
    quantity BIGINT NOT NULL CHECK (quantity > 0),
    acquired_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, item_id)
);

ALTER TABLE economy_player_ledger_entries
    ADD COLUMN IF NOT EXISTS item_id TEXT,
    ADD COLUMN IF NOT EXISTS quantity BIGINT,
    ADD COLUMN IF NOT EXISTS unit_price NUMERIC(38, 6),
    ADD COLUMN IF NOT EXISTS total_cost NUMERIC(38, 6);
