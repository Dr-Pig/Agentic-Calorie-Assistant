from __future__ import annotations

from types import SimpleNamespace

from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent
from app.intake.application.attachment_resolver import resolve_attachment_decision
from app.intake.application.current_turn_context_assembler import (
    build_chat_interaction_event,
    build_current_turn_context_v1,
)
from app.intake.application.transition_guard import resolve_transition_guard


def _resolved_state(
    *,
    active_meal: dict[str, object] | None = None,
    pending_followup: dict[str, object] | None = None,
    recent_committed_meals: list[dict[str, object]] | None = None,
    target_meal_reference: dict[str, object] | None = None,
    session_summary: dict[str, object] | None = None,
    conversation_state: object | None = None,
) -> object:
    return SimpleNamespace(
        user_external_id="phase-a-user",
        user_id=1,
        local_date="2026-04-29",
        active_meal=active_meal,
        conversation_state=conversation_state,
        injected_context={
            "ACTIVE_MEAL": active_meal,
            "PENDING_FOLLOWUP": pending_followup
            if pending_followup is not None
            else {
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": recent_committed_meals or [],
            "TARGET_MEAL_REFERENCE": target_meal_reference
            if target_meal_reference is not None
            else {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": session_summary if session_summary is not None else {},
        },
    )


def test_build_current_turn_context_v1_maps_repo_truth_context_into_current_turn_surface() -> None:
    active_meal = {
        "meal_thread_id": 77,
        "meal_version_id": 88,
        "meal_title": "chicken rice",
        "occurred_at": "2026-04-29T08:00:00",
    }
    pending_followup = {
        "is_open": True,
        "meal_id": 10,
        "meal_thread_id": 77,
        "pending_question": "What portion was it?",
    }
    recent_committed_meals = [
        {
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "meal_title": "chicken rice",
            "occurred_at": "2026-04-29T08:00:00",
        }
    ]
    target_meal_reference = {
        "meal_thread_id": 77,
        "meal_version_id": 88,
        "meal_title": "chicken rice",
        "target_resolution_source": "pending_followup_state",
        "correction_confidence": "high",
    }
    session_summary = {
        "latest_assistant_turns": ["What portion was it?"],
    }

    context = build_current_turn_context_v1(
        raw_user_input="half bowl of rice",
        resolved_state=_resolved_state(
            active_meal=active_meal,
            pending_followup=pending_followup,
            recent_committed_meals=recent_committed_meals,
            target_meal_reference=target_meal_reference,
            session_summary=session_summary,
        ),
    )

    assert isinstance(context, CurrentTurnContextV1)
    assert context.user_utterance == "half bowl of rice"
    assert context.last_system_question == "What portion was it?"
    assert context.active_meal_thread_ref["meal_thread_id"] == 77
    assert context.pending_followup["meal_thread_id"] == 77
    assert context.recent_committed_meal_refs[0]["meal_thread_id"] == 77
    assert context.open_workflow_type == "meal_followup"
    assert context.source_views["pending_followup"].availability == "present"
    assert context.source_views["pending_followup"].owner == "conversation_state/intake_followup_read_model"
    assert context.source_views["last_system_question"].availability == "present"


def test_build_current_turn_context_v1_preserves_unknown_vs_none() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="hello",
        resolved_state=_resolved_state(
            active_meal=None,
            pending_followup={
                "is_open": False,
                "meal_id": None,
                "meal_thread_id": None,
                "pending_question": None,
            },
            recent_committed_meals=[],
            target_meal_reference={
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            session_summary={},
            conversation_state=None,
        ),
    )

    assert context.pending_followup is None
    assert context.source_views["pending_followup"].availability == "none"
    assert context.last_system_question is None
    assert context.source_views["last_system_question"].availability == "unknown"


def test_resolve_attachment_decision_attaches_pending_followup_answers_to_existing_thread() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="half bowl of rice",
        resolved_state=_resolved_state(
            active_meal={"meal_thread_id": 77, "meal_version_id": 88, "meal_title": "chicken rice"},
            pending_followup={
                "is_open": True,
                "meal_id": 10,
                "meal_thread_id": 77,
                "pending_question": "What portion was it?",
            },
            target_meal_reference={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "chicken rice",
                "target_resolution_source": "pending_followup_state",
                "correction_confidence": "high",
            },
        ),
    )

    decision = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, decision)

    assert decision.disposition == "attach_existing_thread"
    assert decision.target_object_type == "meal_thread"
    assert decision.target_object_id == "77"
    assert decision.allowed_transition_class == "interpretation_update"
    assert decision.ambiguity_flag is False
    assert guard.verdict == "pass"


def test_resolve_attachment_decision_targets_recent_committed_meal_for_correction() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="actually change that meal to a half bowl",
        resolved_state=_resolved_state(
            recent_committed_meals=[
                {
                    "meal_thread_id": 55,
                    "meal_version_id": 56,
                    "meal_title": "beef bowl",
                    "occurred_at": "2026-04-28T19:00:00",
                }
            ],
            target_meal_reference={
                "meal_thread_id": 55,
                "meal_version_id": 56,
                "meal_title": "beef bowl",
                "target_resolution_source": "active_meal_view",
                "correction_confidence": "high",
            },
        ),
    )

    decision = resolve_attachment_decision(context)

    assert decision.disposition == "target_committed_thread"
    assert decision.target_object_type == "meal_thread"
    assert decision.target_object_id == "55"
    assert decision.allowed_transition_class == "interpretation_update"


def test_current_turn_context_uses_resolved_target_reference_not_correction_keywords() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=_resolved_state(
            target_meal_reference={
                "meal_thread_id": 55,
                "meal_version_id": 56,
                "meal_title": "milk tea",
                "target_resolution_source": "history_expansion",
                "correction_confidence": "high",
            },
        ),
    )

    assert context.open_workflow_type == "meal_correction"


def test_resolve_attachment_decision_routes_ambiguous_turns_to_answer_only() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="ok",
        resolved_state=_resolved_state(),
    )

    decision = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, decision)

    assert decision.disposition == "answer_only"
    assert decision.ambiguity_flag is True
    assert guard.verdict == "answer_only"


def test_resolve_attachment_decision_does_not_keyword_route_new_workflows() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="ignore that, I ate an egg",
        resolved_state=_resolved_state(),
    )

    decision = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, decision)

    assert decision.disposition == "answer_only"
    assert decision.target_object_id is None
    assert decision.reason == "no_attachment_signal"
    assert guard.verdict == "answer_only"


def test_resolve_attachment_decision_honors_explicit_ui_target_identity() -> None:
    interaction_event = InteractionEvent(
        source="ui",
        event_type="edit_item",
        raw_text="ok",
        action_id="edit-latest-meal",
        target_object_type="meal_thread",
        target_object_id="meal-thread-123",
        occurred_at="2026-04-29T09:30:00Z",
        payload={},
        metadata={},
    )
    context = build_current_turn_context_v1(
        raw_user_input="ok",
        resolved_state=_resolved_state(),
        interaction_event=interaction_event,
    )

    decision = resolve_attachment_decision(context)

    assert decision.disposition == "attach_existing_thread"
    assert decision.target_object_type == "meal_thread"
    assert decision.target_object_id == "meal-thread-123"
    assert decision.reason == "explicit_interaction_target"


def test_build_chat_interaction_event_uses_chat_shape() -> None:
    event = build_chat_interaction_event(raw_user_input="I ate oatmeal")

    assert isinstance(event, InteractionEvent)
    assert event.source == "chat"
    assert event.event_type == "user_message"
    assert event.raw_text == "I ate oatmeal"
    assert event.target_object_type == "none"
