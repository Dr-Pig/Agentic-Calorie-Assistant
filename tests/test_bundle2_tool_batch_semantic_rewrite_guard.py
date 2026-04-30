from __future__ import annotations

from app.composition.intake_manager_tool_batch import apply_final_action_to_payload
from app.shared.contracts.intake_results import EstimatePayload


def test_commit_final_action_does_not_rewrite_followup_or_route_semantics() -> None:
    payload = EstimatePayload(
        request_id="req-semantic-rewrite",
        meal_title="pearl milk tea",
        estimated_kcal=400,
        action_taken="answer_with_uncertainty",
        route_target="clarify_user_private",
        follow_up_needed=True,
        followup_question="What size and sugar level was it?",
        trace_contract={
            "followup_question": "What size and sugar level was it?",
            "unresolved_info": ["size", "sugar_level"],
        },
    )

    apply_final_action_to_payload(
        payload=payload,
        raw_user_input="pearl milk tea",
        final_action="commit",
    )

    assert payload.route_target == "clarify_user_private"
    assert payload.action_taken == "answer_with_uncertainty"
    assert payload.follow_up_needed is True
    assert payload.followup_question == "What size and sugar level was it?"
    assert payload.trace_contract["followup_question"] == "What size and sugar level was it?"
    assert payload.trace_contract["unresolved_info"] == ["size", "sugar_level"]


def test_manager_owned_followup_projection_does_not_rewrite_route_semantics() -> None:
    payload = EstimatePayload(
        request_id="req-manager-followup",
        meal_title="pearl milk tea",
        estimated_kcal=400,
        action_taken="direct_answer",
        route_target="direct_answer",
        follow_up_needed=False,
        followup_question=None,
        trace_contract={},
    )

    apply_final_action_to_payload(
        payload=payload,
        raw_user_input="pearl milk tea",
        final_action="commit",
        manager_answer_contract={"followup_question": "What size and sugar level was it?"},
        manager_semantic_decision={"followup_posture": "precision_refinement"},
    )

    assert payload.route_target == "direct_answer"
    assert payload.action_taken == "direct_answer"
    assert payload.follow_up_needed is True
    assert payload.followup_question == "What size and sugar level was it?"
    assert payload.trace_contract["manager_followup_projection"]["source"] == "manager_answer_contract"
    assert payload.trace_contract["manager_followup_projection"]["deterministic_role"] == "projection_only_no_followup_creation"
