from __future__ import annotations

import json
from pathlib import Path


def test_rt12_trace_grading_v1_artifact_passes_fixture_wall() -> None:
    from scripts import run_accurate_intake_rt12_trace_grading_v1 as module

    artifact = module.build_rt12_trace_grading_v1_artifact()

    assert artifact["status"] == "pass"
    assert artifact["target_manager_runtime_gate"] == "rt12_trace_grading_v1"
    assert artifact["pass_type"] == "fixture"
    assert artifact["runtime_backed"] is False
    assert artifact["summary"]["case_count"] == 4
    assert artifact["grade_layers"] == [
        "trace_shape",
        "tool_choice",
        "argument_accuracy",
        "final_response_basis",
    ]


def test_rt12_evaluator_blocks_missing_trace_shape_and_wrong_tool_args() -> None:
    from scripts import run_accurate_intake_rt12_trace_grading_v1 as module

    case = module._evaluate_case(  # noqa: SLF001
        {
            "case_id": "bad-trace",
            "family": "single_turn_commit",
            "expected_requested_tools": ["estimate_nutrition"],
            "expected_filtered_tool_plan": ["estimate_nutrition"],
            "expected_executed_tools": ["estimate_nutrition"],
            "expected_tool_arguments": {
                "estimate_nutrition": {"meal_text": "tea egg", "local_date": "2026-05-02"}
            },
            "trace": {
                "user_utterance": "tea egg",
                "context_packet_id": "ctx-bad",
                "manager_pass_1": {"intent": "log_meal"},
                "requested_tools": ["estimate_nutrition"],
                "filtered_tool_plan": ["estimate_nutrition"],
                "executed_tools": ["estimate_nutrition"],
                "tool_arguments": {"estimate_nutrition": {"meal_text": "tea egg", "local_date": "2026-05-03"}},
                "guard_result": {"verdict": "pass"},
                "final_response_basis": {
                    "allowed_fact_ids": ["fact-logged"],
                    "claims": [{"claim_type": "logged_status", "fact_id": "fact-logged"}],
                },
            },
        }
    )

    assert case["status"] == "fail"
    assert "trace_shape_missing:manager_pass_2" in case["blockers"]
    assert "tool_argument_mismatch:estimate_nutrition.local_date" in case["blockers"]


def test_rt12_evaluator_blocks_final_response_basis_drift() -> None:
    from scripts import run_accurate_intake_rt12_trace_grading_v1 as module

    case = module._evaluate_case(  # noqa: SLF001
        {
            "case_id": "bad-basis",
            "family": "blocking_clarify",
            "expected_requested_tools": [],
            "expected_filtered_tool_plan": [],
            "expected_executed_tools": [],
            "expected_tool_arguments": {},
            "trace": {
                "user_utterance": "bare basket",
                "context_packet_id": "ctx-basis",
                "manager_pass_1": {"intent": "log_meal"},
                "requested_tools": [],
                "filtered_tool_plan": [],
                "executed_tools": [],
                "tool_arguments": {},
                "manager_pass_2": {"final_action": "ask_followup"},
                "guard_result": {"verdict": "answer_only"},
                "final_response_basis": {
                    "allowed_fact_ids": ["fact-followup"],
                    "claims": [
                        {"claim_type": "logged_status", "fact_id": "fact-not-allowed"},
                        {"claim_type": "readiness", "fact_id": "fact-followup"},
                    ],
                },
            },
        }
    )

    assert case["status"] == "fail"
    assert "response_fact_not_allowed:fact-not-allowed" in case["blockers"]
    assert "forbidden_response_claim:readiness" in case["blockers"]


def test_rt12_cli_writes_artifact(tmp_path: Path) -> None:
    from scripts import run_accurate_intake_rt12_trace_grading_v1 as module

    output_path = tmp_path / "accurate_intake_rt12_trace_grading_v1.json"
    exit_code = module.main(["--output", str(output_path)])

    assert exit_code == 0
    artifact = json.loads(output_path.read_text(encoding="utf-8"))
    assert artifact["status"] == "pass"
    assert artifact["artifact_name"] == "accurate_intake_rt12_trace_grading_v1.json"
