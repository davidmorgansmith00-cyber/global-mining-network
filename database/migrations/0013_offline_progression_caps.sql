ALTER TABLE players
    ADD COLUMN IF NOT EXISTS player_tier INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS blocks_finalized_contributed_count INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS last_offline_progress_at TIMESTAMPTZ;

ALTER TABLE economy_player_ledger_entries
    ALTER COLUMN block_number DROP NOT NULL;

ALTER TABLE economy_player_ledger_entries
    ADD COLUMN IF NOT EXISTS cap_applied BOOLEAN,
    ADD COLUMN IF NOT EXISTS cap_amount NUMERIC(38, 6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS offline_cap_tier INTEGER;

UPDATE players
SET player_tier = COALESCE(player_tier, 1),
    blocks_finalized_contributed_count = COALESCE(blocks_finalized_contributed_count, 0),
    last_offline_progress_at = COALESCE(last_offline_progress_at, NOW()),
    updated_at = NOW();

UPDATE economy_player_ledger_entries
SET cap_applied = COALESCE(cap_applied, FALSE),
    cap_amount = COALESCE(cap_amount, 0)
WHERE cap_applied IS NULL
   OR cap_amount IS NULL;
