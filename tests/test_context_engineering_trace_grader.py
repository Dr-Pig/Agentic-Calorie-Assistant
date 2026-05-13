from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_trace_grader import (
    grade_context_engineering_trace,
    grade_manager_turn_plan_for_case,
)
from app.advanced_shadow_lab.context_engineering_case_loader import (
    load_context_engineering_golden_set,
)


def test_context_engineering_trace_grader_accepts_visible_omission_and_block_boundaries() -> None:
    grade = grade_context_engineering_trace(
        {
            "capabilities_considered": ["intake", "rescue", "recommendation"],
            "capabilities_invoked": ["intake", "rescue"],
            "capabilities_omitted": ["proactive"],
            "blocked_tools": ["proactive.run"],
            "response_claim_boundary": ["must_not_claim_committed_when_only_proposed"],
        }
    )

    assert grade["artifact_type"] == "advanced_product_lab_context_engineering_trace_grade"
    assert grade["status"] == "pass"
    assert grade["blockers"] == []


def test_context_engineering_trace_grader_blocks_hidden_omission_and_claim_boundaries() -> None:
    grade = grade_context_engineering_trace(
        {
            "capabilities_considered": ["query", "memory"],
            "capabilities_invoked": ["query"],
        }
    )

    assert grade["status"] == "blocked"
    assert "capabilities_omitted_visible" in grade["blockers"]
    assert "blocked_tools_visible" in grade["blockers"]
    assert "response_claim_boundary_visible" in grade["blockers"]


def test_manager_turn_plan_grader_accepts_required_tools_order_and_boundaries() -> None:
    case = _case("ce-stress-001")
    grade = grade_manager_turn_plan_for_case(
        case,
        {
            "case_id": "ce-stress-001",
            "capability_requests": [
                _request("intake", "intake.run", {"intake_manager_result": _intake_result()}),
                _request("query", "query.run", {}),
                _request("rescue", "rescue.run", {}),
                _request("recommendation", "recommendation.run", {}),
            ],
            "omission_trace": [{"capability": "proactive", "reason": "forbidden_by_case"}],
            "mutation_posture": "intake_contract_result_and_rescue_proposal_only",
            "canonical_product_mutation_allowed": False,
            "final_response_boundary": ["recorded_vs_proposed_state_must_be_visible"],
        },
    )

    assert grade["artifact_type"] == "advanced_product_lab_manager_turn_plan_grade"
    assert grade["status"] == "pass"
    assert grade["case_id"] == "ce-stress-001"
    assert grade["required_capability_count"] == 4
    assert grade["forbidden_capability_count"] == 0
    assert grade["ordering_constraints_checked"] == [
        "intake_before_query",
        "query_before_rescue",
        "rescue_before_recommendation",
    ]
    assert grade["blockers"] == []


def test_manager_turn_plan_grader_blocks_forbidden_tools_order_and_argument_drift() -> None:
    case = _case("ce-stress-001")
    grade = grade_manager_turn_plan_for_case(
        case,
        {
            "case_id": "ce-stress-001",
            "capability_requests": [
                _request("query", "query.run", {}),
                _request("intake", "intake.run", {}),
                _request("proactive", "proactive.run", {}),
            ],
            "omission_trace": [],
            "mutation_posture": "ledger_commit",
            "canonical_product_mutation_allowed": True,
            "final_response_boundary": [],
        },
    )

    assert grade["status"] == "blocked"
    assert "required_capability.missing:rescue" in grade["blockers"]
    assert "required_capability.missing:recommendation" in grade["blockers"]
    assert "forbidden_capability.invoked:proactive" in grade["blockers"]
    assert "ordering.intake_before_query.violated" in grade["blockers"]
    assert "intake.arguments.intake_manager_result_missing" in grade["blockers"]
    assert "mutation_posture.expected_intake_contract_result_and_rescue_proposal_only_actual_ledger_commit" in grade["blockers"]
    assert "canonical_product_mutation_allowed_true" in grade["blockers"]
    assert "final_response_boundary.missing" in grade["blockers"]


def _case(case_id: str) -> dict[str, object]:
    cases = load_context_engineering_golden_set()["cases"]
    return next(case for case in cases if case["case_id"] == case_id)


def _request(capability: str, tool_name: str, arguments: dict[str, object]) -> dict[str, object]:
    return {
        "capability": capability,
        "tool_name": tool_name,
        "arguments": arguments,
        "call_id": f"{capability}-1",
    }


def _intake_result() -> dict[str, object]:
    return {
        "intent": "log_meal",
        "manager_action": "final",
        "final_action": "commit",
        "workflow_effect": "meal_logged",
    }
