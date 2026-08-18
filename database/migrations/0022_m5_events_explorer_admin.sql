-- M5-CONTENT-02/03/04: Events, Chain Explorer, Admin Dashboard foundations

CREATE TABLE IF NOT EXISTS game_events (
    event_id         UUID         NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    event_name       TEXT         NOT NULL,
    event_type       TEXT         NOT NULL CHECK (event_type IN ('timed', 'fork')),
    start_at         TIMESTAMPTZ  NOT NULL,
    end_at           TIMESTAMPTZ  NOT NULL,
    modifier_type    TEXT         CHECK (modifier_type IN ('reward_multiplier', 'difficulty_modifier')),
    modifier_value   NUMERIC(18,6),
    rollout_stage    TEXT         NOT NULL DEFAULT 'internal',
    status           TEXT         NOT NULL DEFAULT 'scheduled'
                                 CHECK (status IN ('scheduled', 'active', 'completed', 'cancelled', 'archived')),
    cancelled_reason TEXT,
    created_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    updated_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS event_leaderboard (
    event_id                    UUID         NOT NULL REFERENCES game_events(event_id) ON DELETE CASCADE,
    player_id                   TEXT         NOT NULL,
    event_contribution_score    NUMERIC(38,6) NOT NULL DEFAULT 0,
    rank                        INTEGER,
    updated_at                  TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, player_id)
);

