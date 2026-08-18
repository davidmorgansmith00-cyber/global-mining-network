-- GMN-SC-04: Leaderboards v1
CREATE TABLE IF NOT EXISTS leaderboard_hashrate (
    rank                INTEGER        NOT NULL,
    player_id           TEXT           NOT NULL PRIMARY KEY,
    player_name         TEXT           NOT NULL DEFAULT '',
    effective_hashrate  NUMERIC(38,6)  NOT NULL DEFAULT 0,
    is_hidden           BOOLEAN        NOT NULL DEFAULT FALSE,
    updated_at          TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leaderboard_pools (
    rank            INTEGER        NOT NULL,
    pool_id         UUID           NOT NULL PRIMARY KEY,
    pool_name       TEXT           NOT NULL DEFAULT '',
    total_hashrate  NUMERIC(38,6)  NOT NULL DEFAULT 0,
    member_count    INTEGER        NOT NULL DEFAULT 0,
    is_hidden       BOOLEAN        NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leaderboard_tier_progression (
    rank            INTEGER        NOT NULL,
    player_id       TEXT           NOT NULL,
    player_name     TEXT           NOT NULL DEFAULT '',
    tier            INTEGER        NOT NULL,
    days_to_reach   NUMERIC(10,2)  NOT NULL DEFAULT 0,
    reached_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    is_hidden       BOOLEAN        NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW(),
    PRIMARY KEY (player_id, tier)
);

CREATE TABLE IF NOT EXISTS leaderboard_weekly_earnings (
    rank            INTEGER        NOT NULL,
    player_id       TEXT           NOT NULL PRIMARY KEY,
    player_name     TEXT           NOT NULL DEFAULT '',
    earnings_7d     NUMERIC(38,6)  NOT NULL DEFAULT 0,
    is_hidden       BOOLEAN        NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leaderboard_wealth (
    rank            INTEGER        NOT NULL,
    player_id       TEXT           NOT NULL PRIMARY KEY,
    player_name     TEXT           NOT NULL DEFAULT '',
    total_wealth    NUMERIC(38,6)  NOT NULL DEFAULT 0,
    is_hidden       BOOLEAN        NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ    NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS leaderboard_visibility (
    player_id       TEXT        NOT NULL PRIMARY KEY,
    is_hidden       BOOLEAN     NOT NULL DEFAULT FALSE,
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
