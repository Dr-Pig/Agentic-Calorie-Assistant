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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt12b_live_trace_grading_extension.json"
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


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _case(artifact: dict[str, Any], expected_case_id: str) -> dict[str, Any]:
    return next(
        (_dict(case) for case in _list(artifact.get("cases")) if _dict(case).get("case_id") == expected_case_id),
        {},
    )


def _turn(case: dict[str, Any], turn_number: int) -> dict[str, Any]:
    return next(
        (_dict(turn) for turn in _list(case.get("turns")) if int(_dict(turn).get("turn") or 0) == turn_number),
        {},
    )


def _tool_names(turn: dict[str, Any]) -> list[str]:
    names: list[str] = []
    for round_item in _list(turn.get("manager_rounds")):
        decision = _dict(_dict(round_item).get("decision"))
        for call in _list(decision.get("tool_calls")):
            name = str(_dict(call).get("name") or "").strip()
            if name:
                names.append(name)
    return names


def _manager_round_count(turn: dict[str, Any]) -> int:
    return len(_list(turn.get("manager_rounds")))


def _artifact_blockers(label: str, artifact: dict[str, Any], *, expected_case_id: str) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append(f"{label}.unsupported_live_diagnostic_artifact_type")
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


def _grade_turn(
    *,
    case_id: str,
    turn: dict[str, Any],
    expected_tools: list[str],
    expected_final_action: str | list[str] | None,
    manager_round_required: bool,
) -> dict[str, Any]:
    blockers: list[str] = []
    if not turn:
        blockers.append("turn_missing")
    if manager_round_required and _manager_round_count(turn) == 0:
        blockers.append("manager_rounds_missing")
    actual_tools = _tool_names(turn)
    if actual_tools != expected_tools:
        blockers.append(f"tool_choice_mismatch:expected={expected_tools}:actual={actual_tools}")
    if isinstance(expected_final_action, list):
        expected_final_actions = expected_final_action
    elif expected_final_action is None:
        expected_final_actions = []
    else:
        expected_final_actions = [expected_final_action]
    if expected_final_actions and turn.get("manager_final_action") not in expected_final_actions:
        blockers.append(
            f"final_action_mismatch:expected={expected_final_actions}:actual={turn.get('manager_final_action')}"
        )
    if _dict(turn.get("runtime_error")):
        blockers.append("runtime_error_present")
    return {
        "case_id": case_id,
        "turn": turn.get("turn"),
        "status": _status(blockers),
        "blockers": blockers,
        "manager_round_count": _manager_round_count(turn),
        "expected_tools": expected_tools,
        "actual_tools": actual_tools,
        "expected_final_action": expected_final_action,
        "actual_final_action": turn.get("manager_final_action"),
    }


def _live_trace_cases(
    *,
    exact_artifact: dict[str, Any],
    bubble_artifact: dict[str, Any],
    luwei_artifact: dict[str, Any],
    correction_artifact: dict[str, Any],
) -> list[dict[str, Any]]:
    exact = _case(exact_artifact, "exact_item_official_label")
    bubble = _case(bubble_artifact, "bubble_milk_tea_refinement")
    luwei = _case(luwei_artifact, "luwei_bare_to_listed_basket")
    correction = _case(correction_artifact, "chinese_chicken_rice_correction_removal_debug")
    return [
        _grade_turn(
            case_id="exact_item_official_label.turn1",
            turn=_turn(exact, 1),
            expected_tools=["estimate_nutrition"],
            expected_final_action="commit",
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="bubble_milk_tea_refinement.turn1",
            turn=_turn(bubble, 1),
            expected_tools=["estimate_nutrition"],
            expected_final_action="commit",
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="bubble_milk_tea_refinement.turn2",
            turn=_turn(bubble, 2),
            expected_tools=["estimate_nutrition"],
            expected_final_action=["commit", "correction_applied"],
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="luwei_bare_to_listed_basket.turn1",
            turn=_turn(luwei, 1),
            expected_tools=[],
            expected_final_action="ask_followup",
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="luwei_bare_to_listed_basket.turn2",
            turn=_turn(luwei, 2),
            expected_tools=["estimate_nutrition"],
            expected_final_action="commit",
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="chinese_chicken_rice_correction_removal_debug.turn2",
            turn=_turn(correction, 2),
            expected_tools=["estimate_nutrition"],
            expected_final_action="correction_applied",
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="chinese_chicken_rice_correction_removal_debug.turn3",
            turn=_turn(correction, 3),
            expected_tools=["resolve_correction_target"],
            expected_final_action="correction_applied",
            manager_round_required=True,
        ),
        _grade_turn(
            case_id="chinese_chicken_rice_correction_removal_debug.turn4",
            turn=_turn(correction, 4),
            expected_tools=[],
            expected_final_action=None,
            manager_round_required=False,
        ),
    ]


