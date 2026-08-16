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
                "--strict-rejection-max-delta",
                "0",
                "--mismatch-rate-max-per-minute",
                "0.1",
                "--output",
                str(bundle_path),
            )
            self.assertEqual(build_result.returncode, 0, msg=build_result.stderr)
            self.assertTrue(bundle_path.exists())

            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            self.assertEqual(bundle["inputs_count"], 2)
            self.assertTrue(bundle["threshold_checks"]["query_share_window_pass"])
            self.assertTrue(bundle["threshold_checks"]["strict_rejection_window_pass"])
            self.assertTrue(bundle["threshold_checks"]["mismatch_rate_window_pass"])
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
            self.assertEqual(
                memo["threshold_evaluation"]["strict_rejection_stability"]["auto_result"],
                "pass_candidate",
            )
            self.assertEqual(
                memo["threshold_evaluation"]["mismatch_stability"]["auto_result"],
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

    def test_markdown_renderer_outputs_decision_memo_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            draft_path = temp_root / "decision-memo-draft.json"
            markdown_path = temp_root / "decision-memo.md"

            draft_payload = {
                "decision_summary": {
                    "decision_date": "2026-08-30",
                    "environment_scope": "pre-prod canary",
                    "proposed_action": "promote strict mode",
                    "decision_owner": "backend-owner",
                },
                "evidence_inputs": {
                    "rollout_bundle_file": "artifacts/intent-transport-rollout-bundle.json",
                    "strict_mode_sunset_test_log": "logs/sunset.log",
                    "error_rate_comparison_report": "reports/error-rates.json",
                    "client_compatibility_signoff_record": "docs/client-signoff.md",
                },
                "threshold_evaluation": {
                    "query_share_threshold": {
                        "overall_query_share_percent": 0.81,
                        "days_below_threshold": 14,
                        "query_share_window_pass": True,
                        "auto_result": "pass_candidate",
                    },
                    "strict_rejection_stability": {
                        "total_query_rejected_strict_delta": 0,
                        "strict_mode_window_periods_reviewed": "window-a",
                        "auto_result": "pass_candidate",
                    },
                    "mismatch_stability": {
                        "max_mismatch_rate_per_minute": 0.02,
                        "baseline_mismatch_rate_per_minute": 0.01,
                        "sustained_duration_observed": "15m",
                        "auto_result": "pass_candidate",
                    },
                    "error_rate_safety": {
                        "baseline_400_401_rates": "{}",
                        "canary_400_401_rates": "{}",
                        "auto_result": "review_required",
                    },
                    "client_regression_gate": {
                        "open_p1_count": 0,
                        "open_p2_count": 0,
                        "auto_result": "pass_candidate",
                    },
                },
                "rollback_trigger_review": {
                    "header_401_rate_exceeded_2x_for_30m": False,
                    "mismatch_threshold_exceeded_for_30m": False,
                    "critical_compatibility_cohort_blocked": False,
                    "incident_ids_and_remediation": "",
                },
                "final_recommendation": {
                    "recommended_action": "go",
                    "rationale_summary": "all threshold checks pass",
                    "required_followups_before_production": "none",
                },
                "approvals": {
                    "backend_owner": "pending",
                    "client_owner": "pending",
                    "qa_owner": "pending",
                    "operations_owner": "pending",
                    "final_approver": "pending",
                },
            }
            draft_path.write_text(json.dumps(draft_payload), encoding="utf-8")

            render_result = self._run(
                "tools/render_operation_intent_decision_memo.py",
                "--input",
                str(draft_path),
                "--output",
                str(markdown_path),
            )
            self.assertEqual(render_result.returncode, 0, msg=render_result.stderr)
            self.assertTrue(markdown_path.exists())

            markdown = markdown_path.read_text(encoding="utf-8")
            self.assertIn("# Operation Intent Production Rollout Decision Memo", markdown)
            self.assertIn("## Threshold Evaluation", markdown)
            self.assertIn("- query_share_window_pass: True", markdown)
            self.assertIn("- auto_result: pass_candidate", markdown)
            self.assertIn("- recommended_action: go", markdown)


if __name__ == "__main__":
    unittest.main(verbosity=2)
