from __future__ import annotations

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


class OperationIntentRolloutToolingTests(unittest.TestCase):
    def _run(self, *args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            capture_output=True,
            check=False,
        )

    def _write_capture_file(
        self,
        path: Path,
        *,
        finished_at: str,
        query_delta: int,
        header_delta: int,
        dual_match_delta: int,
        mismatch_delta: int,
        query_rejected_strict_delta: int,
    ) -> None:
        total = query_delta + header_delta + dual_match_delta
        ratio = (query_delta / total) if total > 0 else 0.0
        payload = {
            "started_at": "2026-08-16T00:00:00+00:00",
            "finished_at": finished_at,
            "elapsed_seconds": 900.0,
            "base_url": "http://127.0.0.1:8000",
            "token_header": "X-Maintenance-Token",
            "samples": 15,
            "interval_seconds": 60.0,
            "snapshots": [],
            "summary": {
                "query": {"first": 10, "last": 10 + query_delta, "delta": query_delta, "rate_per_minute": 0.1},
                "header": {
                    "first": 100,
                    "last": 100 + header_delta,
                    "delta": header_delta,
                    "rate_per_minute": 1.0,
                },
                "dual_match": {
                    "first": 5,
                    "last": 5 + dual_match_delta,
                    "delta": dual_match_delta,
                    "rate_per_minute": 0.1,
                },
                "mismatch": {
                    "first": 1,
                    "last": 1 + mismatch_delta,
                    "delta": mismatch_delta,
                    "rate_per_minute": 0.05,
                },
                "query_rejected_strict": {
                    "first": 0,
                    "last": query_rejected_strict_delta,
                    "delta": query_rejected_strict_delta,
                    "rate_per_minute": 0.0,
                },
            },
            "query_share_from_deltas": {
                "query_delta": query_delta,
                "header_delta": header_delta,
                "dual_match_delta": dual_match_delta,
                "total_transport_delta": total,
                "query_share_ratio": round(ratio, 6),
                "query_share_percent": round(ratio * 100.0, 4),
            },
        }
        path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def test_bundle_builder_and_prefill_helper_pipeline(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            captures_dir = temp_root / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

            self._write_capture_file(
                captures_dir / "intent-transport-day01.json",
                finished_at="2026-08-16T00:00:00+00:00",
                query_delta=1,
                header_delta=200,
                dual_match_delta=4,
                mismatch_delta=0,
                query_rejected_strict_delta=0,
            )
            self._write_capture_file(
                captures_dir / "intent-transport-day02.json",
                finished_at="2026-08-17T00:00:00+00:00",
                query_delta=1,
                header_delta=220,
                dual_match_delta=5,
                mismatch_delta=1,
                query_rejected_strict_delta=0,
            )

            bundle_path = temp_root / "rollout-bundle.json"
            build_result = self._run(
                "tools/build_operation_intent_rollout_bundle.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--query-threshold-percent",
                "1.0",
                "--output",
                str(bundle_path),
            )
            self.assertEqual(build_result.returncode, 0, msg=build_result.stderr)
            self.assertTrue(bundle_path.exists())

            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(bundle["inputs_count"], 2)
            self.assertTrue(bundle["threshold_checks"]["query_share_window_pass"])
            self.assertIn("aggregate", bundle)

            memo_path = temp_root / "decision-memo-draft.json"
            prefill_result = self._run(
                "tools/prefill_operation_intent_decision_memo.py",
                "--bundle",
                str(bundle_path),
                "--environment-scope",
                "pre-prod-canary",
                "--decision-owner",
                "backend-oncall",
                "--output",
                str(memo_path),
            )
            self.assertEqual(prefill_result.returncode, 0, msg=prefill_result.stderr)
            self.assertTrue(memo_path.exists())

            memo = json.loads(memo_path.read_text(encoding="utf-8"))
            self.assertEqual(memo["decision_summary"]["environment_scope"], "pre-prod-canary")
            self.assertEqual(memo["decision_summary"]["decision_owner"], "backend-oncall")
            self.assertEqual(
                memo["threshold_evaluation"]["query_share_threshold"]["auto_result"],
                "pass_candidate",
            )

    def test_end_to_end_dry_run_helper_generates_expected_files(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp) / "dry-run"
            dry_run_result = self._run(
                "tools/run_operation_intent_rollout_dry_run.py",
                "--output-dir",
                str(output_dir),
                "--days",
                "3",
                "--query-threshold-percent",
                "1.0",
            )
            self.assertEqual(dry_run_result.returncode, 0, msg=dry_run_result.stderr)

            self.assertTrue((output_dir / "intent-transport-day01.json").exists())
            self.assertTrue((output_dir / "intent-transport-day02.json").exists())
            self.assertTrue((output_dir / "intent-transport-day03.json").exists())
            self.assertTrue((output_dir / "intent-transport-rollout-bundle.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo-draft.json").exists())


if __name__ == "__main__":
    unittest.main(verbosity=2)
