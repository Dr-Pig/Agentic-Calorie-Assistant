from __future__ import annotations

from app.intake.application.intake_tool_runtime import normalize_live_payload
from app.shared.contracts.intake_results import EstimatePayload


def test_normalize_live_payload_does_not_rewrite_manager_semantic_fields() -> None:
    payload = EstimatePayload(
        request_id="req-normalize-live",
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

    normalize_live_payload(
        payload,
        raw_user_input="pearl milk tea",
        family_rule="generic_milk_tea",
        high_variance=True,
    )

    assert payload.route_target == "clarify_user_private"
    assert payload.action_taken == "answer_with_uncertainty"
    assert payload.follow_up_needed is True
    assert payload.followup_question == "What size and sugar level was it?"
    assert payload.trace_contract["followup_question"] == "What size and sugar level was it?"
    assert payload.trace_contract["unresolved_info"] == ["size", "sugar_level"]


def test_normalize_live_payload_preserves_direct_answer_semantics_without_upgrade() -> None:
    payload = EstimatePayload(
        request_id="req-normalize-direct",
        meal_title="tea egg",
        estimated_kcal=80,
        action_taken="answer_with_uncertainty",
        route_target="clarify_user_private",
        follow_up_needed=False,
        followup_question="",
        trace_contract={},
    )

    normalize_live_payload(payload, raw_user_input="tea egg")

    assert payload.route_target == "clarify_user_private"
    assert payload.action_taken == "answer_with_uncertainty"
    assert payload.follow_up_needed is False
    assert payload.followup_question == ""
