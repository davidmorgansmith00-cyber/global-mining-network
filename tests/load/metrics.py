"""
Load test metrics collection module.

Collects per-endpoint response time statistics (min, max, mean, p50, p95, p99),
request counts, error breakdowns, and aggregate throughput.
"""
from __future__ import annotations

import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any


@dataclass
class EndpointStats:
    endpoint: str
    total: int = 0
    passed: int = 0
    failed: int = 0
    errors_4xx: int = 0
    errors_5xx: int = 0
    timeouts: int = 0
    _samples: list[float] = field(default_factory=list)

    def record(self, latency_ms: float, status_code: int, timed_out: bool = False) -> None:
        self.total += 1
        self._samples.append(latency_ms)
        if timed_out:
            self.timeouts += 1
            self.failed += 1
        elif status_code < 400:
            self.passed += 1
        elif status_code < 500:
            self.errors_4xx += 1
            self.failed += 1
        else:
            self.errors_5xx += 1
            self.failed += 1

    def percentile(self, p: float) -> float:
        if not self._samples:
            return 0.0
        s = sorted(self._samples)
        idx = int(len(s) * p / 100)
        return s[min(idx, len(s) - 1)]

    @property
    def mean(self) -> float:
        return sum(self._samples) / len(self._samples) if self._samples else 0.0

    @property
    def min_latency(self) -> float:
        return min(self._samples) if self._samples else 0.0

    @property
    def max_latency(self) -> float:
        return max(self._samples) if self._samples else 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "endpoint": self.endpoint,
            "total": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "errors_4xx": self.errors_4xx,
            "errors_5xx": self.errors_5xx,
            "timeouts": self.timeouts,
            "latency_min_ms": round(self.min_latency, 2),
            "latency_max_ms": round(self.max_latency, 2),
            "latency_mean_ms": round(self.mean, 2),
            "latency_p50_ms": round(self.percentile(50), 2),
            "latency_p95_ms": round(self.percentile(95), 2),
            "latency_p99_ms": round(self.percentile(99), 2),
        }


class MetricsAggregator:
    """Aggregates load test metrics across all endpoints."""

    def __init__(self) -> None:
        self._endpoints: dict[str, EndpointStats] = {}
        self._start_time: float = time.monotonic()
        self._end_time: float | None = None

    def record(
        self,
        endpoint: str,
        latency_ms: float,
        status_code: int,
        timed_out: bool = False,
    ) -> None:
        if endpoint not in self._endpoints:
            self._endpoints[endpoint] = EndpointStats(endpoint=endpoint)
        self._endpoints[endpoint].record(latency_ms, status_code, timed_out)

    def finish(self) -> None:
        self._end_time = time.monotonic()

    @property
    def elapsed_seconds(self) -> float:
        end = self._end_time if self._end_time else time.monotonic()
        return end - self._start_time

    @property
    def total_requests(self) -> int:
        return sum(s.total for s in self._endpoints.values())

    @property
    def total_errors(self) -> int:
        return sum(s.failed for s in self._endpoints.values())

    @property
    def error_rate(self) -> float:
        t = self.total_requests
        return self.total_errors / t if t else 0.0

    @property
    def throughput_rps(self) -> float:
        elapsed = self.elapsed_seconds
        return self.total_requests / elapsed if elapsed > 0 else 0.0

    def summary(self) -> dict[str, Any]:
        return {
            "elapsed_seconds": round(self.elapsed_seconds, 2),
            "total_requests": self.total_requests,
            "total_errors": self.total_errors,
            "error_rate": round(self.error_rate, 4),
            "throughput_rps": round(self.throughput_rps, 2),
            "endpoints": [s.to_dict() for s in self._endpoints.values()],
        }

    def meets_sla(self, max_p99_ms: float = 1000.0, max_error_rate: float = 0.01) -> bool:
        """Return True if all SLA thresholds are met."""
        if self.error_rate > max_error_rate:
            return False
        for stats in self._endpoints.values():
            if stats.percentile(99) > max_p99_ms:
                return False
        return True
