CREATE TABLE IF NOT EXISTS blockchain_active_block (
    singleton_id BOOLEAN PRIMARY KEY DEFAULT TRUE,
    block_number BIGINT NOT NULL,
    required_work NUMERIC(38, 6) NOT NULL,
    accumulated_work NUMERIC(38, 6) NOT NULL DEFAULT 0,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (singleton_id = TRUE)
);

CREATE TABLE IF NOT EXISTS blockchain_finalized_blocks (
    block_number BIGINT PRIMARY KEY,
    required_work NUMERIC(38, 6) NOT NULL,
    total_work NUMERIC(38, 6) NOT NULL,
    finalized_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS economy_ledger_entries (
    ledger_entry_id UUID PRIMARY KEY,
    entry_type TEXT NOT NULL,
    amount NUMERIC(38, 6) NOT NULL,
    currency TEXT NOT NULL DEFAULT 'credits',
    reference_block_number BIGINT,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_blockchain_finalized_blocks_finalized_at
    ON blockchain_finalized_blocks (finalized_at DESC);

CREATE INDEX IF NOT EXISTS idx_economy_ledger_entries_reference_block
    ON economy_ledger_entries (reference_block_number);
