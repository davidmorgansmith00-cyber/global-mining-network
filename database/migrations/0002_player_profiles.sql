CREATE TABLE IF NOT EXISTS player_profiles (
    player_id UUID PRIMARY KEY REFERENCES players(player_id),
    starter_hardware_id TEXT NOT NULL,
    starter_hardware_name TEXT NOT NULL,
    starter_hashrate_hps BIGINT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);