from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app.shared.infra.json_artifacts import write_json_artifact  # noqa: E402
from scripts import run_accurate_intake_rt11_final_response_quality as fixture  # noqa: E402


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt11b_final_response_quality_live_wall.json"
REQUIRED_NON_CLAIM_FLAGS = (
    "readiness_claimed",
    "product_readiness_claimed",
    "private_self_use_approved",
    "production_selected",
    "mutation_rollout_approved",
    "live_provider_used_as_truth",
    "runtime_web_activation_approved",
)
REQUIRED_STAGE_ID = "single_case_live_probe"


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _artifact_gate(artifact: dict[str, Any], *, expected_case_id: str) -> tuple[list[str], dict[str, Any], dict[str, Any]]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "accurate_intake_mvp_live_diagnostic":
        blockers.append(f"unsupported_live_diagnostic_artifact_type:{expected_case_id}")
    if artifact.get("provider_mode") != "live":
        blockers.append(f"provider_mode_not_live:{expected_case_id}")
    if artifact.get("live_invoked") is not True:
        blockers.append(f"live_not_invoked:{expected_case_id}")
    if artifact.get("live_llm_invoked") is not True:
        blockers.append(f"live_llm_not_invoked:{expected_case_id}")
    for flag in REQUIRED_NON_CLAIM_FLAGS:
        if artifact.get(flag) is True:
            blockers.append(f"non_claim_violation:{expected_case_id}:{flag}")

    stages = [_dict(stage) for stage in _list(artifact.get("stages"))]
    stage = stages[0] if len(stages) == 1 else {}
    if not stage:
        blockers.append(f"missing_single_case_stage:{expected_case_id}")
    else:
        if stage.get("stage_id") != REQUIRED_STAGE_ID:
            blockers.append(f"unexpected_stage_id:{expected_case_id}")
        if stage.get("status") != "pass":
            blockers.append(f"single_case_stage_not_pass:{expected_case_id}")
        if stage.get("result_kind") != "strict_pass_first_attempt":
            blockers.append(f"single_case_stage_not_strict_first_attempt:{expected_case_id}")
        if _list(stage.get("case_ids")) != [expected_case_id]:
            blockers.append(f"unexpected_case_ids:{expected_case_id}")

    cases = [_dict(case) for case in _list(artifact.get("cases"))]
    case = cases[0] if len(cases) == 1 else {}
    if not case:
        blockers.append(f"unexpected_case_count:{expected_case_id}")
    else:
        if case.get("case_id") != expected_case_id:
            blockers.append(f"unexpected_case_id:{expected_case_id}")
        if case.get("case_contract_status") != "strict_pass":
            blockers.append(f"case_contract_not_strict_pass:{expected_case_id}")
        if case.get("verdict") != "pass":
            blockers.append(f"case_verdict_not_pass:{expected_case_id}")
        if case.get("failure_layer") is not None:
            blockers.append(f"case_failure_layer_present:{expected_case_id}")
    return blockers, stage, case


def _turn(case: dict[str, Any], turn_number: int) -> dict[str, Any]:
    return next((_dict(turn) for turn in _list(case.get("turns")) if int(_dict(turn).get("turn") or 0) == turn_number), {})


def _live_case_specs(
    *,
    exact_case: dict[str, Any],
    bubble_case: dict[str, Any],
    luwei_case: dict[str, Any],
    no_plan_case: dict[str, Any],
    correction_case: dict[str, Any],
) -> list[dict[str, Any]]:
    exact_turn = _turn(exact_case, 1)
    bubble_turn = _turn(bubble_case, 1)
    luwei_turn = _turn(luwei_case, 1)
    no_plan_turn = _turn(no_plan_case, 1)
    correction_update_turn = _turn(correction_case, 2)
    correction_remove_turn = _turn(correction_case, 3)

    return [
        {
            "case_id": "exact_item_logged_live",
            "family": "logged_estimate",
            "reply_text": str(exact_turn.get("coach_message") or ""),
            "logged_status": "logged",
            "final_action": exact_turn.get("manager_final_action"),
            "expected_kcal": _dict(exact_turn.get("remaining_budget")).get("consumed_kcal"),
            "must_include_kcal": True,
            "must_exclude_macro_visible": True,
            "required_markers": [],
            "forbidden_markers": [],
        },
        {
            "case_id": "generic_logged_live",
            "family": "logged_estimate",
            "reply_text": str(bubble_turn.get("coach_message") or ""),
            "logged_status": "logged",
            "final_action": bubble_turn.get("manager_final_action"),
            "expected_kcal": _dict(bubble_turn.get("remaining_budget")).get("consumed_kcal"),
            "must_include_kcal": True,
            "must_exclude_macro_visible": True,
            "required_markers": [],
            "forbidden_markers": [],
        },
        {
            "case_id": "blocking_clarify_live",
            "family": "blocking_clarify",
            "reply_text": str(luwei_turn.get("coach_message") or ""),
            "logged_status": "",
            "final_action": luwei_turn.get("manager_final_action"),
            "must_exclude_kcal": True,
            "must_include_question": True,
            "must_exclude_macro_visible": True,
            "required_markers": ["滷味"],
            "forbidden_markers": [],
        },
        {
            "case_id": "degraded_budget_live",
            "family": "degraded_budget",
            "reply_text": str(no_plan_turn.get("coach_message") or ""),
            "logged_status": "",
            "final_action": no_plan_turn.get("manager_final_action"),
            "must_exclude_macro_visible": True,
            "required_markers": ["設定", "剩餘"],
            "forbidden_markers": ["Onboarding is required", "Remaining about", "remaining 0 kcal", "remaining 1312 kcal", "剩餘 0"],
        },
        {
            "case_id": "correction_update_live",
            "family": "correction",
            "reply_text": str(correction_update_turn.get("coach_message") or ""),
            "logged_status": "",
            "final_action": correction_update_turn.get("manager_final_action"),
            "expected_kcal": _dict(correction_update_turn.get("remaining_budget")).get("consumed_kcal"),
            "must_include_kcal": True,
            "must_exclude_macro_visible": True,
            "required_markers": [],
            "forbidden_markers": [],
        },
        {
            "case_id": "correction_remove_live",
            "family": "correction",
            "reply_text": str(correction_remove_turn.get("coach_message") or ""),
            "logged_status": "",
            "final_action": correction_remove_turn.get("manager_final_action"),
            "must_exclude_kcal": True,
            "must_exclude_macro_visible": True,
            "required_markers": ["Removed"],
            "forbidden_markers": [],
        },
    ]


