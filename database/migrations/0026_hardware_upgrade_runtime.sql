-- UI Phase 4: server-owned, time-based hardware upgrade runtime

CREATE TABLE IF NOT EXISTS hardware_upgrade_operations (
    upgrade_id          UUID         NOT NULL PRIMARY KEY DEFAULT gen_random_uuid(),
    player_id           UUID         NOT NULL REFERENCES players(player_id) ON DELETE CASCADE,
    hardware_id         TEXT         NOT NULL,
    previous_hardware_id TEXT         NOT NULL,
    idempotency_key     TEXT         NOT NULL,
    status              TEXT         NOT NULL DEFAULT 'running'
                        CHECK (status IN ('running', 'completed', 'rejected', 'cancelled')),
    cost                NUMERIC(38,6) NOT NULL,
    started_at          TIMESTAMPTZ  NOT NULL,
    completes_at        TIMESTAMPTZ  NOT NULL,
    completed_at        TIMESTAMPTZ,
    rejection_reason    TEXT,
    created_at          TIMESTAMPTZ  NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, idempotency_key)
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_hardware_upgrade_one_running_per_player
    ON hardware_upgrade_operations (player_id)
    WHERE status = 'running';

CREATE INDEX IF NOT EXISTS idx_hardware_upgrade_player_status
    ON hardware_upgrade_operations (player_id, status, started_at DESC);
