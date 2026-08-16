ALTER TABLE economy_player_ledger_entries
ADD COLUMN IF NOT EXISTS contribution_hashes NUMERIC(38, 6) NOT NULL DEFAULT 0;
