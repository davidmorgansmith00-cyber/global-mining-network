ALTER TABLE players
    ADD COLUMN IF NOT EXISTS power_consumed NUMERIC(18, 6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS power_capacity NUMERIC(18, 6) NOT NULL DEFAULT 120,
    ADD COLUMN IF NOT EXISTS power_throttle_multiplier_cached NUMERIC(18, 6) NOT NULL DEFAULT 1.0;

UPDATE players
SET power_consumed = CASE
        WHEN players.power_consumed <= 0 THEN COALESCE(
            (
                SELECT hardware_definitions.base_power_consumption
                FROM hardware_definitions
                WHERE hardware_definitions.hardware_id = COALESCE(players.hardware_id, player_profiles.starter_hardware_id)
            ),
            0
        )
        ELSE players.power_consumed
    END,
    power_capacity = CASE
        WHEN players.power_capacity <= 0 THEN COALESCE(player_profiles.power_capacity, 120)
        ELSE players.power_capacity
    END,
    power_throttle_multiplier_cached = CASE
        WHEN players.power_throttle_multiplier_cached <= 0 THEN 1.0
        ELSE players.power_throttle_multiplier_cached
    END,
    updated_at = NOW()
FROM player_profiles
WHERE players.player_id = player_profiles.player_id;
