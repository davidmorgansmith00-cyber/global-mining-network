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

            evaluation_path = temp_root / "rollout-evaluation.json"
            eval_result = self._run(
                "tools/evaluate_operation_intent_rollout_gate.py",
                "--bundle",
                str(bundle_path),
                "--output",
                str(evaluation_path),
            )
            self.assertEqual(eval_result.returncode, 0, msg=eval_result.stderr)

            memo_path = temp_root / "decision-memo-draft.json"
            prefill_result = self._run(
                "tools/prefill_operation_intent_decision_memo.py",
                "--bundle",
                str(bundle_path),
                "--evaluation",
                str(evaluation_path),
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
            self.assertEqual(memo["rollout_gate_evaluation"]["decision"], "promote_candidate")
            self.assertTrue(memo["rollout_gate_evaluation"]["promotion_ready"])

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
                "--environment-scope",
                "pre-prod-canary",
                "--decision-owner",
                "backend-oncall",
            )
            self.assertEqual(dry_run_result.returncode, 0, msg=dry_run_result.stderr)

            summary = json.loads(dry_run_result.stdout)
            self.assertEqual(summary["generated_daily_files"], 3)
            self.assertIn("bundle_file", summary)
            self.assertIn("memo_draft_file", summary)
            self.assertIn("memo_markdown_file", summary)
            self.assertIn("rollout_evaluation_file", summary)

            self.assertTrue((output_dir / "intent-transport-day01.json").exists())
            self.assertTrue((output_dir / "intent-transport-day02.json").exists())
            self.assertTrue((output_dir / "intent-transport-day03.json").exists())
            self.assertTrue((output_dir / "intent-transport-rollout-bundle.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo-draft.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo.md").exists())
            self.assertTrue((output_dir / "intent-transport-rollout-evaluation.json").exists())

            memo_draft = json.loads(
                (output_dir / "intent-transport-decision-memo-draft.json").read_text(encoding="utf-8")
            )
            self.assertEqual(memo_draft["decision_summary"]["environment_scope"], "pre-prod-canary")
            self.assertEqual(memo_draft["decision_summary"]["decision_owner"], "backend-oncall")
            self.assertIn("rollout_gate_evaluation", memo_draft)

            evaluation = json.loads(
                (output_dir / "intent-transport-rollout-evaluation.json").read_text(encoding="utf-8")
            )
            self.assertFalse(evaluation["promotion_ready"])
            self.assertEqual(evaluation["decision"], "hold_candidate")

            memo_markdown = (output_dir / "intent-transport-decision-memo.md").read_text(encoding="utf-8")
            self.assertIn("## Rollout Gate Evaluation", memo_markdown)

    def test_markdown_renderer_outputs_decision_memo_sections(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            draft_path = temp_root / "decision-memo-draft.json"
            evaluation_path = temp_root / "rollout-evaluation.json"
            markdown_embedded_path = temp_root / "decision-memo-embedded.md"
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
            evaluation_path.write_text(
                json.dumps(
                    {
                        "promotion_ready": False,
                        "decision": "hold_candidate",
                        "failed_checks": ["query_share_window_pass"],
                    }
                ),
                encoding="utf-8",
            )

            render_result = self._run(
                "tools/render_operation_intent_decision_memo.py",
                "--input",
                str(draft_path),
                "--evaluation",
                str(evaluation_path),
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
            self.assertIn("## Rollout Gate Evaluation", markdown)
            self.assertIn("- decision: hold_candidate", markdown)

            draft_payload["rollout_gate_evaluation"] = {
                "promotion_ready": False,
                "decision": "hold_candidate",
                "failed_checks": ["query_share_window_pass"],
            }
            draft_path.write_text(json.dumps(draft_payload), encoding="utf-8")

            render_embedded_result = self._run(
                "tools/render_operation_intent_decision_memo.py",
                "--input",
                str(draft_path),
                "--output",
                str(markdown_embedded_path),
            )
            self.assertEqual(render_embedded_result.returncode, 0, msg=render_embedded_result.stderr)
            markdown_embedded = markdown_embedded_path.read_text(encoding="utf-8")
            self.assertIn("## Rollout Gate Evaluation", markdown_embedded)
            self.assertIn("- decision: hold_candidate", markdown_embedded)

    def test_threshold_failures_propagate_to_prefill_auto_results(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            captures_dir = temp_root / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

            self._write_capture_file(
                captures_dir / "intent-transport-day01.json",
                finished_at="2026-08-16T00:00:00+00:00",
                query_delta=10,
                header_delta=0,
                dual_match_delta=0,
                mismatch_delta=2,
                query_rejected_strict_delta=2,
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
                "0.01",
                "--output",
                str(bundle_path),
            )
            self.assertEqual(build_result.returncode, 0, msg=build_result.stderr)

            bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
            self.assertFalse(bundle["threshold_checks"]["query_share_window_pass"])
            self.assertFalse(bundle["threshold_checks"]["strict_rejection_window_pass"])
            self.assertFalse(bundle["threshold_checks"]["mismatch_rate_window_pass"])

            memo_path = temp_root / "decision-memo-draft.json"
            prefill_result = self._run(
                "tools/prefill_operation_intent_decision_memo.py",
                "--bundle",
                str(bundle_path),
                "--output",
                str(memo_path),
            )
            self.assertEqual(prefill_result.returncode, 0, msg=prefill_result.stderr)

            memo = json.loads(memo_path.read_text(encoding="utf-8"))
            self.assertEqual(
                memo["threshold_evaluation"]["query_share_threshold"]["auto_result"],
                "fail_candidate",
            )
            self.assertEqual(
                memo["threshold_evaluation"]["strict_rejection_stability"]["auto_result"],
                "fail_candidate",
            )
            self.assertEqual(
                memo["threshold_evaluation"]["mismatch_stability"]["auto_result"],
                "fail_candidate",
            )

    def test_rollout_gate_evaluator_reports_hold_and_can_fail_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            bundle_path = temp_root / "rollout-bundle.json"

            bundle_payload = {
                "threshold_checks": {
                    "query_share_window_pass": True,
                    "query_share_window_rule": "query share condition",
                    "strict_rejection_window_pass": False,
                    "strict_rejection_window_rule": "strict rejection condition",
                    "mismatch_rate_window_pass": True,
                    "mismatch_rate_window_rule": "mismatch condition",
                }
            }
            bundle_path.write_text(json.dumps(bundle_payload), encoding="utf-8")

            eval_result = self._run(
                "tools/evaluate_operation_intent_rollout_gate.py",
                "--bundle",
                str(bundle_path),
            )
            self.assertEqual(eval_result.returncode, 0, msg=eval_result.stderr)

            evaluation = json.loads(eval_result.stdout)
            self.assertFalse(evaluation["promotion_ready"])
            self.assertEqual(evaluation["decision"], "hold_candidate")
            self.assertEqual(evaluation["passed_checks"], 2)
            self.assertEqual(evaluation["total_checks"], 3)
            self.assertEqual(evaluation["failed_checks"], ["strict_rejection_window_pass"])

            fail_result = self._run(
                "tools/evaluate_operation_intent_rollout_gate.py",
                "--bundle",
                str(bundle_path),
                "--fail-on-blocked",
            )
            self.assertEqual(fail_result.returncode, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
