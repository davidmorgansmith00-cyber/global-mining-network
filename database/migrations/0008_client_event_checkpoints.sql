CREATE TABLE IF NOT EXISTS client_event_checkpoints (
    checkpoint_id UUID PRIMARY KEY,
    player_id UUID NOT NULL,
    session_id UUID NOT NULL,
    channel TEXT NOT NULL,
    reconnect_cursor BIGINT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    UNIQUE (player_id, session_id, channel)
);

CREATE INDEX IF NOT EXISTS idx_client_event_checkpoints_player_session
    ON client_event_checkpoints (player_id, session_id, channel);
