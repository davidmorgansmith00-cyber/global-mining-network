CREATE TABLE IF NOT EXISTS difficulty_settings (
    singleton_id BOOLEAN PRIMARY KEY DEFAULT TRUE,
    target_block_seconds INTEGER NOT NULL,
    history_window_size INTEGER NOT NULL,
    max_upward_adjustment_pct NUMERIC(10, 6) NOT NULL,
    max_downward_adjustment_pct NUMERIC(10, 6) NOT NULL,
    minimum_required_work NUMERIC(38, 6) NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    CHECK (singleton_id = TRUE)
);

INSERT INTO difficulty_settings (
    singleton_id,
    target_block_seconds,
    history_window_size,
    max_upward_adjustment_pct,
    max_downward_adjustment_pct,
    minimum_required_work
)
VALUES (TRUE, 10, 10, 0.200000, 0.200000, 1.000000)
ON CONFLICT (singleton_id) DO NOTHING;
