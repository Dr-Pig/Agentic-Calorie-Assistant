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


DEFAULT_OUTPUT_PATH = ROOT / "artifacts" / "accurate_intake_rt12_trace_grading_v1.json"

_REQUIRED_TRACE_KEYS = (
    "user_utterance",
    "context_packet_id",
    "manager_pass_1",
    "requested_tools",
    "filtered_tool_plan",
    "executed_tools",
    "manager_pass_2",
    "guard_result",
    "final_response_basis",
)
_FORBIDDEN_RESPONSE_CLAIM_TYPES = {"readiness", "self_use_approval", "provider_topology"}


def _status(blockers: list[str]) -> str:
    return "pass" if not blockers else "fail"


def _trace_shape_grade(trace: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key in _REQUIRED_TRACE_KEYS:
        if key not in trace:
            blockers.append(f"trace_shape_missing:{key}")
    return blockers


def _tool_choice_grade(case: dict[str, Any], trace: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if trace.get("requested_tools") != case.get("expected_requested_tools"):
        blockers.append("requested_tools_mismatch")
    if trace.get("filtered_tool_plan") != case.get("expected_filtered_tool_plan"):
        blockers.append("filtered_tool_plan_mismatch")
    if trace.get("executed_tools") != case.get("expected_executed_tools"):
        blockers.append("executed_tools_mismatch")
    return blockers


def _argument_accuracy_grade(case: dict[str, Any], trace: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    tool_arguments = dict(trace.get("tool_arguments") or {})
    expected_arguments = dict(case.get("expected_tool_arguments") or {})
    for tool_name, expected_payload in expected_arguments.items():
        actual_payload = tool_arguments.get(tool_name)
        if not isinstance(actual_payload, dict):
            blockers.append(f"tool_arguments_missing:{tool_name}")
            continue
        for key, expected_value in expected_payload.items():
            if actual_payload.get(key) != expected_value:
                blockers.append(f"tool_argument_mismatch:{tool_name}.{key}")
    return blockers


def _final_response_basis_grade(trace: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    basis = dict(trace.get("final_response_basis") or {})
    allowed_fact_ids = set(basis.get("allowed_fact_ids") or [])
    claims = list(basis.get("claims") or [])
    for claim in claims:
        if not isinstance(claim, dict):
            blockers.append("final_response_basis_claim_not_structured")
            continue
        claim_type = str(claim.get("claim_type") or "")
        fact_id = str(claim.get("fact_id") or "")
        if claim_type in _FORBIDDEN_RESPONSE_CLAIM_TYPES:
            blockers.append(f"forbidden_response_claim:{claim_type}")
        if fact_id and fact_id not in allowed_fact_ids:
            blockers.append(f"response_fact_not_allowed:{fact_id}")
    return blockers


def _evaluate_case(case: dict[str, Any]) -> dict[str, Any]:
    trace = dict(case["trace"])
    blockers = [
        *_trace_shape_grade(trace),
        *_tool_choice_grade(case, trace),
        *_argument_accuracy_grade(case, trace),
        *_final_response_basis_grade(trace),
    ]
    return {
        "case_id": case["case_id"],
        "family": case["family"],
        "status": _status(blockers),
        "blockers": blockers,
        "requested_tools": trace.get("requested_tools"),
        "filtered_tool_plan": trace.get("filtered_tool_plan"),
        "executed_tools": trace.get("executed_tools"),
    }


def _case_specs() -> list[dict[str, Any]]:
    return [
        {
            "case_id": "single_turn_commit_trace_has_complete_tool_and_basis_lineage",
            "family": "single_turn_commit",
            "expected_requested_tools": ["estimate_nutrition", "compare_against_budget"],
            "expected_filtered_tool_plan": ["estimate_nutrition", "compare_against_budget"],
            "expected_executed_tools": ["estimate_nutrition", "compare_against_budget"],
            "expected_tool_arguments": {
                "estimate_nutrition": {"meal_text": "chicken sandwich", "local_date": "2026-05-02"},
                "compare_against_budget": {"local_date": "2026-05-02", "estimated_kcal": 480},
            },
            "trace": {
                "user_utterance": "chicken sandwich",
                "context_packet_id": "ctx-commit-1",
                "manager_pass_1": {"intent": "log_meal"},
                "requested_tools": ["estimate_nutrition", "compare_against_budget"],
                "filtered_tool_plan": ["estimate_nutrition", "compare_against_budget"],
                "executed_tools": ["estimate_nutrition", "compare_against_budget"],
                "tool_arguments": {
                    "estimate_nutrition": {"meal_text": "chicken sandwich", "local_date": "2026-05-02"},
                    "compare_against_budget": {"local_date": "2026-05-02", "estimated_kcal": 480},
                },
                "manager_pass_2": {"final_action": "commit"},
                "guard_result": {"verdict": "pass"},
                "final_response_basis": {
                    "allowed_fact_ids": ["fact-logged", "fact-kcal", "fact-remaining"],
                    "claims": [
                        {"claim_type": "logged_status", "fact_id": "fact-logged"},
                        {"claim_type": "kcal", "fact_id": "fact-kcal"},
                        {"claim_type": "remaining", "fact_id": "fact-remaining"},
                    ],
                },
            },
        },
        {
            "case_id": "optional_refinement_trace_keeps_followup_on_allowed_basis",
            "family": "optional_refinement",
            "expected_requested_tools": ["estimate_nutrition"],
            "expected_filtered_tool_plan": ["estimate_nutrition"],
            "expected_executed_tools": ["estimate_nutrition"],
            "expected_tool_arguments": {
                "estimate_nutrition": {"meal_text": "\u73cd\u73e0\u5976\u8336", "local_date": "2026-05-02"}
            },
            "trace": {
                "user_utterance": "\u6211\u559d\u4e86\u73cd\u73e0\u5976\u8336",
                "context_packet_id": "ctx-refine-1",
                "manager_pass_1": {"intent": "log_meal"},
                "requested_tools": ["estimate_nutrition"],
                "filtered_tool_plan": ["estimate_nutrition"],
                "executed_tools": ["estimate_nutrition"],
                "tool_arguments": {
                    "estimate_nutrition": {"meal_text": "\u73cd\u73e0\u5976\u8336", "local_date": "2026-05-02"}
                },
                "manager_pass_2": {"final_action": "commit_with_followup"},
                "guard_result": {"verdict": "pass"},
                "final_response_basis": {
                    "allowed_fact_ids": ["fact-logged", "fact-kcal", "fact-followup"],
                    "claims": [
                        {"claim_type": "logged_status", "fact_id": "fact-logged"},
                        {"claim_type": "kcal", "fact_id": "fact-kcal"},
                        {"claim_type": "followup", "fact_id": "fact-followup"},
                    ],
                },
            },
        },
        {
            "case_id": "blocking_clarify_trace_can_grade_no_tool_answer_path",
            "family": "blocking_clarify",
            "expected_requested_tools": [],
            "expected_filtered_tool_plan": [],
            "expected_executed_tools": [],
            "expected_tool_arguments": {},
            "trace": {
                "user_utterance": "\u6211\u5403\u4e86\u6ef7\u5473",
                "context_packet_id": "ctx-clarify-1",
                "manager_pass_1": {"intent": "log_meal"},
                "requested_tools": [],
                "filtered_tool_plan": [],
                "executed_tools": [],
                "tool_arguments": {},
                "manager_pass_2": {"final_action": "ask_followup"},
                "guard_result": {"verdict": "answer_only"},
                "final_response_basis": {
                    "allowed_fact_ids": ["fact-not-logged", "fact-followup"],
                    "claims": [
                        {"claim_type": "logged_status", "fact_id": "fact-not-logged"},
                        {"claim_type": "followup", "fact_id": "fact-followup"},
                    ],
                },
            },
        },
        {
            "case_id": "degraded_budget_trace_grades_read_tool_and_response_basis",
            "family": "degraded_budget",
            "expected_requested_tools": ["budget.get_remaining_calories", "body.get_active_plan"],
            "expected_filtered_tool_plan": ["budget.get_remaining_calories", "body.get_active_plan"],
            "expected_executed_tools": ["budget.get_remaining_calories", "body.get_active_plan"],
            "expected_tool_arguments": {
                "budget.get_remaining_calories": {"local_date": "2026-05-02"},
                "body.get_active_plan": {"local_date": "2026-05-02"},
            },
            "trace": {
                "user_utterance": "\u6211\u4eca\u5929\u9084\u5269\u591a\u5c11\u71b1\u91cf\uff1f",
                "context_packet_id": "ctx-budget-1",
                "manager_pass_1": {"intent": "query_remaining_budget"},
                "requested_tools": ["budget.get_remaining_calories", "body.get_active_plan"],
                "filtered_tool_plan": ["budget.get_remaining_calories", "body.get_active_plan"],
                "executed_tools": ["budget.get_remaining_calories", "body.get_active_plan"],
                "tool_arguments": {
                    "budget.get_remaining_calories": {"local_date": "2026-05-02"},
                    "body.get_active_plan": {"local_date": "2026-05-02"},
                },
                "manager_pass_2": {"final_action": "answer_only_degraded"},
                "guard_result": {"verdict": "answer_only"},
                "final_response_basis": {
                    "allowed_fact_ids": ["fact-budget-status", "fact-remaining-status"],
                    "claims": [
                        {"claim_type": "budget_status", "fact_id": "fact-budget-status"},
                        {"claim_type": "remaining_status", "fact_id": "fact-remaining-status"},
                    ],
                },
            },
        },
    ]


def build_rt12_trace_grading_v1_artifact(
    *,
    output_path: Path | None = None,
) -> dict[str, Any]:
    cases = [_evaluate_case(case) for case in _case_specs()]
    blockers = [f"{case['case_id']}.{blocker}" for case in cases for blocker in case["blockers"]]
    resolved_output_path = Path(output_path) if output_path is not None else DEFAULT_OUTPUT_PATH
    return {
        "artifact_schema_version": "1.0",
        "artifact_name": resolved_output_path.name,
        "artifact_path": str(resolved_output_path),
        "claim_scope": "trace_grading_v1_fixture_gate",
        "launch_scope": "current_shell_v1",
        "producer_track": "CurrentShell/ManagerRuntime",
        "target_manager_runtime_gate": "rt12_trace_grading_v1",
        "pass_type": "fixture",
        "runtime_backed": False,
        "live_llm_invoked": False,
        "production_db_used": False,
        "fooddb_truth_updated": False,
        "supports_journeys": ["B", "C", "D", "J"],
        "status": _status(blockers),
        "blockers": blockers,
        "summary": {
            "case_count": len(cases),
            "passed_case_count": sum(1 for case in cases if case["status"] == "pass"),
        },
        "cases": cases,
        "grade_layers": [
            "trace_shape",
            "tool_choice",
            "argument_accuracy",
            "final_response_basis",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build the RT12 trace grading v1 artifact.")
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Where to write the JSON artifact.",
    )
    args = parser.parse_args(argv)
    artifact = build_rt12_trace_grading_v1_artifact(output_path=args.output)
    write_json_artifact(args.output, artifact)
    print(json.dumps(artifact, ensure_ascii=False, indent=2))
    return 0 if artifact["status"] == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
