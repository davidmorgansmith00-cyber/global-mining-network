CREATE TABLE IF NOT EXISTS economy_player_ledger_entries (
    ledger_entry_id UUID PRIMARY KEY,
    block_number BIGINT NOT NULL,
    player_id TEXT NOT NULL,
    amount NUMERIC(38, 6) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'credits',
    entry_type TEXT NOT NULL,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_economy_player_ledger_entries_block_number
    ON economy_player_ledger_entries (block_number);

CREATE INDEX IF NOT EXISTS idx_economy_player_ledger_entries_player_id
    ON economy_player_ledger_entries (player_id);
