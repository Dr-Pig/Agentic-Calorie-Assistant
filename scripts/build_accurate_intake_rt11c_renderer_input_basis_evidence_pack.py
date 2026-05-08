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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt11c_renderer_input_basis_evidence_pack.json"
REQUIRED_NON_CLAIM_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "live_provider_used_as_truth",
    "runtime_web_activation_approved",
)
EXPECTED_LIVE_CASE_IDS = {
    "exact_item": "exact_item_official_label",
    "bubble": "bubble_milk_tea_refinement",
    "luwei": "luwei_bare_to_listed_basket",
    "no_plan": "no_plan_consumed_without_budget_target",
    "correction": "chinese_chicken_rice_correction_removal_debug",
}
COMMITTED_ACTIONS = {"commit", "correction_applied"}


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _case(artifact: dict[str, Any], expected_case_id: str) -> dict[str, Any]:
    cases = [_dict(case) for case in _list(artifact.get("cases"))]
    return next((case for case in cases if case.get("case_id") == expected_case_id), {})


def _turn(case: dict[str, Any], turn_number: int) -> dict[str, Any]:
    return next(
        (_dict(turn) for turn in _list(case.get("turns")) if int(_dict(turn).get("turn") or 0) == turn_number),
        {},
    )


def _live_artifact_blockers(label: str, artifact: dict[str, Any], *, expected_case_id: str) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append(f"{label}.unsupported_artifact_type")
    if artifact.get("provider_mode") != "live":
        blockers.append(f"{label}.provider_mode_not_live")
    if artifact.get("live_invoked") is not True or artifact.get("live_llm_invoked") is not True:
        blockers.append(f"{label}.live_llm_not_invoked")
    for flag in REQUIRED_NON_CLAIM_FLAGS:
        if artifact.get(flag) is True:
            blockers.append(f"{label}.non_claim_violation:{flag}")

    case = _case(artifact, expected_case_id)
    if not case:
        blockers.append(f"{label}.expected_case_missing:{expected_case_id}")
    else:
        if case.get("case_contract_status") != "strict_pass":
            blockers.append(f"{label}.case_contract_not_strict_pass")
        if case.get("verdict") != "pass":
            blockers.append(f"{label}.case_verdict_not_pass")
        if case.get("failure_layer") is not None:
            blockers.append(f"{label}.case_failure_layer_present")
    return blockers


