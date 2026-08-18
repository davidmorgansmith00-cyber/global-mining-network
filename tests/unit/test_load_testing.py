from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (str(ROOT), str(ROOT / "tests")):
    if p not in sys.path:
        sys.path.insert(0, p)

from tests.load.metrics import EndpointStats, MetricsAggregator
from tests.load.report_generator import generate_html_report


class EndpointStatsTests(unittest.TestCase):
    def test_passed_incremented_for_2xx(self) -> None:
        stats = EndpointStats(endpoint="GET:/test")
        stats.record(50.0, 200)
        self.assertEqual(stats.passed, 1)
        self.assertEqual(stats.failed, 0)

    def test_4xx_increments_failed_and_error_4xx(self) -> None:
        stats = EndpointStats(endpoint="GET:/test")
        stats.record(10.0, 404)
        self.assertEqual(stats.failed, 1)
        self.assertEqual(stats.errors_4xx, 1)

    def test_5xx_increments_failed_and_error_5xx(self) -> None:
        stats = EndpointStats(endpoint="GET:/test")
        stats.record(10.0, 503)
        self.assertEqual(stats.failed, 1)
        self.assertEqual(stats.errors_5xx, 1)

    def test_timeout_increments_timeout_and_failed(self) -> None:
        stats = EndpointStats(endpoint="GET:/test")
        stats.record(5000.0, 0, timed_out=True)
        self.assertEqual(stats.timeouts, 1)
        self.assertEqual(stats.failed, 1)

    def test_percentile_ordering(self) -> None:
        stats = EndpointStats(endpoint="GET:/latency")
        for i in range(1, 101):
            stats.record(float(i), 200)
        p50 = stats.percentile(50)
        p95 = stats.percentile(95)
        p99 = stats.percentile(99)
        self.assertLessEqual(p50, p95)
        self.assertLessEqual(p95, p99)

    def test_to_dict_contains_required_keys(self) -> None:
        stats = EndpointStats(endpoint="POST:/login")
        stats.record(30.0, 200)
        d = stats.to_dict()
        for key in ("endpoint", "total", "passed", "failed", "latency_p50_ms", "latency_p99_ms"):
            self.assertIn(key, d)


class MetricsAggregatorTests(unittest.TestCase):
    def test_aggregate_throughput_calculation(self) -> None:
        agg = MetricsAggregator()
        for _ in range(100):
            agg.record("GET:/api", 10.0, 200)
        agg.finish()
        summary = agg.summary()
        self.assertEqual(summary["total_requests"], 100)
        self.assertEqual(summary["total_errors"], 0)
        self.assertGreater(summary["throughput_rps"], 0)

    def test_error_rate_calculation(self) -> None:
        agg = MetricsAggregator()
        for _ in range(90):
            agg.record("GET:/ok", 10.0, 200)
        for _ in range(10):
            agg.record("GET:/fail", 10.0, 500)
        agg.finish()
        self.assertAlmostEqual(agg.error_rate, 0.10, places=2)

    def test_sla_pass_when_within_thresholds(self) -> None:
        agg = MetricsAggregator()
        for _ in range(100):
            agg.record("GET:/fast", 50.0, 200)
        agg.finish()
        self.assertTrue(agg.meets_sla())

    def test_sla_fail_when_error_rate_exceeded(self) -> None:
        agg = MetricsAggregator()
        for _ in range(90):
            agg.record("GET:/ok", 10.0, 200)
        for _ in range(10):
            agg.record("GET:/fail", 10.0, 500)
        agg.finish()
        self.assertFalse(agg.meets_sla(max_error_rate=0.01))

    def test_sla_fail_when_p99_exceeded(self) -> None:
        agg = MetricsAggregator()
        for _ in range(99):
            agg.record("GET:/slow", 10.0, 200)
        agg.record("GET:/slow", 2000.0, 200)  # worst outlier
        agg.finish()
        self.assertFalse(agg.meets_sla(max_p99_ms=1000.0))


class ReportGeneratorTests(unittest.TestCase):
    def test_report_generates_valid_html(self) -> None:
        import tempfile
        import os

        summary = {
            "elapsed_seconds": 60.0,
            "total_requests": 1000,
            "total_errors": 5,
            "error_rate": 0.005,
            "throughput_rps": 16.7,
            "endpoints": [
                {
                    "endpoint": "GET:/api/v1/blockchain/status",
                    "total": 1000,
                    "passed": 995,
                    "failed": 5,
                    "errors_4xx": 0,
                    "errors_5xx": 5,
                    "timeouts": 0,
                    "latency_min_ms": 5.0,
                    "latency_max_ms": 800.0,
                    "latency_mean_ms": 50.0,
                    "latency_p50_ms": 45.0,
                    "latency_p95_ms": 250.0,
                    "latency_p99_ms": 700.0,
                }
            ],
        }

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as f:
            path = f.name
        try:
            generate_html_report(summary, path)
            content = Path(path).read_text()
            self.assertIn("<!DOCTYPE html>", content)
            self.assertIn("GMN Load Test Report", content)
            self.assertIn("GET:/api/v1/blockchain/status", content)
        finally:
            os.unlink(path)


if __name__ == "__main__":
    unittest.main(verbosity=2)
