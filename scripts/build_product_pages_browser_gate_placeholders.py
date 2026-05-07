from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

PLACEHOLDER_ARTIFACTS = (
    "artifacts/accurate_intake_product_pages_browser_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_long_session_navigation_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_seven_day_diary_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_short_term_context_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_target_candidate_ui_smoke_ci.json",
    "artifacts/accurate_intake_product_pages_visual_qa_ci.json",
    "artifacts/accurate_intake_product_pages_renderer_source_map_ci.json",
    "artifacts/accurate_intake_short_term_context_runtime_replay_ci.json",
    "artifacts/accurate_intake_fake_provider_context_smoke_ci.json",
    "artifacts/accurate_intake_pl_ce_context_coverage_matrix_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_case_matrix_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_anti_overfit_guard_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_holdout_plan_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_dry_run_evaluator_ci.json",
    "artifacts/accurate_intake_context_live_provider_input_preflight_ci.json",
    "artifacts/accurate_intake_context_live_response_contract_dry_run_ci.json",
    "artifacts/accurate_intake_context_live_diagnostic_gate_ci.json",
    "artifacts/accurate_intake_pl_ce_ui_context_alignment_pack_ci.json",
    "artifacts/accurate_intake_pl_ce_local_mvp_candidate_bundle_ci.json",
    "artifacts/accurate_intake_fixture_full_product_loop_e2e_ci.json",
    "artifacts/accurate_intake_pl_ce_product_pages_self_use_flow_gate_ci.json",
    "artifacts/accurate_intake_pl_ce_browser_activation_evidence_gate_ci.json",
    "artifacts/accurate_intake_non_fooddb_manager_tool_contract_ci.json",
    "artifacts/accurate_intake_pl_ce_activation_review_manifest_ci.json",
    "artifacts/accurate_intake_pl_ce_current_metadata_freshness_pack_ci.json",
    "artifacts/accurate_intake_pl_ce_serial_handoff_ci.json",
    "artifacts/accurate_intake_pl_ce_merge_queue_metadata_ci.json",
)

PLACEHOLDER_DIRS = ("artifacts/product_pages_visual_qa_ci",)


def build_placeholders(*, mode: str, reason: str) -> dict[str, object]:
    artifact_payload = {
        "artifact_type": "product_pages_browser_gate_placeholder",
        "status": "blocked_upstream" if mode == "blocked_upstream" else "skipped",
        "mode": mode,
        "reason": reason,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }
    written: list[str] = []
    for relative_path in PLACEHOLDER_ARTIFACTS:
        path = ROOT / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(artifact_payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        written.append(relative_path)
    for relative_dir in PLACEHOLDER_DIRS:
        path = ROOT / relative_dir
        path.mkdir(parents=True, exist_ok=True)
        written.append(relative_dir)
    return {
        "artifact_type": "product_pages_browser_gate_placeholder_report",
        "mode": mode,
        "reason": reason,
        "written": written,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Write placeholder artifacts for fast-pass or blocked-upstream product pages jobs.")
    parser.add_argument("--mode", choices=("fast_pass", "blocked_upstream"), required=True)
    parser.add_argument("--reason", required=True)
    args = parser.parse_args(argv)

    report = build_placeholders(mode=args.mode, reason=args.reason)
    print(json.dumps(report, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
