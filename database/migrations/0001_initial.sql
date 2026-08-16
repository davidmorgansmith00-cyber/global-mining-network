CREATE TABLE IF NOT EXISTS players (
    player_id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    session_id UUID PRIMARY KEY,
    player_id UUID NOT NULL REFERENCES players(player_id),
    refresh_token_hash TEXT NOT NULL,
    device_label TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at TIMESTAMPTZ NOT NULL,
    revoked_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS domain_events (
    event_id UUID PRIMARY KEY,
    event_type TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    aggregate_id TEXT NOT NULL,
    occurred_at TIMESTAMPTZ NOT NULL,
    correlation_id UUID NOT NULL,
    causation_id UUID,
    payload JSONB NOT NULL DEFAULT '{}'::jsonb
);