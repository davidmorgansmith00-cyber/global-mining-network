"""GMN-EC-08: Progression Funnel Telemetry.

Provides fire-and-forget event emission (PlayerTelemetryService) that queues
structured telemetry events in an in-memory buffer.  A background worker
drains the buffer, persists events to the local telemetry_events table (for
audit and replay), and optionally forwards batches to a configurable external
analytics backend (Amplitude, Mixpanel, or a generic HTTP endpoint).

Design constraints:
- All emission methods return immediately (non-blocking).
- No single analytics-backend failure should affect the player experience.
- Events are always stored locally regardless of backend availability.
"""

from __future__ import annotations

import json
import queue
import threading
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4

from shared.database import database_is_configured, open_connection
from shared.logging import get_logger
from shared.settings import settings


logger = get_logger("gmn.telemetry")

# ---------------------------------------------------------------------------
# Event types (AC-1)
# ---------------------------------------------------------------------------

EVENT_TIER_UPGRADED = "tier_upgraded"
EVENT_HARDWARE_PURCHASED = "hardware_purchased"
EVENT_OFFLINE_PROGRESS = "offline_progress"
EVENT_SESSION_START = "session_start"
EVENT_SESSION_END = "session_end"
EVENT_BALANCE_MILESTONE = "balance_milestone"

# Milestone thresholds at which a balance_milestone event is emitted (AC-6)
BALANCE_MILESTONES: list[Decimal] = [
    Decimal("1000"),
    Decimal("5000"),
    Decimal("10000"),
    Decimal("25000"),
    Decimal("50000"),
    Decimal("100000"),
]


# ---------------------------------------------------------------------------
# Event dataclass (AC-2, AC-3)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TelemetryEvent:
    event_id: str
    event_type: str
    player_id: str
    session_id: str | None
    timestamp: datetime
    properties: dict[str, Any]


# ---------------------------------------------------------------------------
# Analytics backend (AC-5)
# ---------------------------------------------------------------------------

class AnalyticsBackendService:
    """Sends batches of events to the configured external analytics backend.

    Backends are selected via the ANALYTICS_BACKEND environment variable:
      amplitude  - Amplitude HTTP API v2
      mixpanel   - Mixpanel /track HTTP API
      http       - Generic HTTP endpoint configured via ANALYTICS_HTTP_URL
      noop       - Silently discard (default / dev)
    """

    def __init__(self) -> None:
        self._backend: str = settings.analytics_backend
        self._http_url: str = settings.analytics_http_url
        self._api_key: str = settings.analytics_api_key

    def send_batch(self, events: list[TelemetryEvent]) -> None:
        """Send a batch of events to the external backend (blocking, called from worker)."""
        if not events:
            return
        backend = self._backend
        if backend == "amplitude":
            self._send_amplitude(events)
        elif backend == "mixpanel":
            self._send_mixpanel(events)
        elif backend == "http":
            self._send_http(events)
        # noop: do nothing

    # -- backend-specific serialisers --

    def _send_amplitude(self, events: list[TelemetryEvent]) -> None:
        if not self._http_url and not self._api_key:
            return
        url = self._http_url or "https://api2.amplitude.com/2/httpapi"
        payload = {
            "api_key": self._api_key,
            "events": [
                {
                    "event_type": e.event_type,
                    "user_id": e.player_id,
                    "session_id": e.session_id,
                    "time": int(e.timestamp.timestamp() * 1000),
                    "event_properties": e.properties,
                    "insert_id": e.event_id,
                }
                for e in events
            ],
        }
        self._post_json(url, payload)

    def _send_mixpanel(self, events: list[TelemetryEvent]) -> None:
        if not self._api_key:
            return
        url = self._http_url or "https://api.mixpanel.com/track"
        payload = [
            {
                "event": e.event_type,
                "properties": {
                    "distinct_id": e.player_id,
                    "token": self._api_key,
                    "time": int(e.timestamp.timestamp()),
                    "$insert_id": e.event_id,
                    **e.properties,
                },
            }
            for e in events
        ]
        self._post_json(url, payload)

    def _send_http(self, events: list[TelemetryEvent]) -> None:
        if not self._http_url:
            return
        payload = [_event_to_dict(e) for e in events]
        self._post_json(self._http_url, payload)

    def _post_json(self, url: str, payload: Any) -> None:
        try:
            import urllib.request  # stdlib only – no new dependencies

            body = json.dumps(payload, default=str).encode()
            req = urllib.request.Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
                if resp.status >= 400:
                    logger.warning(
                        "analytics_backend_http_error",
                        extra={"url": url, "status": resp.status},
                    )
        except Exception as exc:
            logger.warning(
                "analytics_backend_send_failed",
                extra={"url": url, "error": str(exc)},
            )


