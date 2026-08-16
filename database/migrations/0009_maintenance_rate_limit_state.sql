CREATE TABLE IF NOT EXISTS maintenance_cleanup_rate_limit_state (
    state_key TEXT PRIMARY KEY,
    window_started_at TIMESTAMPTZ NOT NULL,
    request_count INTEGER NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
