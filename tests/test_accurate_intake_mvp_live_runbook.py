from __future__ import annotations

from pathlib import Path


def test_accurate_intake_live_diagnostic_runbook_records_staged_protocol() -> None:
    runbook_path = Path("docs/quality/ACCURATE_INTAKE_MVP_LIVE_DIAGNOSTIC_RUNBOOK.md")

    assert runbook_path.exists()

    runbook = runbook_path.read_text(encoding="utf-8-sig")

    required_fragments = [
        "claim scope: `live_diagnostic`",
        "Generated live artifacts are local diagnostic evidence, not repo truth",
        "full_suite_live_diagnostic remains blocked",
        "offline replay artifact is present and `strict_replay_ready=true`",
        "Full-Suite Evidence Window",
        "full_suite_replay_ready=true",
        "One strict full-suite artifact is diagnostic evidence only",
        "provider robustness matrix has `model_inversion_evidence_passed=true`",
        "--stage full_suite_live_diagnostic --offline-replay-artifact artifacts/accurate_intake_mvp_offline_shadow_replay.json",
        "offline_replay_required",
        "strict_pass_first_attempt",
        "pass_after_retry is not strict evidence",
        "timeout_after_retry remains a blocker",
        "private_self_use_approved=false",
        "product_readiness_claimed=false",
        "production_selected=false",
        "mutation_rollout_approved=false",
        "live_provider_used_as_truth=false",
        "No Tavily/web product truth",
        "No production DB",
        "No shadow/canary",
        "live_canary_approved=false",
        "kimi_active_runtime_default_allowed=false",
        "browser_executed=true",
        "stay_local_self_use",
        "python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage provider_health_smoke",
        "python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage schema_contract_probe",
        "python scripts/run_accurate_intake_mvp_live_diagnostic.py --stage fake_provider_active_runtime_gate",
        "tests/test_accurate_intake_mvp_offline_shadow_replay.py",
        "--stage single_case_live_probe --case-id explicit_item_removal_seeded",
        "--stage single_case_live_probe --case-id chinese_chicken_rice_correction_removal_debug",
        "python scripts/build_accurate_intake_mvp_live_stage_manifest.py",
        "python scripts/build_accurate_intake_contract_hardening_guard.py",
        "python scripts/build_accurate_intake_mvp_offline_shadow_replay.py",
        "python scripts/build_accurate_intake_mvp_live_robustness_matrix.py",
        "python scripts/build_accurate_intake_mvp_live_cost_summary.py",
        "python scripts/build_accurate_intake_mvp_live_decision_pack.py",
        "python scripts/build_accurate_intake_pre_live_self_use_decision_pack.py",
        "python scripts/build_accurate_intake_mvp_private_self_use_candidate.py",
        "artifacts/accurate_intake_mvp_live_diagnostic_provider_health.json",
        "artifacts/accurate_intake_mvp_live_diagnostic_schema_probe.json",
        "artifacts/accurate_intake_mvp_live_diagnostic_fake_runtime_gate.json",
        "artifacts/accurate_intake_mvp_live_diagnostic_seeded_removal.json",
        "artifacts/accurate_intake_mvp_live_diagnostic_single_case.json",
        "artifacts/accurate_intake_mvp_live_diagnostic_full_suite.json",
        "artifacts/accurate_intake_mvp_live_stage_manifest.json",
        "artifacts/accurate_intake_mvp_offline_shadow_replay.json",
        "artifacts/accurate_intake_mvp_live_robustness_matrix.json",
        "artifacts/accurate_intake_mvp_live_cost_summary.json",
        "artifacts/accurate_intake_mvp_live_decision_pack.json",
        "artifacts/accurate_intake_mvp_private_self_use_candidate.json",
        "python scripts/build_accurate_intake_mvp_live_stage_manifest.py --output artifacts/accurate_intake_mvp_live_stage_manifest_run_i.json",
        "python scripts/build_accurate_intake_contract_hardening_guard.py --output artifacts/accurate_intake_contract_hardening_guard_run_i.json",
        "python scripts/build_accurate_intake_mvp_offline_shadow_replay.py --stage-manifest artifacts/accurate_intake_mvp_live_stage_manifest_run_i.json --output artifacts/accurate_intake_mvp_offline_shadow_replay_run_i.json",
        "python scripts/build_accurate_intake_mvp_live_robustness_matrix.py --output artifacts/accurate_intake_mvp_live_robustness_matrix_run_i.json",
        "python scripts/build_accurate_intake_mvp_live_cost_summary.py --output artifacts/accurate_intake_mvp_live_cost_summary_run_i.json",
        "python scripts/build_accurate_intake_mvp_live_decision_pack.py --output artifacts/accurate_intake_mvp_live_decision_pack_run_i.json",
        "python scripts/build_accurate_intake_mvp_private_self_use_candidate.py --output artifacts/accurate_intake_mvp_private_self_use_candidate_run_i.json",
        "live full-suite failure unlocks attribution/audit only",
        "live failure alone cannot justify prompt/schema/contract hardening",
        "contract_hardening_debt",
        "legal_flows_broken",
        "holdout_tests_added",
        "token counts are not billing truth",
        "cost_unavailable_without_pricing=true",
        "billing_truth_source=provider_reported_artifact_fields_only",
    ]

    for fragment in required_fragments:
        assert fragment in runbook