CREATE TABLE IF NOT EXISTS event_rewards (
    event_reward_id  UUID         NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id         UUID         NOT NULL REFERENCES game_events(event_id) ON DELETE CASCADE,
    player_id        TEXT         NOT NULL,
    reward_type      TEXT         NOT NULL,
    reward_data      JSONB        NOT NULL DEFAULT '{}'::jsonb,
    awarded_at       TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS fork_event_branches (
    branch_id          UUID          NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id           UUID          NOT NULL REFERENCES game_events(event_id) ON DELETE CASCADE,
    branch_name        TEXT          NOT NULL,
    accumulated_work   NUMERIC(38,6) NOT NULL DEFAULT 0,
    winning_branch     BOOLEAN       NOT NULL DEFAULT FALSE,
    archived_at        TIMESTAMPTZ,
    resolved_at        TIMESTAMPTZ,
    created_at         TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    UNIQUE (event_id, branch_name)
);

CREATE TABLE IF NOT EXISTS event_balance_snapshots (
    event_id        UUID          NOT NULL REFERENCES game_events(event_id) ON DELETE CASCADE,
    player_id       TEXT          NOT NULL,
    balance_before  NUMERIC(38,6) NOT NULL,
    captured_at     TIMESTAMPTZ   NOT NULL DEFAULT NOW(),
    PRIMARY KEY (event_id, player_id)
);

CREATE INDEX IF NOT EXISTS idx_game_events_status_window
    ON game_events (status, start_at, end_at);

CREATE INDEX IF NOT EXISTS idx_event_leaderboard_score
    ON event_leaderboard (event_id, event_contribution_score DESC);

CREATE INDEX IF NOT EXISTS idx_fork_event_branches_event
    ON fork_event_branches (event_id, accumulated_work DESC);

-- Chain explorer views
CREATE OR REPLACE VIEW v_block_summary AS
SELECT
    fb.block_number,
    CONCAT('block-', fb.block_number::text) AS block_id,
    fb.required_work AS difficulty,
    COALESCE(pool.reward_pool, 0) AS reward_pool,
    COALESCE(miners.miners_count, 0) AS miners_count,
    fb.finalized_at AS completion_time
FROM blockchain_finalized_blocks fb
LEFT JOIN (
    SELECT reference_block_number AS block_number, SUM(amount) AS reward_pool
    FROM economy_ledger_entries
    WHERE entry_type = 'block.finalized.reward_pool.v1'
    GROUP BY reference_block_number
) pool ON pool.block_number = fb.block_number
LEFT JOIN (
    SELECT block_number, COUNT(DISTINCT player_id) AS miners_count
    FROM economy_player_ledger_entries
    WHERE entry_type = 'block.finalized.player_reward.v1'
    GROUP BY block_number
) miners ON miners.block_number = fb.block_number;

CREATE OR REPLACE VIEW v_player_contribution_history AS
SELECT
    pel.player_id,
    pel.block_number,
    pel.contribution_hashes AS contribution_amount,
    pel.amount AS reward_earned,
    pel.created_at AS "timestamp"
FROM economy_player_ledger_entries pel
WHERE pel.entry_type = 'block.finalized.player_reward.v1';

CREATE OR REPLACE VIEW v_transaction_ledger AS
SELECT
    pel.ledger_entry_id::text AS transaction_id,
    NULLIF(pel.metadata->>'from_player', '') AS from_player,
    COALESCE(NULLIF(pel.metadata->>'to_player', ''), pel.player_id) AS to_player,
    pel.amount,
    CASE
        WHEN pel.entry_type = 'block.finalized.player_reward.v1' THEN 'reward'
        WHEN pel.entry_type = 'market.purchase.v1' THEN 'purchase'
        WHEN pel.entry_type = 'player.equipment_trade.v1' THEN 'trade'
        WHEN pel.entry_type = 'pool.reward_distribution.v1' THEN 'pool_distribution'
        ELSE pel.entry_type
    END AS type,
    pel.created_at AS "timestamp",
    pel.player_id
FROM economy_player_ledger_entries pel;

CREATE OR REPLACE VIEW v_pool_history AS
SELECT
    pm.pool_id::text AS pool_id,
    'member_joined'::text AS event_type,
    pm.player_id,
    0::NUMERIC(38,6) AS amount,
    pm.joined_at AS "timestamp"
FROM pool_members pm
UNION ALL
SELECT
    pm.pool_id::text AS pool_id,
    'member_left'::text AS event_type,
    pm.player_id,
    0::NUMERIC(38,6) AS amount,
    pm.left_at AS "timestamp"
FROM pool_members pm
WHERE pm.left_at IS NOT NULL
UNION ALL
SELECT
    COALESCE(pel.metadata->>'pool_id', '') AS pool_id,
    'reward_distributed'::text AS event_type,
    pel.player_id,
    pel.amount AS amount,
    pel.created_at AS "timestamp"
FROM economy_player_ledger_entries pel
WHERE pel.entry_type = 'pool.reward_distribution.v1';

CREATE INDEX IF NOT EXISTS idx_economy_player_ledger_entries_player_timestamp
    ON economy_player_ledger_entries (player_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_blockchain_finalized_blocks_number_time
    ON blockchain_finalized_blocks (block_number DESC, finalized_at DESC);

CREATE INDEX IF NOT EXISTS idx_pool_members_pool_timestamp
    ON pool_members (pool_id, joined_at DESC);

CREATE TABLE IF NOT EXISTS admin_roles (
    admin_id       TEXT         NOT NULL,
    role           TEXT         NOT NULL CHECK (role IN ('admin', 'moderator', 'analyst')),
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    revoked_at     TIMESTAMPTZ,
    notes          TEXT         NOT NULL DEFAULT '',
    PRIMARY KEY (admin_id, role)
);

CREATE TABLE IF NOT EXISTS admin_config_values (
    config_key     TEXT         PRIMARY KEY,
    config_value   JSONB        NOT NULL,
    updated_by     TEXT         NOT NULL,
    updated_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_audit_log (
    audit_id       BIGSERIAL    PRIMARY KEY,
    admin_id       TEXT         NOT NULL,
    action_type    TEXT         NOT NULL,
    resource_id    TEXT         NOT NULL,
    old_value      JSONB,
    new_value      JSONB,
    reason         TEXT         NOT NULL DEFAULT '',
    twofa_verified BOOLEAN      NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    ip_address     TEXT         NOT NULL DEFAULT '',
    user_agent     TEXT         NOT NULL DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_created
    ON admin_audit_log (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_admin_audit_log_admin
    ON admin_audit_log (admin_id, created_at DESC);
