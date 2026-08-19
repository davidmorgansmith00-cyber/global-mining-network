CREATE TABLE IF NOT EXISTS mining_operation_runtime_events (
    event_id UUID PRIMARY KEY,
    operation_id TEXT NOT NULL,
    player_id UUID NOT NULL,
    event_type TEXT NOT NULL,
    base_hashrate_hps NUMERIC(38, 6),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb,
    occurred_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_mining_operation_runtime_events_operation_time
    ON mining_operation_runtime_events (operation_id, occurred_at, created_at, event_id);

CREATE INDEX IF NOT EXISTS idx_mining_operation_runtime_events_player_time
    ON mining_operation_runtime_events (player_id, occurred_at DESC);
