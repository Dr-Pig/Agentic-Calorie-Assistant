from __future__ import annotations

from app.nutrition.application.followup_policy import annotate_followup_policy
from app.runtime.infrastructure.trace.payload_builders import build_payload
from app.schemas import EstimateRequest


def _parsed(**overrides: object) -> dict[str, object]:
    parsed: dict[str, object] = {
        "title": "pearl milk tea",
        "components": ["milk tea", "pearls"],
        "protein_g": 3,
        "carb_g": 80,
        "fat_g": 8,
        "estimated_kcal": 450,
        "uncertainty_factors": ["size and sugar unknown"],
        "followup_question": "What size and sugar level was it?",
        "follow_up_needed": True,
        "response_mode_hint": "rough_estimate_ok",
        "unresolved_info": [],
        "blocking_slots": [],
    }
    parsed.update(overrides)
    return parsed


def test_payload_source_decision_does_not_treat_followup_as_ask_user_gate() -> None:
    payload = build_payload(
        EstimateRequest(text="I had a pearl milk tea"),
        request_id="req-followup",
        parsed=_parsed(),
        risk_packet={},
        action_taken="answer_with_uncertainty",
        route_target="direct_answer",
        route_reason="manager_estimate_with_refinement",
        debug_steps=[],
        llm_traces=[],
        retrieval_triggered=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        quality_signals={},
        retry_triggered=False,
        retry_reason=None,
        best_answer_source="llm",
        private_only=False,
        used_search=False,
        search_query=None,
        search_quality=None,
        sources=[],
    )

    assert payload.source_decision == "ready"
    assert payload.follow_up_needed is True
    assert payload.followup_question == "What size and sugar level was it?"


def test_payload_source_decision_keeps_clarify_first_as_ask_user_gate() -> None:
    payload = build_payload(
        EstimateRequest(text="I had luwei"),
        request_id="req-clarify",
        parsed=_parsed(response_mode_hint="clarify_first", blocking_slots=["item_identity"]),
        risk_packet={},
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        route_reason="blocking_slot",
        debug_steps=[],
        llm_traces=[],
        retrieval_triggered=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        quality_signals={},
        retry_triggered=False,
        retry_reason=None,
        best_answer_source="llm",
        private_only=False,
        used_search=False,
        search_query=None,
        search_quality=None,
        sources=[],
    )

    assert payload.source_decision == "ask_user"


def test_followup_projection_preserves_manager_followup_flag() -> None:
    parsed = annotate_followup_policy(
        dict(
            _parsed(
                follow_up_needed=False,
                followup_question="Optional: what size and sugar level was it?",
            ),
            reasoning_state={},
        )
    )

    assert parsed["follow_up_needed"] is False
    assert parsed["followup_question"] == "Optional: what size and sugar level was it?"
    assert parsed["followup_decision_type"] == "direct_answer"
    assert parsed["followup_policy_source"] == "structured_manager_fields_only"


def test_followup_projection_preserves_followup_flag_without_question() -> None:
    parsed = annotate_followup_policy(
        dict(
            _parsed(
                follow_up_needed=True,
                followup_question="",
                missing_slots=[],
            ),
            reasoning_state={},
        )
    )

    assert parsed["follow_up_needed"] is True
    assert parsed["followup_question"] == ""
    assert parsed["followup_decision_type"] == "estimate_with_followup"


def test_followup_projection_does_not_default_clarify_first_from_followup_question() -> None:
    projected = annotate_followup_policy(
        {
            "estimated_kcal": 450,
            "followup_question": "What size and sugar level was it?",
            "follow_up_needed": True,
            "response_mode_hint": "rough_estimate_ok",
            "action_taken": "answer_with_uncertainty",
            "reasoning_state": {},
        }
    )

    assert projected["followup_question"] == "What size and sugar level was it?"
    assert projected["follow_up_needed"] is True
    assert projected["action_taken"] == "answer_with_uncertainty"
    assert projected["response_mode_hint"] == "rough_estimate_ok"
    assert projected["followup_decision_type"] == "estimate_with_followup"


def test_followup_projection_preserves_explicit_clarify_first_blocker() -> None:
    projected = annotate_followup_policy(
        {
            "estimated_kcal": 0,
            "followup_question": "Which items and portions?",
            "follow_up_needed": True,
            "action_taken": "clarify_before_estimate",
            "response_mode_hint": "clarify_first",
            "blocking_slots": ["item_identity"],
            "reasoning_state": {},
        }
    )

    assert projected["action_taken"] == "clarify_before_estimate"
    assert projected["response_mode_hint"] == "clarify_first"
    assert projected["blocking_slots"] == ["item_identity"]
    assert projected["followup_decision_type"] == "ask_followup_only"
