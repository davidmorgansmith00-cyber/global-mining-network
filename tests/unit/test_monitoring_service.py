from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SERVER_ROOT = ROOT / "server"
for p in (str(ROOT), str(SERVER_ROOT)):
    if p not in sys.path:
        sys.path.insert(0, p)

from domain.monitoring.service import (
    Alerter,
    AlertRule,
    ErrorTracker,
    MetricsCollector,
)


class ErrorTrackerTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tracker = ErrorTracker()

    def test_capture_returns_fingerprint(self) -> None:
        fp = self.tracker.capture(ValueError("oops"))
        self.assertIsInstance(fp, str)
        self.assertEqual(len(fp), 16)

    def test_same_exception_deduplicates(self) -> None:
        exc = ValueError("duplicate error")
        fp1 = self.tracker.capture(exc)
        fp2 = self.tracker.capture(exc)
        self.assertEqual(fp1, fp2)
        record = self.tracker.get(fp1)
        self.assertIsNotNone(record)
        self.assertEqual(record.count, 2)  # type: ignore[union-attr]

    def test_different_exceptions_get_different_fingerprints(self) -> None:
        fp1 = self.tracker.capture(ValueError("error A"))
        fp2 = self.tracker.capture(RuntimeError("error B"))
        self.assertNotEqual(fp1, fp2)

    def test_affected_users_tracked(self) -> None:
        exc = ValueError("user-specific error")
        self.tracker.capture(exc, user_id="user-1")
        self.tracker.capture(exc, user_id="user-2")
        fp = self.tracker.capture(exc, user_id="user-1")
        record = self.tracker.get(fp)
        self.assertEqual(len(record.affected_users), 2)  # type: ignore[union-attr]

    def test_get_all_returns_all_records(self) -> None:
        self.tracker.capture(ValueError("a"))
        self.tracker.capture(RuntimeError("b"))
        records = self.tracker.get_all()
        self.assertEqual(len(records), 2)


class MetricsCollectorTests(unittest.TestCase):
    def setUp(self) -> None:
        self.collector = MetricsCollector()

    def test_record_and_retrieve(self) -> None:
        self.collector.record_request("GET", "/test", 50.0, 200)
        m = self.collector.get_endpoint_metrics("GET", "/test")
        self.assertIsNotNone(m)
        self.assertEqual(m.request_count, 1)  # type: ignore[union-attr]
        self.assertEqual(m.error_count, 0)

    def test_error_counted_for_4xx(self) -> None:
        self.collector.record_request("POST", "/bad", 10.0, 400)
        m = self.collector.get_endpoint_metrics("POST", "/bad")
        self.assertEqual(m.error_count, 1)  # type: ignore[union-attr]
        self.assertAlmostEqual(m.error_rate, 1.0)  # type: ignore[union-attr]

    def test_summary_counts_totals(self) -> None:
        self.collector.record_request("GET", "/a", 10.0, 200)
        self.collector.record_request("GET", "/a", 20.0, 500)
        summary = self.collector.summary()
        self.assertEqual(summary["total_requests"], 2)
        self.assertEqual(summary["total_errors"], 1)

    def test_percentile_calculations(self) -> None:
        for i in range(100):
            self.collector.record_request("GET", "/latency", float(i), 200)
        m = self.collector.get_endpoint_metrics("GET", "/latency")
        p50 = m.percentile(50)  # type: ignore[union-attr]
        p99 = m.percentile(99)  # type: ignore[union-attr]
        self.assertGreater(p99, p50)


class AlerterTests(unittest.TestCase):
    def _make_alerter(self) -> tuple[MetricsCollector, Alerter]:
        collector = MetricsCollector()
        rules = [
            AlertRule("high_errors", "error_rate_gt", 0.05, 300, "warning"),
            AlertRule("high_latency", "p99_latency_gt", 100.0, 60, "critical"),
        ]
        alerter = Alerter(collector, rules)
        return collector, alerter

    def test_no_alerts_when_below_threshold(self) -> None:
        collector, alerter = self._make_alerter()
        collector.record_request("GET", "/ok", 10.0, 200)
        fired = alerter.evaluate()
        self.assertEqual(fired, [])

    def test_error_rate_alert_fires(self) -> None:
        collector, alerter = self._make_alerter()
        for _ in range(10):
            collector.record_request("GET", "/bad", 10.0, 500)
        fired = alerter.evaluate()
        names = [a.rule_name for a in fired]
        self.assertIn("high_errors", names)

    def test_p99_latency_alert_fires(self) -> None:
        collector, alerter = self._make_alerter()
        for _ in range(100):
            collector.record_request("GET", "/slow", 200.0, 200)
        fired = alerter.evaluate()
        names = [a.rule_name for a in fired]
        self.assertIn("high_latency", names)

    def test_silence_suppresses_alert(self) -> None:
        collector, alerter = self._make_alerter()
        for _ in range(10):
            collector.record_request("GET", "/bad", 10.0, 500)
        alerter.evaluate()
        alerter.silence("high_errors", 3600)
        active = alerter.get_active_alerts()
        self.assertFalse(any(a.rule_name == "high_errors" for a in active))


if __name__ == "__main__":
    unittest.main(verbosity=2)
