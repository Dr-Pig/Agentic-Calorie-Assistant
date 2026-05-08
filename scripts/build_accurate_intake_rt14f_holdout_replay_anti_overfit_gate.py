from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import read_json_artifact, write_json_artifact  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt14f_holdout_replay_anti_overfit_gate.json"
FORBIDDEN_TRUE_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "runtime_web_activation_approved",
    "live_provider_used_as_truth",
)


def build_rt14f_holdout_replay_anti_overfit_gate(
    *,
    anti_overfit_guard: dict[str, Any],
    holdout_plan: dict[str, Any],
    offline_shadow_replay: dict[str, Any],
    live_robustness_matrix: dict[str, Any],
    rt13b_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [
        _dependency_case(rt13b_artifact),
        _holdout_selection_case(anti_overfit_guard, holdout_plan),
        _shadow_replay_case(offline_shadow_replay),
        _live_robustness_case(live_robustness_matrix),
        _boundary_claim_case(
            anti_overfit_guard,
            holdout_plan,
            offline_shadow_replay,
            live_robustness_matrix,
            rt13b_artifact,
        ),
    ]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    holdout_summary = _dict(holdout_plan.get("summary"))
    replay_summary = _dict(offline_shadow_replay.get("summary"))
    robustness_summary = live_robustness_matrix
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_name": resolved_output_path.name,
            "artifact_path": str(resolved_output_path),
            "artifact_type": "accurate_intake_rt14f_holdout_replay_anti_overfit_gate",
            "claim_scope": "holdout_replay_and_anti_overfit_gate",
            "launch_scope": "current_shell_v1",
            "producer_track": "CurrentShell/ManagerRuntime",
            "target_manager_runtime_gate": "rt14f_holdout_replay_anti_overfit_gate",
            "pass_type": "runtime_backed",
            "runtime_backed": True,
            "live_llm_invoked": True,
            "production_db_used": False,
            "fooddb_truth_updated": False,
            "supports_journeys": ["B", "C", "D", "E", "J", "K"],
            "status": _status(blockers),
            "blockers": blockers,
            "summary": {
                "fixed_case_count": _int(holdout_summary.get("fixed_case_count")),
                "withheld_holdout_variant_count": _int(
                    holdout_summary.get("withheld_holdout_variant_count")
                    or holdout_summary.get("holdout_variant_count")
                ),
                "strict_replay_ready": replay_summary.get("strict_replay_ready") is True,
                "full_suite_replay_ready": replay_summary.get("full_suite_replay_ready") is True,
                "sample_run_count": _int(replay_summary.get("sample_run_count")),
                "retry_dependent_evidence_present": (
                    _int(replay_summary.get("pass_after_retry_count"))
                    + _int(replay_summary.get("retry_dependent_count"))
                    > 0
                    or robustness_summary.get("has_retry_dependent_evidence") is True
                ),
                "timeout_evidence_present": (
                    _int(replay_summary.get("timeout_count")) > 0
                    or robustness_summary.get("has_timeout_evidence") is True
                ),
                "contract_overfit_risk": robustness_summary.get("contract_overfit_risk") is True,
                "model_diversity_status": _optional_string(
                    robustness_summary.get("model_diversity_status")
                    or replay_summary.get("model_diversity_status")
                ),
                "model_diversity_required_before_private_candidate": True,
            },
            "semantic_boundary": {
                "deterministic_role": "validate_selection_replay_and_overfit_risk",
                "llm_role": "future_live_manager_provider",
                "deterministic_must_not_select_intent": True,
                "deterministic_must_not_rewrite_manager_semantics": True,
            },
            "cases": cases,
            "dependencies": {
                "rt13b_latency_cost_cache_budget_pack": {
                    "target_manager_runtime_gate": rt13b_artifact.get("target_manager_runtime_gate"),
                    "status": rt13b_artifact.get("status"),
                }
            },
            "non_claims": {
                "product_readiness_claimed": False,
                "private_self_use_approved": False,
                "whole_product_mvp_ready": False,
                "production_selected": False,
                "mutation_rollout_approved": False,
            },
        }
    )


