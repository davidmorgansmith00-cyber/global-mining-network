-- GMN-EC-08: Progression Funnel Telemetry
-- Adds telemetry_events table for storing structured player progression events.
-- Provides views for funnel conversion, time-to-tier, retention, and churn analysis.

-- ---------------------------------------------------------------------------
-- telemetry_events: immutable audit log of player progression events
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS telemetry_events (
    event_id            UUID        NOT NULL DEFAULT gen_random_uuid(),
    event_type          TEXT        NOT NULL,
    player_id           TEXT        NOT NULL,
    session_id          TEXT,
    timestamp           TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    properties_json     JSONB       NOT NULL DEFAULT '{}',
    sent_to_backend_at  TIMESTAMPTZ,

    PRIMARY KEY (event_id, timestamp)    -- partition key included for pg_partman
) PARTITION BY RANGE (timestamp);

-- Default partition covering all historical and future months until explicit
-- partitions are created.  Add monthly partitions via pg_partman in production.
CREATE TABLE IF NOT EXISTS telemetry_events_default
    PARTITION OF telemetry_events DEFAULT;

-- Index for fast cohort and player-level queries (AC-3)
CREATE INDEX IF NOT EXISTS idx_telemetry_events_player_ts
    ON telemetry_events (player_id, timestamp);

CREATE INDEX IF NOT EXISTS idx_telemetry_events_type_ts
    ON telemetry_events (event_type, timestamp);

-- ---------------------------------------------------------------------------
-- Views: funnel metrics (AC-6, AC-7, AC-8)
-- ---------------------------------------------------------------------------

-- Retention funnel: player counts by tier + last-activity recency bucket
CREATE OR REPLACE VIEW v_retention_funnel AS
SELECT
    player_tier,
    CASE
        WHEN last_activity_seconds < 86400   THEN 'active_24h'
        WHEN last_activity_seconds < 604800  THEN 'active_7d'
        WHEN last_activity_seconds < 2592000 THEN 'active_30d'
        ELSE                                      'inactive_30d'
    END AS activity_bucket,
    COUNT(*) AS player_count
FROM (
    SELECT
        player_id,
        COALESCE((properties_json->>'player_tier')::int, 1) AS player_tier,
        EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))        AS last_activity_seconds
    FROM telemetry_events
    GROUP BY player_id, player_tier
) t
GROUP BY player_tier, activity_bucket;

-- Churn risk: tier 1/2 players inactive 7+ days
CREATE OR REPLACE VIEW v_churn_risk_players AS
SELECT
    player_id,
    player_tier,
    EXTRACT(EPOCH FROM (NOW() - last_activity)) AS inactive_seconds
FROM (
    SELECT
        player_id,
        COALESCE((properties_json->>'player_tier')::int, 1) AS player_tier,
        MAX(timestamp) AS last_activity
    FROM telemetry_events
    GROUP BY player_id, player_tier
) t
WHERE player_tier <= 2
  AND EXTRACT(EPOCH FROM (NOW() - last_activity)) >= 604800
ORDER BY inactive_seconds DESC;

-- Purchase frequency by cohort month
CREATE OR REPLACE VIEW v_purchase_frequency AS
SELECT
    TO_CHAR(DATE_TRUNC('month', p.created_at), 'YYYY-MM') AS cohort_month,
    COUNT(te.event_id)                                     AS total_purchases,
    COUNT(DISTINCT te.player_id)                           AS purchasing_players,
    ROUND(
        COUNT(te.event_id)::numeric /
        NULLIF(COUNT(DISTINCT te.player_id), 0),
        2
    ) AS avg_purchases_per_player
FROM players p
LEFT JOIN telemetry_events te
    ON p.player_id::text = te.player_id
    AND te.event_type = 'hardware_purchased'
GROUP BY cohort_month
ORDER BY cohort_month;