def _renderer_turn_blockers(case_label: str, turn: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in ("coach_message", "manager_final_action", "remaining_budget", "show_macro", "macro_guard_reason"):
        if field not in turn:
            blockers.append(f"{case_label}.renderer_basis_missing:{field}")
    if not str(turn.get("coach_message") or "").strip():
        blockers.append(f"{case_label}.coach_message_empty")
    remaining_budget = _dict(turn.get("remaining_budget"))
    if turn.get("manager_final_action") in COMMITTED_ACTIONS and not isinstance(
        remaining_budget.get("consumed_kcal"),
        int,
    ):
        blockers.append(f"{case_label}.committed_turn_missing_consumed_kcal")
    return blockers


def _no_plan_blockers(turn: dict[str, Any]) -> list[str]:
    remaining_budget = _dict(turn.get("remaining_budget"))
    blockers: list[str] = []
    if remaining_budget.get("daily_target_kcal") is not None:
        blockers.append("no_plan.degraded_basis_claimed_daily_target")
    if remaining_budget.get("remaining_kcal") is not None:
        blockers.append("no_plan.degraded_basis_claimed_remaining")
    if remaining_budget.get("status") not in {"onboarding_required", "degraded_no_plan"}:
        blockers.append("no_plan.degraded_basis_status_missing")
    return blockers


def _rt6_body_blockers(rt6_artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if rt6_artifact.get("target_manager_runtime_gate") != "rt6_bootstrap_no_plan_body_closure":
        blockers.append("rt6_body_basis.unexpected_gate")
    if rt6_artifact.get("status") != "pass":
        blockers.append("rt6_body_basis.status_not_pass")
    cases = {str(case.get("case_id")): _dict(case) for case in _list(rt6_artifact.get("cases"))}
    for case_id in ("bootstrap_ready", "manager_body_observation_write", "weight_route_write"):
        if cases.get(case_id, {}).get("status") != "pass":
            blockers.append(f"rt6_body_basis.case_not_pass:{case_id}")
    if not isinstance(cases.get("bootstrap_ready", {}).get("daily_target_kcal"), int):
        blockers.append("rt6_body_basis.daily_target_missing")
    for case_id in ("manager_body_observation_write", "weight_route_write"):
        if not isinstance(cases.get(case_id, {}).get("latest_weight_value"), int | float):
            blockers.append(f"rt6_body_basis.latest_weight_missing:{case_id}")
    return blockers


def _turn_cases(
    *,
    exact_artifact: dict[str, Any],
    bubble_artifact: dict[str, Any],
    luwei_artifact: dict[str, Any],
    no_plan_artifact: dict[str, Any],
    correction_artifact: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    return {
        "exact_item_commit": _turn(_case(exact_artifact, "exact_item_official_label"), 1),
        "optional_refinement_initial_commit": _turn(_case(bubble_artifact, "bubble_milk_tea_refinement"), 1),
        "optional_refinement_update": _turn(_case(bubble_artifact, "bubble_milk_tea_refinement"), 2),
        "blocking_clarify_question": _turn(_case(luwei_artifact, "luwei_bare_to_listed_basket"), 1),
        "blocking_clarify_commit": _turn(_case(luwei_artifact, "luwei_bare_to_listed_basket"), 2),
        "no_plan_degraded_query": _turn(_case(no_plan_artifact, "no_plan_consumed_without_budget_target"), 1),
        "correction_update": _turn(_case(correction_artifact, "chinese_chicken_rice_correction_removal_debug"), 2),
        "correction_remove": _turn(_case(correction_artifact, "chinese_chicken_rice_correction_removal_debug"), 3),
        "correction_remaining_query": _turn(_case(correction_artifact, "chinese_chicken_rice_correction_removal_debug"), 4),
    }


def build_rt11c_renderer_input_basis_evidence_pack(
    *,
    exact_item_artifact: dict[str, Any],
    bubble_artifact: dict[str, Any],
    luwei_artifact: dict[str, Any],
    no_plan_artifact: dict[str, Any],
    correction_artifact: dict[str, Any],
    rt6_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []
    for label, artifact in (
        ("exact_item", exact_item_artifact),
        ("bubble", bubble_artifact),
        ("luwei", luwei_artifact),
        ("no_plan", no_plan_artifact),
        ("correction", correction_artifact),
    ):
        blockers.extend(_live_artifact_blockers(label, artifact, expected_case_id=EXPECTED_LIVE_CASE_IDS[label]))

    turn_cases = _turn_cases(
        exact_artifact=exact_item_artifact,
        bubble_artifact=bubble_artifact,
        luwei_artifact=luwei_artifact,
        no_plan_artifact=no_plan_artifact,
        correction_artifact=correction_artifact,
    )
    for case_label, turn in turn_cases.items():
        blockers.extend(_renderer_turn_blockers(case_label, turn))
    blockers.extend(_no_plan_blockers(turn_cases["no_plan_degraded_query"]))
    blockers.extend(_rt6_body_blockers(rt6_artifact))

    rt6_cases = {str(case.get("case_id")): _dict(case) for case in _list(rt6_artifact.get("cases"))}
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt11c_renderer_input_basis_evidence_pack",
        "claim_scope": "renderer_input_basis_runtime_evidence_for_appshell_consumption",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt11c_renderer_input_basis_evidence_pack",
        "pass_type": "runtime_backed",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "status": _status(blockers),
        "blockers": blockers,
        "supports_journeys": ["A", "B", "C", "D", "E", "G", "H", "J", "K"],
        "appshell_contract_boundary": {
            "manager_runtime_truth_owner": True,
            "appshell_downstream_consumer_only": True,
            "frontend_semantic_owner": False,
            "frontend_selected_target": False,
            "frontend_calculates_kcal": False,
            "frontend_calculates_remaining": False,
            "renderer_input_basis_contract_green": not blockers,
        },
        "renderer_input_basis_by_surface": {
            "chat": {
                "source": "live_turn_summaries",
                "fields": ["coach_message", "manager_final_action", "workflow_effect", "request_id"],
                "case_count": len(turn_cases),
            },
            "today": {
                "source": "live_turn_summaries.remaining_budget_and_state_delta",
                "fields": [
                    "remaining_budget.status",
                    "remaining_budget.daily_target_kcal",
                    "remaining_budget.consumed_kcal",
                    "remaining_budget.remaining_kcal",
                    "state_delta.canonical_commit",
                    "show_macro",
                    "macro_guard_reason",
                ],
                "degraded_no_plan_checked": True,
            },
            "body": {
                "source": "rt6_bootstrap_no_plan_body_closure",
                "fields": [
                    "active_body_plan.daily_target_kcal",
                    "latest_weight.value",
                    "latest_weight.unit",
                ],
                "bootstrap_daily_target_kcal": rt6_cases.get("bootstrap_ready", {}).get("daily_target_kcal"),
                "manager_latest_weight_value": rt6_cases.get("manager_body_observation_write", {}).get(
                    "latest_weight_value"
                ),
                "ui_latest_weight_value": rt6_cases.get("weight_route_write", {}).get("latest_weight_value"),
            },
        },
        "summary": {
            "surface_count": 3,
            "live_case_count": 5,
            "turn_basis_count": len(turn_cases),
            "body_basis_source_status": rt6_artifact.get("status"),
            "degraded_no_plan_budget_basis_preserved": not _no_plan_blockers(turn_cases["no_plan_degraded_query"]),
        },
        "non_claims": {
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "whole_product_mvp_ready": False,
            "production_selected": False,
            "mutation_rollout_approved": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RT11c renderer input basis evidence pack.")
    parser.add_argument("--exact-item-artifact", type=Path, required=True)
    parser.add_argument("--bubble-artifact", type=Path, required=True)
    parser.add_argument("--luwei-artifact", type=Path, required=True)
    parser.add_argument("--no-plan-artifact", type=Path, required=True)
    parser.add_argument("--correction-artifact", type=Path, required=True)
    parser.add_argument("--rt6-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    artifact = build_rt11c_renderer_input_basis_evidence_pack(
        exact_item_artifact=read_json_artifact(args.exact_item_artifact),
        bubble_artifact=read_json_artifact(args.bubble_artifact),
        luwei_artifact=read_json_artifact(args.luwei_artifact),
        no_plan_artifact=read_json_artifact(args.no_plan_artifact),
        correction_artifact=read_json_artifact(args.correction_artifact),
        rt6_artifact=read_json_artifact(args.rt6_artifact),
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
