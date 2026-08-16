CREATE TABLE IF NOT EXISTS network_events (
    sequence BIGSERIAL PRIMARY KEY,
    event_type TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);

CREATE INDEX IF NOT EXISTS idx_network_events_sequence ON network_events (sequence);