def build_rt11b_final_response_quality_live_wall(
    *,
    exact_item_artifact: dict[str, Any],
    bubble_artifact: dict[str, Any],
    luwei_artifact: dict[str, Any],
    no_plan_artifact: dict[str, Any],
    correction_artifact: dict[str, Any],
    output_path: Path | None = None,
) -> dict[str, Any]:
    blockers: list[str] = []

    exact_blockers, exact_stage, exact_case = _artifact_gate(exact_item_artifact, expected_case_id="exact_item_official_label")
    bubble_blockers, bubble_stage, bubble_case = _artifact_gate(bubble_artifact, expected_case_id="bubble_milk_tea_refinement")
    luwei_blockers, luwei_stage, luwei_case = _artifact_gate(luwei_artifact, expected_case_id="luwei_bare_to_listed_basket")
    no_plan_blockers, no_plan_stage, no_plan_case = _artifact_gate(no_plan_artifact, expected_case_id="no_plan_consumed_without_budget_target")
    correction_blockers, correction_stage, correction_case = _artifact_gate(
        correction_artifact,
        expected_case_id="chinese_chicken_rice_correction_removal_debug",
    )
    blockers.extend(
        [
            *exact_blockers,
            *bubble_blockers,
            *luwei_blockers,
            *no_plan_blockers,
            *correction_blockers,
        ]
    )

    live_cases = _live_case_specs(
        exact_case=exact_case,
        bubble_case=bubble_case,
        luwei_case=luwei_case,
        no_plan_case=no_plan_case,
        correction_case=correction_case,
    )

    evaluated_cases = [fixture._evaluate_case(case) for case in live_cases]  # noqa: SLF001
    blockers.extend(f"{case['case_id']}.{blocker}" for case in evaluated_cases for blocker in case["blockers"])

    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "artifact_type": "accurate_intake_rt11b_final_response_quality_live_wall",
        "claim_scope": "final_response_quality_live_wall",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt11b_final_response_quality_live_wall",
        "pass_type": "live_diagnostic",
        "runtime_backed": True,
        "live_llm_invoked": True,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "J", "K"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(evaluated_cases),
            "passed_case_count": sum(1 for case in evaluated_cases if case["status"] == "pass"),
            "required_stage_id": REQUIRED_STAGE_ID,
            "language_locked_to_zh_tw": False,
            "llm_judge_used": False,
        },
        "cases": evaluated_cases,
        "rubric": {
            "must_include": [
                "logged/update status when applicable",
                "kcal when reply claims a committed estimate or correction update",
                "follow-up question for blocking clarify",
                "degraded honesty without invented remaining budget",
            ],
            "must_not_include": [
                "debug/provider/trace leakage",
                "macro grams when macros are not surfaced",
            ],
            "judge_type": "rule_based_live_wall",
            "llm_judge_used": False,
        },
        "source_stages": {
            "exact_item": exact_stage,
            "bubble": bubble_stage,
            "luwei": luwei_stage,
            "no_plan": no_plan_stage,
            "correction": correction_stage,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Build the RT11b final response quality live wall artifact."
    )
    parser.add_argument("--exact-item-artifact", type=Path, required=True)
    parser.add_argument("--bubble-artifact", type=Path, required=True)
    parser.add_argument("--luwei-artifact", type=Path, required=True)
    parser.add_argument("--no-plan-artifact", type=Path, required=True)
    parser.add_argument("--correction-artifact", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT_PATH)
    args = parser.parse_args(argv)

    artifact = build_rt11b_final_response_quality_live_wall(
        exact_item_artifact=json.loads(args.exact_item_artifact.read_text(encoding="utf-8")),
        bubble_artifact=json.loads(args.bubble_artifact.read_text(encoding="utf-8")),
        luwei_artifact=json.loads(args.luwei_artifact.read_text(encoding="utf-8")),
        no_plan_artifact=json.loads(args.no_plan_artifact.read_text(encoding="utf-8")),
        correction_artifact=json.loads(args.correction_artifact.read_text(encoding="utf-8")),
        output_path=args.output,
    )
    write_json_artifact(args.output, artifact)
    print(args.output)
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
