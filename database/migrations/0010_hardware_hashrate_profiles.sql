ALTER TABLE players
    ADD COLUMN IF NOT EXISTS hardware_id TEXT,
    ADD COLUMN IF NOT EXISTS effective_hashrate_cached DOUBLE PRECISION,
    ADD COLUMN IF NOT EXISTS effective_hashrate_updated_at TIMESTAMPTZ;

ALTER TABLE player_profiles
    ADD COLUMN IF NOT EXISTS power_available DOUBLE PRECISION NOT NULL DEFAULT 120,
    ADD COLUMN IF NOT EXISTS power_capacity DOUBLE PRECISION NOT NULL DEFAULT 120,
    ADD COLUMN IF NOT EXISTS cooling_efficiency DOUBLE PRECISION NOT NULL DEFAULT 1.0;

CREATE TABLE IF NOT EXISTS hardware_definitions (
    hardware_id TEXT PRIMARY KEY,
    base_hashrate DOUBLE PRECISION NOT NULL,
    base_power_consumption DOUBLE PRECISION NOT NULL,
    heat_generation DOUBLE PRECISION NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

INSERT INTO hardware_definitions (hardware_id, base_hashrate, base_power_consumption, heat_generation)
VALUES
    ('starter_rusty_home_computer', 12, 120, 40),
    ('starter_improved_home_computer', 24, 180, 90)
ON CONFLICT (hardware_id) DO NOTHING;

UPDATE players
SET hardware_id = COALESCE(players.hardware_id, player_profiles.starter_hardware_id),
    effective_hashrate_cached = COALESCE(players.effective_hashrate_cached, player_profiles.starter_hashrate_hps::DOUBLE PRECISION),
    effective_hashrate_updated_at = COALESCE(players.effective_hashrate_updated_at, NOW())
FROM player_profiles
WHERE players.player_id = player_profiles.player_id;
