from __future__ import annotations

from app.advanced_shadow_lab.context_engineering_final_response_boundary import (
    build_context_engineering_final_response_boundary_grade,
    final_response_boundary_blockers,
)
from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)


def test_final_response_boundary_separates_facts_proposals_and_claim_limits() -> None:
    grade = build_context_engineering_final_response_boundary_grade(
        case_id="ce-stress-001",
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert grade["artifact_type"] == "advanced_product_lab_final_response_boundary_grade"
    assert grade["status"] == "pass"
    assert grade["case_id"] == "ce-stress-001"
    assert grade["recorded_fact_capabilities"] == ["intake", "query"]
    assert grade["proposal_capabilities"] == ["rescue", "recommendation"]
    assert grade["pending_context_capabilities"] == []
    assert "logged_when_not_committed" in grade["must_not_claim"]
    assert "budget_changed_until_acceptance" in grade["must_not_claim"]
    assert grade["tool_names_exposed_to_user"] is False
    assert grade["served_to_mainline_user"] is False
    assert grade["canonical_product_mutation_allowed"] is False
    assert grade["blockers"] == []


def test_final_response_boundary_blocks_hidden_mutation_or_delivery_claims() -> None:
    blockers = final_response_boundary_blockers(
        {
            "claim_flags": {
                "logged_when_not_committed": True,
                "scheduled_when_not_sent": True,
            },
            "tool_names_exposed_to_user": False,
        }
    )

    assert blockers == [
        "final_response.claim_forbidden:logged_when_not_committed",
        "final_response.claim_forbidden:scheduled_when_not_sent",
    ]


def test_final_response_boundary_allows_no_op_answer_without_tool_claims() -> None:
    grade = build_context_engineering_final_response_boundary_grade(
        case_id="ce-stress-024",
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert grade["status"] == "pass"
    assert grade["recorded_fact_capabilities"] == []
    assert grade["proposal_capabilities"] == []
    assert grade["no_op_answer"] is True