def _dependency_case(rt13b_artifact: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if rt13b_artifact.get("target_manager_runtime_gate") != "rt13b_latency_cost_cache_budget_pack":
        blockers.append("rt13b_latency_cost_cache_budget_pack_unexpected_gate")
    if rt13b_artifact.get("status") != "pass":
        blockers.append("rt13b_latency_cost_cache_budget_pack_not_pass")
    return _case(
        "dependencies",
        blockers,
        {
            "rt13b_status": rt13b_artifact.get("status"),
            "rt13b_gate": rt13b_artifact.get("target_manager_runtime_gate"),
        },
    )


def _holdout_selection_case(
    anti_overfit_guard: dict[str, Any],
    holdout_plan: dict[str, Any],
) -> dict[str, Any]:
    blockers: list[str] = []
    if anti_overfit_guard.get("artifact_type") != "accurate_intake_context_live_diagnostic_anti_overfit_guard":
        blockers.append("anti_overfit_guard_unexpected_artifact_type")
    if anti_overfit_guard.get("status") != "pass":
        blockers.append("anti_overfit_guard_not_pass")
    anti_summary = _dict(anti_overfit_guard.get("summary"))
    if anti_summary.get("fixed_case_matrix_used") is not True:
        blockers.append("anti_overfit_fixed_case_matrix_not_used")
    if _int(anti_summary.get("holdout_utterance_variant_count")) < _int(anti_summary.get("case_count")) * 2:
        blockers.append("anti_overfit_holdout_variant_count_too_low")

    if holdout_plan.get("artifact_type") != "accurate_intake_context_live_diagnostic_holdout_plan":
        blockers.append("holdout_plan_unexpected_artifact_type")
    if holdout_plan.get("status") != "pass":
        blockers.append("holdout_plan_not_pass")
    if holdout_plan.get("fixed_case_matrix_used") is not True:
        blockers.append("fixed_case_matrix_not_used")
    if holdout_plan.get("holdout_variants_withheld_from_default_live_prompt") is not True:
        blockers.append("holdout_variants_not_withheld")
    if holdout_plan.get("ad_hoc_live_case_selection_allowed") is not False:
        blockers.append("ad_hoc_live_case_selection_allowed")
    if holdout_plan.get("provider_optimized_case_selection_allowed") is not False:
        blockers.append("provider_optimized_case_selection_allowed")
    summary = _dict(holdout_plan.get("summary"))
    if _int(summary.get("withheld_holdout_variant_count") or summary.get("holdout_variant_count")) < (
        _int(summary.get("fixed_case_count")) * 2
    ):
        blockers.append("withheld_holdout_variant_count_too_low")
    return _case(
        "holdout_selection",
        blockers,
        {
            "fixed_case_count": _int(summary.get("fixed_case_count")),
            "withheld_holdout_variant_count": _int(
                summary.get("withheld_holdout_variant_count") or summary.get("holdout_variant_count")
            ),
            "ad_hoc_live_case_selection_allowed": holdout_plan.get("ad_hoc_live_case_selection_allowed"),
            "provider_optimized_case_selection_allowed": holdout_plan.get(
                "provider_optimized_case_selection_allowed"
            ),
        },
    )


def _shadow_replay_case(offline_shadow_replay: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if offline_shadow_replay.get("artifact_type") != "accurate_intake_mvp_offline_shadow_replay":
        blockers.append("unexpected_artifact_type")
    input_integrity = _dict(offline_shadow_replay.get("input_integrity"))
    if input_integrity.get("passed") is not True:
        blockers.append("input_integrity_not_pass")
    summary = _dict(offline_shadow_replay.get("summary"))
    if summary.get("strict_replay_ready") is not True:
        blockers.append("strict_replay_not_ready")
    if _int(summary.get("pass_after_retry_count")) or _int(summary.get("retry_dependent_count")):
        blockers.append("retry_dependent_evidence_present")
    if _int(summary.get("timeout_count")):
        blockers.append("timeout_evidence_present")
    if _int(summary.get("failed_stage_count")):
        blockers.append("failed_stage_evidence_present")
    if summary.get("eligible_for_private_self_use_candidate") is True:
        blockers.append("private_candidate_claimed_by_replay")
    return _case(
        "shadow_replay",
        blockers,
        {
            "sample_run_count": _int(summary.get("sample_run_count")),
            "strict_replay_ready": summary.get("strict_replay_ready") is True,
            "full_suite_replay_ready": summary.get("full_suite_replay_ready") is True,
            "pass_after_retry_count": _int(summary.get("pass_after_retry_count")),
            "timeout_count": _int(summary.get("timeout_count")),
        },
    )


def _live_robustness_case(live_robustness_matrix: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if live_robustness_matrix.get("artifact_type") != "accurate_intake_mvp_live_robustness_matrix":
        blockers.append("unexpected_artifact_type")
    input_integrity = _dict(live_robustness_matrix.get("input_integrity"))
    if input_integrity.get("passed") is not True:
        blockers.append("input_integrity_not_pass")
    if live_robustness_matrix.get("has_retry_dependent_evidence") is True:
        blockers.append("retry_dependent_evidence_present")
    if live_robustness_matrix.get("has_timeout_evidence") is True:
        blockers.append("timeout_evidence_present")
    if live_robustness_matrix.get("has_error_evidence") is True:
        blockers.append("error_evidence_present")
    if live_robustness_matrix.get("contract_overfit_risk") is True:
        blockers.append("contract_overfit_risk")
    return _case(
        "live_robustness",
        blockers,
        {
            "model_diversity_status": live_robustness_matrix.get("model_diversity_status"),
            "model_inversion_evidence_passed": live_robustness_matrix.get(
                "model_inversion_evidence_passed"
            ),
            "private_self_use_candidate_blocked": live_robustness_matrix.get(
                "private_self_use_candidate_blocked"
            ),
            "contract_overfit_risk": live_robustness_matrix.get("contract_overfit_risk"),
        },
    )


def _boundary_claim_case(*artifacts: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    for index, artifact in enumerate(artifacts):
        for flag in FORBIDDEN_TRUE_FLAGS:
            if _truthy(artifact.get(flag)):
                blockers.append(f"source_{index}_{flag}")
    return _case(
        "boundary_claims",
        blockers,
        {
            "forbidden_claim_flags_checked": list(FORBIDDEN_TRUE_FLAGS),
            "deterministic_semantic_owner": False,
        },
    )


def _case(case_id: str, blockers: list[str], observed: dict[str, Any]) -> dict[str, Any]:
    return {
        "case_id": case_id,
        "status": _status(blockers),
        "blockers": blockers,
        "observed": observed,
    }


def _truthy(value: Any) -> bool:
    if value is True:
        return True
    if value is False or value is None:
        return False
    if isinstance(value, (int, float)):
        return value != 0
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "claimed", "enabled"}
    return False


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _int(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _optional_string(value: Any) -> str | None:
    text = str(value or "").strip()
    return text or None


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RT14f holdout replay anti-overfit gate.")
    parser.add_argument("--anti-overfit-artifact", type=Path, required=True)
    parser.add_argument("--holdout-plan-artifact", type=Path, required=True)
    parser.add_argument("--offline-replay-artifact", type=Path, required=True)
    parser.add_argument("--live-robustness-artifact", type=Path, required=True)
    parser.add_argument("--rt13b-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    artifact = build_rt14f_holdout_replay_anti_overfit_gate(
        anti_overfit_guard=read_json_artifact(args.anti_overfit_artifact),
        holdout_plan=read_json_artifact(args.holdout_plan_artifact),
        offline_shadow_replay=read_json_artifact(args.offline_replay_artifact),
        live_robustness_matrix=read_json_artifact(args.live_robustness_artifact),
        rt13b_artifact=read_json_artifact(args.rt13b_artifact),
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
