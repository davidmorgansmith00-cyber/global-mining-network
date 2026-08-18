from __future__ import annotations

import hashlib
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any


# ---------------------------------------------------------------------------
# Error Tracker
# ---------------------------------------------------------------------------
@dataclass
class ErrorRecord:
    fingerprint: str
    message: str
    first_seen: datetime
    last_seen: datetime
    count: int
    affected_users: set[str]
    sample_trace: str


class ErrorTracker:
    """In-memory error tracker with deduplication and grouping."""

    def __init__(self) -> None:
        self._errors: dict[str, ErrorRecord] = {}
        self._lock = threading.Lock()

    @staticmethod
    def _fingerprint(exc: Exception) -> str:
        """Normalise exception to a stable fingerprint."""
        raw = f"{type(exc).__name__}:{str(exc)}"
        return hashlib.sha256(raw.encode()).hexdigest()[:16]

    def capture(self, exc: Exception, user_id: str | None = None) -> str:
        fp = self._fingerprint(exc)
        import traceback
        trace = traceback.format_exc()

        with self._lock:
            if fp in self._errors:
                record = self._errors[fp]
                record.count += 1
                record.last_seen = datetime.now(UTC)
                if user_id:
                    record.affected_users.add(user_id)
            else:
                self._errors[fp] = ErrorRecord(
                    fingerprint=fp,
                    message=str(exc),
                    first_seen=datetime.now(UTC),
                    last_seen=datetime.now(UTC),
                    count=1,
                    affected_users={user_id} if user_id else set(),
                    sample_trace=trace,
                )
        return fp

    def get_all(self) -> list[ErrorRecord]:
        with self._lock:
            return list(self._errors.values())

    def get(self, fingerprint: str) -> ErrorRecord | None:
        with self._lock:
            return self._errors.get(fingerprint)


# ---------------------------------------------------------------------------
# Metrics collector (per-endpoint rolling window)
# ---------------------------------------------------------------------------
@dataclass
class EndpointMetrics:
    method: str
    path: str
    request_count: int = 0
    error_count: int = 0
    _latency_samples: deque = field(default_factory=lambda: deque(maxlen=10000))

    def record(self, latency_ms: float, status_code: int) -> None:
        self.request_count += 1
        self._latency_samples.append(latency_ms)
        if status_code >= 400:
            self.error_count += 1

    def percentile(self, p: float) -> float | None:
        if not self._latency_samples:
            return None
        samples = sorted(self._latency_samples)
        idx = int(len(samples) * p / 100)
        return samples[min(idx, len(samples) - 1)]

    @property
    def error_rate(self) -> float:
        if self.request_count == 0:
            return 0.0
        return self.error_count / self.request_count


class MetricsCollector:
    """Lightweight in-process metrics collector."""

    def __init__(self) -> None:
        self._endpoints: dict[str, EndpointMetrics] = {}
        self._lock = threading.Lock()

    def _key(self, method: str, path: str) -> str:
        return f"{method.upper()}:{path}"

    def record_request(
        self, method: str, path: str, latency_ms: float, status_code: int
    ) -> None:
        key = self._key(method, path)
        with self._lock:
            if key not in self._endpoints:
                self._endpoints[key] = EndpointMetrics(method=method, path=path)
            self._endpoints[key].record(latency_ms, status_code)

    def get_endpoint_metrics(self, method: str, path: str) -> EndpointMetrics | None:
        return self._endpoints.get(self._key(method, path))

    def get_all(self) -> list[EndpointMetrics]:
        with self._lock:
            return list(self._endpoints.values())

    def summary(self) -> dict[str, Any]:
        total_requests = 0
        total_errors = 0
        for m in self._endpoints.values():
            total_requests += m.request_count
            total_errors += m.error_count
        return {
            "total_requests": total_requests,
            "total_errors": total_errors,
            "error_rate": total_errors / total_requests if total_requests else 0.0,
            "endpoints": len(self._endpoints),
        }


# ---------------------------------------------------------------------------
# Alerter
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class AlertRule:
    name: str
    condition: str  # 'error_rate_gt', 'p99_latency_gt'
    threshold: float
    window_seconds: int
    severity: str  # 'warning', 'critical'
    path: str | None = None


@dataclass
class Alert:
    rule_name: str
    severity: str
    message: str
    triggered_at: datetime
    silenced_until: datetime | None = None

    @property
    def is_silenced(self) -> bool:
        if self.silenced_until is None:
            return False
        return datetime.now(UTC) < self.silenced_until


_DEFAULT_RULES: list[AlertRule] = [
    AlertRule("high_error_rate_warning", "error_rate_gt", 0.05, 300, "warning"),
    AlertRule("high_error_rate_critical", "error_rate_gt", 0.10, 120, "critical"),
    AlertRule("high_p99_latency_warning", "p99_latency_gt", 1000.0, 600, "warning"),
]


class Alerter:
    """Evaluates alert rules against current metrics."""

    def __init__(
        self,
        metrics: MetricsCollector,
        rules: list[AlertRule] | None = None,
    ) -> None:
        self._metrics = metrics
        self._rules = rules if rules is not None else _DEFAULT_RULES
        self._active_alerts: dict[str, Alert] = {}

    def evaluate(self) -> list[Alert]:
        fired: list[Alert] = []
        for rule in self._rules:
            triggered = False
            message = ""

            if rule.condition == "error_rate_gt":
                summary = self._metrics.summary()
                rate = summary["error_rate"]
                if rate > rule.threshold:
                    triggered = True
                    message = (
                        f"Error rate {rate:.1%} exceeds threshold {rule.threshold:.1%}"
                    )

            elif rule.condition == "p99_latency_gt":
                for m in self._metrics.get_all():
                    p99 = m.percentile(99)
                    if p99 is not None and p99 > rule.threshold:
                        triggered = True
                        message = (
                            f"P99 latency {p99:.0f}ms on {m.method}:{m.path} "
                            f"exceeds {rule.threshold:.0f}ms"
                        )
                        break

            if triggered:
                alert = Alert(
                    rule_name=rule.name,
                    severity=rule.severity,
                    message=message,
                    triggered_at=datetime.now(UTC),
                )
                if rule.name not in self._active_alerts or (
                    not self._active_alerts[rule.name].is_silenced
                ):
                    self._active_alerts[rule.name] = alert
                    fired.append(alert)

        return fired

    def silence(self, rule_name: str, duration_seconds: int) -> None:
        from datetime import timedelta

        if rule_name in self._active_alerts:
            alert = self._active_alerts[rule_name]
            self._active_alerts[rule_name] = Alert(
                rule_name=alert.rule_name,
                severity=alert.severity,
                message=alert.message,
                triggered_at=alert.triggered_at,
                silenced_until=datetime.now(UTC) + timedelta(seconds=duration_seconds),
            )

    def get_active_alerts(self) -> list[Alert]:
        return [a for a in self._active_alerts.values() if not a.is_silenced]


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------
_error_tracker = ErrorTracker()
_metrics_collector = MetricsCollector()
_alerter = Alerter(_metrics_collector)


def get_error_tracker() -> ErrorTracker:
    return _error_tracker


def get_metrics_collector() -> MetricsCollector:
    return _metrics_collector


def get_alerter() -> Alerter:
    return _alerter