def _rt11c_blockers(rt11c_artifact: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if rt11c_artifact.get("target_manager_runtime_gate") != "rt11c_renderer_input_basis_evidence_pack":
        blockers.append("rt11c_renderer_basis.unexpected_gate")
    if rt11c_artifact.get("status") != "pass":
        blockers.append("rt11c_renderer_basis.status_not_pass")
    boundary = _dict(rt11c_artifact.get("appshell_contract_boundary"))
    if boundary.get("renderer_input_basis_contract_green") is not True:
        blockers.append("rt11c_renderer_basis.contract_not_green")
    if boundary.get("frontend_semantic_owner") is not False:
        blockers.append("rt11c_renderer_basis.frontend_semantic_owner")
    return blockers


def build_rt12b_live_trace_grading_extension(
    *,
    exact_item_artifact: dict[str, Any],
    bubble_artifact: dict[str, Any],
    luwei_artifact: dict[str, Any],
    no_plan_artifact: dict[str, Any],
    correction_artifact: dict[str, Any],
    rt11c_artifact: dict[str, Any],
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
        blockers.extend(_artifact_blockers(label, artifact, expected_case_id=EXPECTED_LIVE_CASE_IDS[label]))
    blockers.extend(_rt11c_blockers(rt11c_artifact))

    cases = _live_trace_cases(
        exact_artifact=exact_item_artifact,
        bubble_artifact=bubble_artifact,
        luwei_artifact=luwei_artifact,
        correction_artifact=correction_artifact,
    )
    blockers.extend(f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"])
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt12b_live_trace_grading_extension",
        "claim_scope": "live_trace_grading_extension",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt12b_live_trace_grading_extension",
        "pass_type": "runtime_backed",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "status": _status(blockers),
        "blockers": blockers,
        "supports_journeys": ["B", "C", "D", "K"],
        "grade_layers": [
            "live_trace_shape",
            "live_tool_choice",
            "live_final_action",
            "renderer_input_basis_dependency",
        ],
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
            "llm_judge_used": False,
            "argument_accuracy_not_locked_in_v1": True,
        },
        "cases": cases,
        "rt11c_dependency": {
            "status": rt11c_artifact.get("status"),
            "renderer_input_basis_contract_green": _dict(
                rt11c_artifact.get("appshell_contract_boundary")
            ).get("renderer_input_basis_contract_green"),
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
    parser = argparse.ArgumentParser(description="Build the RT12b live trace grading extension artifact.")
    parser.add_argument("--exact-item-artifact", type=Path, required=True)
    parser.add_argument("--bubble-artifact", type=Path, required=True)
    parser.add_argument("--luwei-artifact", type=Path, required=True)
    parser.add_argument("--no-plan-artifact", type=Path, required=True)
    parser.add_argument("--correction-artifact", type=Path, required=True)
    parser.add_argument("--rt11c-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)
    artifact = build_rt12b_live_trace_grading_extension(
        exact_item_artifact=read_json_artifact(args.exact_item_artifact),
        bubble_artifact=read_json_artifact(args.bubble_artifact),
        luwei_artifact=read_json_artifact(args.luwei_artifact),
        no_plan_artifact=read_json_artifact(args.no_plan_artifact),
        correction_artifact=read_json_artifact(args.correction_artifact),
        rt11c_artifact=read_json_artifact(args.rt11c_artifact),
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