# ---------------------------------------------------------------------------
# Telemetry worker (AC-4, AC-9)
# ---------------------------------------------------------------------------

_BATCH_SIZE = 100
_FLUSH_INTERVAL_SECONDS = 30.0
_MAX_RETRIES = 5


class _TelemetryWorker(threading.Thread):
    """Background daemon thread that drains the event buffer."""

    def __init__(self, buf: queue.Queue[TelemetryEvent], backend: AnalyticsBackendService) -> None:
        super().__init__(name="gmn-telemetry-worker", daemon=True)
        self._buf = buf
        self._backend = backend

    def run(self) -> None:
        last_flush_at = time.monotonic()
        pending: list[TelemetryEvent] = []

        while True:
            now = time.monotonic()
            timeout = max(0.0, _FLUSH_INTERVAL_SECONDS - (now - last_flush_at))
            try:
                event = self._buf.get(timeout=timeout)
                pending.append(event)
            except queue.Empty:
                pass

            time_elapsed = (time.monotonic() - last_flush_at) >= _FLUSH_INTERVAL_SECONDS
            if len(pending) >= _BATCH_SIZE or (pending and time_elapsed):
                self._flush(pending)
                pending = []
                last_flush_at = time.monotonic()

    def _flush(self, events: list[TelemetryEvent]) -> None:
        if not events:
            return
        # Persist locally first (audit trail).
        self._persist(events)
        # Forward to the external backend in a separate daemon thread so that
        # retry sleeps never block the worker from draining and persisting new
        # events (AC-9: fire-and-forget at every level).
        threading.Thread(
            target=self._send_with_retries,
            args=(events,),
            daemon=True,
            name="gmn-telemetry-send",
        ).start()

    def _send_with_retries(self, events: list[TelemetryEvent]) -> None:
        for attempt in range(_MAX_RETRIES):
            try:
                self._backend.send_batch(events)
                self._mark_sent(events)
                return
            except Exception as exc:
                backoff = 2 ** attempt
                logger.warning(
                    "analytics_batch_send_failed",
                    extra={"attempt": attempt + 1, "backoff": backoff, "error": str(exc)},
                )
                time.sleep(backoff)
        logger.warning(
            "analytics_batch_send_exhausted",
            extra={"max_retries": _MAX_RETRIES, "event_count": len(events)},
        )

    def _persist(self, events: list[TelemetryEvent]) -> None:
        if not database_is_configured():
            return
        rows = [
            (
                UUID(e.event_id),
                e.event_type,
                e.player_id,
                e.session_id,
                e.timestamp,
                json.dumps(e.properties, default=str),
            )
            for e in events
        ]
        try:
            with open_connection() as conn:
                with conn.cursor() as cur:
                    cur.executemany(
                        """
                        INSERT INTO telemetry_events
                            (event_id, event_type, player_id, session_id, timestamp, properties_json)
                        VALUES (%s, %s, %s, %s, %s, %s::jsonb)
                        ON CONFLICT (event_id) DO NOTHING
                        """,
                        rows,
                    )
                conn.commit()
        except Exception as exc:
            logger.warning("telemetry_persist_failed", extra={"error": str(exc)})

    def _mark_sent(self, events: list[TelemetryEvent]) -> None:
        if not database_is_configured():
            return
        now = datetime.now(tz=UTC)
        ids = [UUID(e.event_id) for e in events]
        try:
            with open_connection() as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        UPDATE telemetry_events
                        SET sent_to_backend_at = %s
                        WHERE event_id = ANY(%s)
                          AND sent_to_backend_at IS NULL
                        """,
                        (now, ids),
                    )
                conn.commit()
        except Exception as exc:
            logger.warning("telemetry_mark_sent_failed", extra={"error": str(exc)})


# ---------------------------------------------------------------------------
# Player Telemetry Service (AC-1, AC-2, AC-3, AC-9, AC-10)
# ---------------------------------------------------------------------------

class PlayerTelemetryService:
    """Fire-and-forget structured event emitter for player progression analytics.

    All public ``emit_*`` methods return immediately.  Events are queued to an
    in-memory thread-safe buffer and drained by a background daemon thread.
    """

    def __init__(
        self,
        *,
        buf: "queue.Queue[TelemetryEvent] | None" = None,
        backend: AnalyticsBackendService | None = None,
    ) -> None:
        self._buf: queue.Queue[TelemetryEvent] = buf if buf is not None else queue.Queue()
        self._backend = backend or AnalyticsBackendService()
        self._worker = _TelemetryWorker(self._buf, self._backend)
        self._worker.start()

    # -- public emit methods --

    def emit_tier_upgraded(
        self,
        *,
        player_id: str,
        from_tier: int,
        to_tier: int,
        blocks_finalized_count: int,
        session_id: str | None = None,
    ) -> None:
        self._enqueue(
            event_type=EVENT_TIER_UPGRADED,
            player_id=player_id,
            session_id=session_id,
            properties={
                "player_tier": from_tier,
                "player_tier_new": to_tier,
                "blocks_finalized_count": blocks_finalized_count,
            },
        )

    def emit_hardware_purchased(
        self,
        *,
        player_id: str,
        hardware_id: str,
        previous_hardware_id: str | None,
        cost: Decimal,
        player_tier: int,
        session_id: str | None = None,
    ) -> None:
        self._enqueue(
            event_type=EVENT_HARDWARE_PURCHASED,
            player_id=player_id,
            session_id=session_id,
            properties={
                "hardware_id": hardware_id,
                "hardware_previous": previous_hardware_id,
                "cost_paid": float(cost),
                "player_tier": player_tier,
            },
        )

    def emit_offline_progress(
        self,
        *,
        player_id: str,
        offline_duration_seconds: int,
        work_credited: Decimal,
        cap_applied: bool,
        offline_cap_tier: int,
        session_id: str | None = None,
    ) -> None:
        self._enqueue(
            event_type=EVENT_OFFLINE_PROGRESS,
            player_id=player_id,
            session_id=session_id,
            properties={
                "offline_duration_seconds": offline_duration_seconds,
                "offline_work_credited": float(work_credited),
                "offline_cap_applied": cap_applied,
                "player_tier": offline_cap_tier,
            },
        )

    def emit_session_start(
        self,
        *,
        player_id: str,
        session_id: str,
        player_tier: int,
    ) -> None:
        self._enqueue(
            event_type=EVENT_SESSION_START,
            player_id=player_id,
            session_id=session_id,
            properties={"player_tier": player_tier},
        )

    def emit_session_end(
        self,
        *,
        player_id: str,
        session_id: str,
        session_duration_seconds: int,
    ) -> None:
        self._enqueue(
            event_type=EVENT_SESSION_END,
            player_id=player_id,
            session_id=session_id,
            properties={"session_duration_seconds": session_duration_seconds},
        )

    def emit_balance_milestone(
        self,
        *,
        player_id: str,
        milestone_amount: Decimal,
        balance_before: Decimal,
        balance_after: Decimal,
        session_id: str | None = None,
    ) -> None:
        self._enqueue(
            event_type=EVENT_BALANCE_MILESTONE,
            player_id=player_id,
            session_id=session_id,
            properties={
                "milestone_amount": float(milestone_amount),
                "balance_before": float(balance_before),
                "balance_after": float(balance_after),
            },
        )

    # -- internal helpers --

    def _enqueue(
        self,
        *,
        event_type: str,
        player_id: str,
        session_id: str | None,
        properties: dict[str, Any],
    ) -> None:
        event = TelemetryEvent(
            event_id=str(uuid4()),
            event_type=event_type,
            player_id=player_id,
            session_id=session_id,
            timestamp=datetime.now(tz=UTC),
            properties=properties,
        )
        try:
            self._buf.put_nowait(event)
        except queue.Full:
            logger.warning(
                "telemetry_buffer_full",
                extra={"event_type": event_type, "player_id": player_id},
            )

    # -- balance milestone helper --

    @staticmethod
    def crossed_milestones(balance_before: Decimal, balance_after: Decimal) -> list[Decimal]:
        """Return any milestone thresholds crossed between two balance values."""
        return [
            m
            for m in BALANCE_MILESTONES
            if balance_before < m <= balance_after
        ]


# ---------------------------------------------------------------------------
# Module-level singleton (used by hooks in other services)
# ---------------------------------------------------------------------------

_telemetry_instance: PlayerTelemetryService | None = None
_telemetry_lock = threading.Lock()


def get_telemetry_service() -> PlayerTelemetryService:
    """Return the process-wide PlayerTelemetryService singleton."""
    global _telemetry_instance  # noqa: PLW0603
    if _telemetry_instance is None:
        with _telemetry_lock:
            if _telemetry_instance is None:
                _telemetry_instance = PlayerTelemetryService()
    return _telemetry_instance


# ---------------------------------------------------------------------------
# Funnel query helpers (AC-6, AC-7, AC-8)
# ---------------------------------------------------------------------------

def query_funnel_cohort_conversion(cohort_date: str) -> dict[str, Any]:
    """Return Tier 1/2/3 conversion rates for the given cohort date (YYYY-MM-DD)."""
    if not database_is_configured():
        return {"error": "database_unavailable"}
    with open_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    COUNT(*) AS cohort_size,
                    COUNT(*) FILTER (WHERE player_tier >= 2) AS tier2_count,
                    COUNT(*) FILTER (WHERE player_tier >= 3) AS tier3_count
                FROM players
                WHERE created_at >= %s::date
                  AND created_at <  %s::date + INTERVAL '1 day'
                """,
                (cohort_date, cohort_date),
            )
            row = cur.fetchone()
    if row is None or row[0] == 0:
        return {"cohort_date": cohort_date, "cohort_size": 0, "tier2_conversion": 0.0, "tier3_conversion": 0.0}
    cohort_size, tier2_count, tier3_count = row
    return {
        "cohort_date": cohort_date,
        "cohort_size": cohort_size,
        "tier2_count": tier2_count,
        "tier3_count": tier3_count,
        "tier2_conversion": round(tier2_count / cohort_size, 4),
        "tier3_conversion": round(tier3_count / cohort_size, 4),
    }


