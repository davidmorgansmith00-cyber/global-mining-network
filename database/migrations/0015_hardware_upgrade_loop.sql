-- GMN-EC-06: Starter Upgrade Loop
-- Adds hardware tier metadata columns, seeds tier 2/3 hardware definitions,
-- and adds previous_item_id to ledger entries for upgrade audit trail.

ALTER TABLE hardware_definitions
    ADD COLUMN IF NOT EXISTS tier INTEGER NOT NULL DEFAULT 1,
    ADD COLUMN IF NOT EXISTS market_price NUMERIC(38, 6) NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS unlock_condition TEXT,
    ADD COLUMN IF NOT EXISTS previous_tier TEXT,
    ADD COLUMN IF NOT EXISTS next_tier TEXT;

-- Back-fill tier 1 metadata for existing starter hardware.
UPDATE hardware_definitions
SET tier = 1,
    market_price = 0,
    unlock_condition = NULL,
    previous_tier = NULL,
    next_tier = 'improved_workstation'
WHERE hardware_id = 'starter_rusty_home_computer';

UPDATE hardware_definitions
SET tier = 1,
    market_price = 0,
    unlock_condition = NULL,
    previous_tier = NULL,
    next_tier = 'improved_workstation'
WHERE hardware_id = 'starter_improved_home_computer';

-- Insert tier 2 and tier 3 hardware definitions.
INSERT INTO hardware_definitions (
    hardware_id,
    base_hashrate,
    base_power_consumption,
    heat_generation,
    heat_dissipation_rate_per_minute,
    tier,
    market_price,
    unlock_condition,
    previous_tier,
    next_tier
)
VALUES
    (
        'improved_workstation',
        25.0,
        180.0,
        90.0,
        0.05,
        2,
        2500.000000,
        NULL,
        'starter_rusty_home_computer',
        'professional_mining_rig'
    ),
    (
        'professional_mining_rig',
        60.0,
        300.0,
        150.0,
        0.05,
        3,
        8000.000000,
        'tier >= 2',
        'improved_workstation',
        NULL
    )
ON CONFLICT (hardware_id) DO NOTHING;

-- Add previous_item_id to economy ledger entries to track hardware upgrades.
ALTER TABLE economy_player_ledger_entries
    ADD COLUMN IF NOT EXISTS previous_item_id TEXT;
