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
            self.assertIn("decision_package_manifest_file", summary)
            self.assertIn("decision_package_verification_file", summary)
            self.assertIn("decision_package_compact_summary_file", summary)
            self.assertIn("decision_package_compact_summary_json_file", summary)
            self.assertIn("decision_package_inspector_summary_file", summary)
            self.assertIn("decision_package_inspector_summary_json_file", summary)
            self.assertIn("decision_package_decision", summary)
            self.assertIn("decision_package_promotion_ready", summary)
            self.assertIn("decision_package_passed_checks", summary)
            self.assertIn("decision_package_total_checks", summary)
            self.assertIn("decision_package_failed_checks", summary)
            self.assertIn("decision_package_checks", summary)
            self.assertIn("decision_package_verified", summary)
            self.assertIn("decision_package_schema_supported", summary)
            self.assertIn("decision_package_evaluation_matches_memo", summary)
            self.assertIn("decision_package_decision", summary)
            self.assertIn("decision_package_promotion_ready", summary)
            self.assertIn("decision_package_passed_checks", summary)
            self.assertIn("decision_package_total_checks", summary)
            self.assertIn("decision_package_failed_checks", summary)
            self.assertIn("decision_package_verification_missing_artifacts", summary)
            self.assertIn("decision_package_verification_mismatch_details", summary)
            self.assertIn("decision_package_compact_summary_text_matches", summary)
            self.assertIn("decision_package_compact_summary_json_matches", summary)
            self.assertIn("decision_package_compact_summary_checks_performed", summary)
            self.assertIn("decision_package_compact_summary_checks_skipped", summary)
            self.assertIn("decision_package_compact_summary_artifacts_present", summary)
            self.assertIn("decision_package_compact_summary_mismatch_count", summary)
            self.assertIn("decision_package_compact_summary_mismatch_details", summary)
            self.assertIn("decision_package_inspector_summary_artifacts_present", summary)
            self.assertIn("decision_package_inspector_summary_checks_performed", summary)
            self.assertIn("decision_package_inspector_summary_checks_skipped", summary)
            self.assertIn("decision_package_inspector_summary_text_matches", summary)
            self.assertIn("decision_package_inspector_summary_json_matches", summary)
            self.assertIn("decision_package_inspector_summary_mismatch_count", summary)
            self.assertIn("decision_package_inspector_summary_mismatch_details", summary)
            self.assertIn("decision_package_inspector_verified", summary)
            self.assertIn("decision_package_inspector_mismatch_count", summary)
            self.assertIn("decision_package_inspector_mismatch_details", summary)
            self.assertTrue(summary["decision_package_compact_summary_artifacts_present"])
            self.assertTrue(summary["decision_package_compact_summary_checks_performed"])
            self.assertFalse(summary["decision_package_compact_summary_checks_skipped"])
            self.assertEqual(summary["decision_package_compact_summary_mismatch_count"], 0)
            self.assertEqual(summary["decision_package_compact_summary_mismatch_details"], [])
            self.assertTrue(summary["decision_package_verified"])
            self.assertTrue(summary["decision_package_schema_supported"])
            self.assertEqual(summary["decision_package_decision"], "hold_candidate")
            self.assertFalse(summary["decision_package_promotion_ready"])
            self.assertEqual(summary["decision_package_passed_checks"], 2)
            self.assertEqual(summary["decision_package_total_checks"], 3)
            self.assertEqual(summary["decision_package_failed_checks"], ["query_share_window_pass"])
            self.assertIsInstance(summary["decision_package_checks"], list)
            self.assertEqual(len(summary["decision_package_checks"]), 3)
            evaluation = json.loads(
                (output_dir / "intent-transport-rollout-evaluation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(summary["decision_package_checks"], evaluation["checks"])
            self.assertTrue(summary["decision_package_inspector_summary_artifacts_present"])
            self.assertTrue(summary["decision_package_inspector_summary_checks_performed"])
            self.assertFalse(summary["decision_package_inspector_summary_checks_skipped"])
            self.assertTrue(summary["decision_package_inspector_summary_text_matches"])
            self.assertTrue(summary["decision_package_inspector_summary_json_matches"])
            self.assertEqual(summary["decision_package_inspector_summary_mismatch_count"], 0)
            self.assertEqual(summary["decision_package_inspector_summary_mismatch_details"], [])
            self.assertTrue(summary["decision_package_evaluation_matches_memo"])
            self.assertEqual(summary["decision_package_verification_missing_artifacts"], [])
            self.assertEqual(summary["decision_package_verification_mismatch_details"], "")
            self.assertTrue(summary["decision_package_compact_summary_text_matches"])
            self.assertTrue(summary["decision_package_compact_summary_json_matches"])
            self.assertTrue(summary["decision_package_inspector_verified"])
            self.assertEqual(summary["decision_package_inspector_mismatch_count"], 0)
            self.assertEqual(summary["decision_package_inspector_mismatch_details"], [])
            self.assertIsInstance(summary["decision_package_failed_checks"], list)
            self.assertGreater(len(summary["decision_package_failed_checks"]), 0)
            self.assertEqual(summary["decision_package_passed_checks"], 2)
            self.assertEqual(summary["decision_package_total_checks"], 3)

            self.assertTrue((output_dir / "intent-transport-day01.json").exists())
            self.assertTrue((output_dir / "intent-transport-day02.json").exists())
            self.assertTrue((output_dir / "intent-transport-day03.json").exists())
            self.assertTrue((output_dir / "intent-transport-rollout-bundle.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo-draft.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo.md").exists())
            self.assertTrue((output_dir / "intent-transport-rollout-evaluation.json").exists())
            self.assertTrue(
                (output_dir / "decision-package" / "intent-transport-decision-package-manifest.json").exists()
            )
            self.assertTrue(
                (output_dir / "decision-package" / "intent-transport-decision-package-verification.json").exists()
            )
            self.assertTrue(
                (output_dir / "decision-package" / "intent-transport-decision-package-summary.txt").exists()
            )
            self.assertTrue(
                (output_dir / "decision-package" / "intent-transport-decision-package-summary.json").exists()
            )
            self.assertTrue(
                (output_dir / "decision-package" / "intent-transport-decision-package-inspector-summary.txt").exists()
            )
            self.assertTrue(
                (output_dir / "decision-package" / "intent-transport-decision-package-inspector-summary.json").exists()
            )

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
            self.assertEqual(summary["decision_package_checks"], evaluation["checks"])

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

    def test_decision_package_builder_generates_full_artifact_set(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            captures_dir = temp_root / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

            self._write_capture_file(
                captures_dir / "intent-transport-day01.json",
                finished_at="2026-08-16T00:00:00+00:00",
                query_delta=1,
                header_delta=120,
                dual_match_delta=4,
                mismatch_delta=0,
                query_rejected_strict_delta=0,
            )
            self._write_capture_file(
                captures_dir / "intent-transport-day02.json",
                finished_at="2026-08-17T00:00:00+00:00",
                query_delta=1,
                header_delta=150,
                dual_match_delta=4,
                mismatch_delta=0,
                query_rejected_strict_delta=0,
            )

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
                "--environment-scope",
                "pre-prod-canary",
                "--decision-owner",
                "backend-oncall",
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            summary = json.loads(package_result.stdout)
            self.assertIn("bundle_file", summary)
            self.assertIn("evaluation_file", summary)
            self.assertIn("memo_draft_file", summary)
            self.assertIn("memo_markdown_file", summary)
            self.assertIn("manifest_file", summary)
            self.assertIn("verification_file", summary)
            self.assertIn("compact_summary_file", summary)
            self.assertIn("compact_summary_json_file", summary)
            self.assertIn("inspector_summary_file", summary)
            self.assertIn("inspector_summary_json_file", summary)
            self.assertTrue(summary["verification_verified"])
            self.assertTrue(summary["verification_schema_supported"])
            self.assertTrue(summary["verification_evaluation_matches_memo"])
            self.assertEqual(summary["verification_decision"], "promote_candidate")
            self.assertTrue(summary["verification_promotion_ready"])
            self.assertEqual(summary["verification_passed_checks"], 3)
            self.assertEqual(summary["verification_total_checks"], 3)
            self.assertEqual(summary["verification_failed_checks"], [])
            self.assertIsInstance(summary["verification_checks"], list)
            self.assertEqual(len(summary["verification_checks"]), 3)
            self.assertEqual(summary["verification_missing_artifacts"], [])
            self.assertEqual(summary["verification_mismatch_details"], "")
            self.assertTrue(summary["verification_compact_summary_text_matches"])
            self.assertTrue(summary["verification_compact_summary_json_matches"])
            self.assertTrue(summary["verification_compact_summary_artifacts_present"])
            self.assertTrue(summary["verification_compact_summary_checks_performed"])
            self.assertFalse(summary["verification_compact_summary_checks_skipped"])
            self.assertEqual(summary["verification_compact_summary_mismatch_count"], 0)
            self.assertEqual(summary["verification_compact_summary_mismatch_details"], [])
            self.assertTrue(summary["verification_inspector_summary_artifacts_present"])
            self.assertTrue(summary["verification_inspector_summary_checks_performed"])
            self.assertFalse(summary["verification_inspector_summary_checks_skipped"])
            self.assertTrue(summary["verification_inspector_summary_text_matches"])
            self.assertTrue(summary["verification_inspector_summary_json_matches"])
            self.assertEqual(summary["verification_inspector_summary_mismatch_count"], 0)
            self.assertEqual(summary["verification_inspector_summary_mismatch_details"], [])
            self.assertTrue(summary["inspector_verified"])
            self.assertEqual(summary["inspector_mismatch_count"], 0)
            self.assertEqual(summary["inspector_mismatch_details"], [])

            self.assertTrue((output_dir / "intent-transport-rollout-bundle.json").exists())
            self.assertTrue((output_dir / "intent-transport-rollout-evaluation.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo-draft.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-memo.md").exists())
            self.assertTrue((output_dir / "intent-transport-decision-package-manifest.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-package-verification.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-package-summary.txt").exists())
            self.assertTrue((output_dir / "intent-transport-decision-package-summary.json").exists())
            self.assertTrue((output_dir / "intent-transport-decision-package-inspector-summary.txt").exists())
            self.assertTrue((output_dir / "intent-transport-decision-package-inspector-summary.json").exists())

            memo_draft = json.loads(
                (output_dir / "intent-transport-decision-memo-draft.json").read_text(encoding="utf-8")
            )
            self.assertEqual(memo_draft["decision_summary"]["environment_scope"], "pre-prod-canary")
            self.assertEqual(memo_draft["decision_summary"]["decision_owner"], "backend-oncall")
            self.assertIn("rollout_gate_evaluation", memo_draft)

            manifest = json.loads(
                (output_dir / "intent-transport-decision-package-manifest.json").read_text(encoding="utf-8")
            )
            self.assertEqual(manifest["manifest_schema_version"], "1.0")
            self.assertEqual(manifest["inputs"]["environment_scope"], "pre-prod-canary")
            self.assertIn("bundle_file", manifest["artifacts"])
            self.assertIn("verification_file", manifest["artifacts"])
            self.assertIn("compact_summary_file", manifest["artifacts"])
            self.assertIn("compact_summary_json_file", manifest["artifacts"])
            self.assertIn("inspector_summary_file", manifest["artifacts"])
            self.assertIn("inspector_summary_json_file", manifest["artifacts"])

            verification = json.loads(
                (output_dir / "intent-transport-decision-package-verification.json").read_text(
                    encoding="utf-8"
                )
            )
            self.assertTrue(verification["verified"])
            self.assertIn("checks", verification)

            evaluation = json.loads(
                (output_dir / "intent-transport-rollout-evaluation.json").read_text(encoding="utf-8")
            )
            self.assertEqual(verification["checks"], evaluation["checks"])
            self.assertEqual(summary["verification_checks"], verification["checks"])

            compact_summary = (output_dir / "intent-transport-decision-package-summary.txt").read_text(
                encoding="utf-8"
            )
            self.assertIn("decision=", compact_summary)

            compact_summary_json = json.loads(
                (output_dir / "intent-transport-decision-package-summary.json").read_text(encoding="utf-8")
            )
            self.assertIn("decision", compact_summary_json)
            self.assertIn("verified", compact_summary_json)
            self.assertIn("schema_supported", compact_summary_json)

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            inspect_text_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(inspect_text_result.returncode, 0, msg=inspect_text_result.stderr)
            self.assertEqual(compact_summary.strip(), inspect_text_result.stdout.strip())

            inspect_json_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--format",
                "json",
            )
            self.assertEqual(inspect_json_result.returncode, 0, msg=inspect_json_result.stderr)
            self.assertEqual(compact_summary_json, json.loads(inspect_json_result.stdout))
            inspect_summary = json.loads(inspect_json_result.stdout)
            self.assertIn("checks", inspect_summary)
            self.assertIsInstance(inspect_summary["checks"], list)
            self.assertEqual(len(inspect_summary["checks"]), 3)

    def test_decision_package_builder_can_fail_on_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            captures_dir = temp_root / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

            self._write_capture_file(
                captures_dir / "intent-transport-day01.json",
                finished_at="2026-08-16T00:00:00+00:00",
                query_delta=20,
                header_delta=0,
                dual_match_delta=0,
                mismatch_delta=1,
                query_rejected_strict_delta=1,
            )

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
                "--fail-on-blocked",
            )
            self.assertEqual(package_result.returncode, 1)

    def test_decision_package_builder_supports_custom_manifest_name(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            temp_root = Path(tmp)
            captures_dir = temp_root / "captures"
            captures_dir.mkdir(parents=True, exist_ok=True)

            self._write_capture_file(
                captures_dir / "intent-transport-day01.json",
                finished_at="2026-08-16T00:00:00+00:00",
                query_delta=1,
                header_delta=160,
                dual_match_delta=4,
                mismatch_delta=0,
                query_rejected_strict_delta=0,
            )

            output_dir = temp_root / "decision-package"
            custom_manifest = "custom-manifest.json"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
                "--manifest-name",
                custom_manifest,
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            summary = json.loads(package_result.stdout)
            self.assertTrue(summary["manifest_file"].endswith("/custom-manifest.json"))
            self.assertTrue((output_dir / custom_manifest).exists())

    def test_decision_package_verifier_reports_valid_package(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--output",
                str(output_dir / "verification-copy.json"),
            )
            self.assertEqual(verify_result.returncode, 0, msg=verify_result.stderr)
            verification = json.loads(verify_result.stdout)
            self.assertTrue(verification["verified"])
            self.assertTrue(verification["schema_supported"])
            self.assertTrue(verification["compact_summary_artifacts_present"])
            self.assertTrue(verification["compact_summary_checks_performed"])
            self.assertFalse(verification["compact_summary_checks_skipped"])
            self.assertTrue(verification["compact_summary_text_matches"])
            self.assertTrue(verification["compact_summary_json_matches"])
            self.assertEqual(verification["compact_summary_mismatch_count"], 0)
            self.assertTrue(verification["inspector_summary_artifacts_present"])
            self.assertTrue(verification["inspector_summary_checks_performed"])
            self.assertFalse(verification["inspector_summary_checks_skipped"])
            self.assertTrue(verification["inspector_summary_text_matches"])
            self.assertTrue(verification["inspector_summary_json_matches"])
            self.assertEqual(verification["inspector_summary_mismatch_count"], 0)
            self.assertTrue((output_dir / "verification-copy.json").exists())

    def test_decision_package_verifier_detects_memo_evaluation_mismatch(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            memo_path = output_dir / "intent-transport-decision-memo-draft.json"
            memo = json.loads(memo_path.read_text(encoding="utf-8"))
            memo["rollout_gate_evaluation"]["decision"] = "hold_candidate"
            memo_path.write_text(json.dumps(memo, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertFalse(verification["verified"])
            self.assertFalse(verification["evaluation_matches_memo"])

    def test_decision_package_verifier_rejects_unsupported_manifest_schema(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            manifest["manifest_schema_version"] = "9.9"
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertFalse(verification["schema_supported"])

    def test_decision_package_verifier_accepts_manifest_without_compact_summary_fields(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = manifest.get("artifacts", {})
            if isinstance(artifacts, dict):
                artifacts.pop("compact_summary_file", None)
                artifacts.pop("compact_summary_json_file", None)
                artifacts.pop("inspector_summary_file", None)
                artifacts.pop("inspector_summary_json_file", None)
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 0, msg=verify_result.stderr)
            verification = json.loads(verify_result.stdout)
            self.assertTrue(verification["verified"])
            self.assertFalse(verification["compact_summary_artifacts_present"])
            self.assertFalse(verification["compact_summary_checks_performed"])
            self.assertTrue(verification["compact_summary_checks_skipped"])
            self.assertTrue(verification["compact_summary_text_matches"])
            self.assertTrue(verification["compact_summary_json_matches"])
            self.assertFalse(verification["inspector_summary_artifacts_present"])
            self.assertFalse(verification["inspector_summary_checks_performed"])
            self.assertTrue(verification["inspector_summary_checks_skipped"])
            self.assertTrue(verification["inspector_summary_text_matches"])
            self.assertTrue(verification["inspector_summary_json_matches"])

    def test_decision_package_verifier_accepts_manifest_without_inspector_summary_fields(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            artifacts = manifest.get("artifacts", {})
            if isinstance(artifacts, dict):
                artifacts.pop("inspector_summary_file", None)
                artifacts.pop("inspector_summary_json_file", None)
            manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 0, msg=verify_result.stderr)
            verification = json.loads(verify_result.stdout)
            self.assertTrue(verification["verified"])
            self.assertTrue(verification["compact_summary_artifacts_present"])
            self.assertTrue(verification["compact_summary_checks_performed"])
            self.assertFalse(verification["compact_summary_checks_skipped"])
            self.assertFalse(verification["inspector_summary_artifacts_present"])
            self.assertFalse(verification["inspector_summary_checks_performed"])
            self.assertTrue(verification["inspector_summary_checks_skipped"])

    def test_decision_package_verifier_detects_inspector_summary_mismatch(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            (output_dir / "intent-transport-decision-package-inspector-summary.txt").write_text(
                "decision=corrupted\n",
                encoding="utf-8",
            )

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertFalse(verification["verified"])
            self.assertFalse(verification["inspector_summary_text_matches"])
            self.assertTrue(verification["inspector_summary_json_matches"])
            self.assertEqual(verification["inspector_summary_mismatch_count"], 1)

    def test_decision_package_verifier_detects_missing_artifacts(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            (output_dir / "intent-transport-decision-memo.md").unlink()

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertIn("memo_markdown_file", verification["missing_artifacts"])

    def test_decision_package_verifier_detects_compact_summary_mismatch(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            (output_dir / "intent-transport-decision-package-summary.txt").write_text(
                "decision=corrupted\n",
                encoding="utf-8",
            )

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertFalse(verification["verified"])
            self.assertFalse(verification["compact_summary_text_matches"])
            self.assertTrue(verification["compact_summary_json_matches"])
            self.assertEqual(verification["compact_summary_mismatch_count"], 1)

    def test_decision_package_verifier_detects_malformed_compact_summary_json(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            (output_dir / "intent-transport-decision-package-summary.json").write_text(
                "not-json\n",
                encoding="utf-8",
            )

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertFalse(verification["verified"])
            self.assertFalse(verification["compact_summary_json_matches"])

    def test_decision_package_verifier_detects_malformed_inspector_summary_json(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            (output_dir / "intent-transport-decision-package-inspector-summary.json").write_text(
                "not-json\n",
                encoding="utf-8",
            )

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            verify_result = self._run(
                "tools/verify_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(verify_result.returncode, 1)
            verification = json.loads(verify_result.stdout)
            self.assertFalse(verification["verified"])
            self.assertFalse(verification["inspector_summary_json_matches"])
            self.assertEqual(verification["inspector_summary_mismatch_count"], 1)

    def test_decision_package_inspector_emits_text_and_json(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"

            inspect_text_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(inspect_text_result.returncode, 0, msg=inspect_text_result.stderr)
            self.assertIn("decision=", inspect_text_result.stdout)
            self.assertIn("verified=true", inspect_text_result.stdout)
            self.assertIn("summary_checks_performed=true", inspect_text_result.stdout)
            self.assertIn("summary_mismatch_count=0", inspect_text_result.stdout)

            text_output_path = output_dir / "inspector-summary.txt"
            inspect_text_output_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--output",
                str(text_output_path),
            )
            self.assertEqual(inspect_text_output_result.returncode, 0, msg=inspect_text_output_result.stderr)
            self.assertTrue(text_output_path.exists())
            self.assertEqual(
                inspect_text_output_result.stdout.strip(),
                text_output_path.read_text(encoding="utf-8").strip(),
            )

            inspect_json_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--format",
                "json",
            )
            self.assertEqual(inspect_json_result.returncode, 0, msg=inspect_json_result.stderr)
            summary = json.loads(inspect_json_result.stdout)
            self.assertIn("decision", summary)
            self.assertTrue(summary["verified"])
            self.assertIn("compact_summary_checks_performed", summary)
            self.assertIn("compact_summary_checks_skipped", summary)
            self.assertIn("compact_summary_mismatch_count", summary)
            self.assertIn("compact_summary_mismatch_details", summary)

            json_output_path = output_dir / "inspector-summary.json"
            inspect_json_output_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--format",
                "json",
                "--output",
                str(json_output_path),
            )
            self.assertEqual(inspect_json_output_result.returncode, 0, msg=inspect_json_output_result.stderr)
            self.assertTrue(json_output_path.exists())
            self.assertEqual(
                json.loads(inspect_json_output_result.stdout),
                json.loads(json_output_path.read_text(encoding="utf-8")),
            )

    def test_decision_package_inspector_can_fail_on_unverified(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            verification_path = output_dir / "intent-transport-decision-package-verification.json"
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            verification["verified"] = False
            verification_path.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            inspect_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--fail-on-unverified",
            )
            self.assertEqual(inspect_result.returncode, 1)

    def test_decision_package_inspector_verify_before_inspect_refreshes_status(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            # Tamper summary text after package generation to make verification stale.
            summary_path = output_dir / "intent-transport-decision-package-summary.txt"
            summary_path.write_text("decision=corrupted\n", encoding="utf-8")

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            inspect_without_refresh = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--fail-on-unverified",
            )
            self.assertEqual(inspect_without_refresh.returncode, 0)

            inspect_with_refresh = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--fail-on-unverified",
                "--verify-before-inspect",
            )
            self.assertEqual(inspect_with_refresh.returncode, 1)

            failed_output_path = output_dir / "inspector-refresh-failed.json"
            inspect_with_refresh_output = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--fail-on-unverified",
                "--verify-before-inspect",
                "--format",
                "json",
                "--output",
                str(failed_output_path),
            )
            self.assertEqual(inspect_with_refresh_output.returncode, 1)
            self.assertTrue(failed_output_path.exists())
            failed_summary = json.loads(failed_output_path.read_text(encoding="utf-8"))
            self.assertFalse(failed_summary["verified"])

            inspect_json_with_refresh = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--verify-before-inspect",
                "--format",
                "json",
            )
            self.assertEqual(inspect_json_with_refresh.returncode, 0, msg=inspect_json_with_refresh.stderr)
            refreshed_summary = json.loads(inspect_json_with_refresh.stdout)
            self.assertFalse(refreshed_summary["verified"])

    def test_decision_package_inspector_uses_verifier_mismatch_count_field(self) -> None:
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

            output_dir = temp_root / "decision-package"
            package_result = self._run(
                "tools/build_operation_intent_decision_package.py",
                "--input-glob",
                str(captures_dir / "intent-transport-day*.json"),
                "--output-dir",
                str(output_dir),
            )
            self.assertEqual(package_result.returncode, 0, msg=package_result.stderr)

            verification_path = output_dir / "intent-transport-decision-package-verification.json"
            verification = json.loads(verification_path.read_text(encoding="utf-8"))
            verification["compact_summary_mismatch_count"] = 3
            verification["compact_summary_mismatch_details"] = []
            verification_path.write_text(json.dumps(verification, indent=2, sort_keys=True) + "\n", encoding="utf-8")

            manifest_path = output_dir / "intent-transport-decision-package-manifest.json"
            inspect_json_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
                "--format",
                "json",
            )
            self.assertEqual(inspect_json_result.returncode, 0, msg=inspect_json_result.stderr)
            summary = json.loads(inspect_json_result.stdout)
            self.assertEqual(summary["compact_summary_mismatch_count"], 3)
            self.assertEqual(summary["compact_summary_mismatch_details"], [])

            inspect_text_result = self._run(
                "tools/inspect_operation_intent_decision_package.py",
                "--manifest",
                str(manifest_path),
            )
            self.assertEqual(inspect_text_result.returncode, 0, msg=inspect_text_result.stderr)
            self.assertIn("summary_mismatch_count=3", inspect_text_result.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
