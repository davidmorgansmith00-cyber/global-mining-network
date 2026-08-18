-- GMN-EC-03: Cooling Dynamics and Efficiency
-- Adds heat-tracking and passive-dissipation columns to the players table and
-- a dissipation-rate column to hardware_definitions.

ALTER TABLE players
    ADD COLUMN IF NOT EXISTS heat_generated NUMERIC(18, 6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS cooling_capacity NUMERIC(18, 6) NOT NULL DEFAULT 100,
    ADD COLUMN IF NOT EXISTS cooling_efficiency_multiplier_cached NUMERIC(18, 6) NOT NULL DEFAULT 1.0,
    ADD COLUMN IF NOT EXISTS last_heat_dissipation_at TIMESTAMPTZ;

ALTER TABLE hardware_definitions
    ADD COLUMN IF NOT EXISTS heat_dissipation_rate_per_minute NUMERIC(6, 4) NOT NULL DEFAULT 0.05;

-- Back-fill existing players: initialise heat_generated from their active hardware,
-- set cooling_capacity to a safe default (100 W equivalent – above starter rig heat),
-- and stamp the dissipation clock.
UPDATE players p
SET
    heat_generated = COALESCE(
        (
            SELECT hd.heat_generation
            FROM hardware_definitions hd
            WHERE hd.hardware_id = COALESCE(p.hardware_id, pp.starter_hardware_id)
        ),
        0
    ),
    cooling_capacity = 100,
    cooling_efficiency_multiplier_cached = 1.0,
    last_heat_dissipation_at = NOW()
FROM player_profiles pp
WHERE p.player_id = pp.player_id;
