-- GMN-SC-01: Mining Pools v1
CREATE TABLE IF NOT EXISTS mining_pools (
    pool_id         UUID         NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    owner_id        TEXT         NOT NULL,
    pool_name       TEXT         NOT NULL,
    description     TEXT         NOT NULL DEFAULT '',
    fee_percentage  NUMERIC(5,2) NOT NULL DEFAULT 0,
    status          TEXT         NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    dissolved_at    TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS pool_members (
    pool_id                     UUID          NOT NULL REFERENCES mining_pools(pool_id),
    player_id                   TEXT          NOT NULL,
    joined_at                   TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    left_at                     TIMESTAMPTZ,
    accumulated_reward_at_leave NUMERIC(38,6) NOT NULL DEFAULT 0,
    PRIMARY KEY (pool_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_pool_members_player ON pool_members (player_id) WHERE left_at IS NULL;
CREATE INDEX IF NOT EXISTS idx_mining_pools_status ON mining_pools (status);