def query_funnel_time_to_tier(tier: int) -> dict[str, Any]:
    """Return median seconds from player creation to reaching the given tier."""
    if not database_is_configured():
        return {"error": "database_unavailable"}
    with open_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    PERCENTILE_CONT(0.5) WITHIN GROUP (
                        ORDER BY EXTRACT(EPOCH FROM (te.timestamp - p.created_at))
                    ) AS median_seconds,
                    COUNT(*) AS sample_count
                FROM players p
                JOIN telemetry_events te
                  ON p.player_id::text = te.player_id
                WHERE te.event_type = 'tier_upgraded'
                  AND (te.properties_json->>'player_tier_new')::int = %s
                """,
                (tier,),
            )
            row = cur.fetchone()
    if row is None or row[0] is None:
        return {"tier": tier, "median_seconds": None, "sample_count": 0}
    return {"tier": tier, "median_seconds": float(row[0]), "sample_count": int(row[1])}


def query_retention_funnel(tier: int | None) -> list[dict[str, Any]]:
    """Return player counts grouped by tier and last-activity recency bucket."""
    if not database_is_configured():
        return [{"error": "database_unavailable"}]
    query = """
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
                COALESCE(
                    (properties_json->>'player_tier')::int,
                    1
                ) AS player_tier,
                EXTRACT(EPOCH FROM (NOW() - MAX(timestamp))) AS last_activity_seconds
            FROM telemetry_events
            GROUP BY player_id, player_tier
        ) t
        {where}
        GROUP BY player_tier, activity_bucket
        ORDER BY player_tier, activity_bucket
    """
    where = "WHERE player_tier = %s" if tier is not None else ""
    params = (tier,) if tier is not None else ()
    with open_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query.format(where=where), params)
            rows = cur.fetchall()
    return [
        {"player_tier": row[0], "activity_bucket": row[1], "player_count": row[2]}
        for row in rows
    ]


def query_churn_risk_players() -> list[dict[str, Any]]:
    """Return tier 1/2 players inactive for 7+ days (churn risk)."""
    if not database_is_configured():
        return [{"error": "database_unavailable"}]
    with open_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
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
                ORDER BY inactive_seconds DESC
                LIMIT 500
                """
            )
            rows = cur.fetchall()
    return [
        {
            "player_id": row[0],
            "player_tier": row[1],
            "inactive_seconds": float(row[2]),
        }
        for row in rows
    ]


def query_purchase_frequency() -> dict[str, Any]:
    """Return average hardware purchases per player, broken down by cohort month."""
    if not database_is_configured():
        return {"error": "database_unavailable"}
    with open_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT
                    TO_CHAR(DATE_TRUNC('month', p.created_at), 'YYYY-MM') AS cohort_month,
                    COUNT(te.event_id) AS total_purchases,
                    COUNT(DISTINCT te.player_id) AS purchasing_players,
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
                ORDER BY cohort_month
                """
            )
            rows = cur.fetchall()
    return {
        "cohorts": [
            {
                "cohort_month": row[0],
                "total_purchases": row[1],
                "purchasing_players": row[2],
                "avg_purchases_per_player": float(row[3]) if row[3] is not None else 0.0,
            }
            for row in rows
        ]
    }


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------

def _event_to_dict(e: TelemetryEvent) -> dict[str, Any]:
    return {
        "event_id": e.event_id,
        "event_type": e.event_type,
        "player_id": e.player_id,
        "session_id": e.session_id,
        "timestamp": e.timestamp.isoformat(),
        "properties": e.properties,
    }
