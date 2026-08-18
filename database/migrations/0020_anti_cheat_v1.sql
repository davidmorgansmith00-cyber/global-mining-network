-- GMN-SC-06: Anti-Cheat v1
CREATE TABLE IF NOT EXISTS anti_cheat_actions (
    action_id       UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    player_id       TEXT        NOT NULL,
    action_type     TEXT        NOT NULL,
    reason          TEXT        NOT NULL,
    anomaly_score   INTEGER     NOT NULL DEFAULT 0,
    evidence_json   JSONB       NOT NULL DEFAULT '{}',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    expires_at      TIMESTAMPTZ,
    appealed_at     TIMESTAMPTZ,
    appeal_status   TEXT
);

CREATE TABLE IF NOT EXISTS anti_cheat_events (
    event_id        UUID        NOT NULL DEFAULT gen_random_uuid() PRIMARY KEY,
    player_id       TEXT        NOT NULL,
    event_type      TEXT        NOT NULL,
    check_passed    BOOLEAN     NOT NULL DEFAULT TRUE,
    anomaly_score   INTEGER     NOT NULL DEFAULT 0,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_anti_cheat_actions_player ON anti_cheat_actions (player_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_anti_cheat_events_player ON anti_cheat_events (player_id, created_at DESC);
