from __future__ import annotations

from types import SimpleNamespace

from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.shadow_hypothesis_runtime import build_shadow_hypothesis_runtime
from app.runtime.contracts.phase_a import AttachmentDecision, InteractionEvent, TransitionGuardResult


def _state(*, pending_followup: bool = False, recent_meals: list[dict[str, object]] | None = None) -> object:
    return SimpleNamespace(
        onboarding_ready=True,
        user_id=1,
        user_external_id="user-1",
        local_date="2026-04-29",
        active_body_plan_view=None,
        current_budget_view=None,
        conversation_state=None,
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
                "is_open": pending_followup,
                "meal_id": 10 if pending_followup else None,
                "meal_thread_id": 77 if pending_followup else None,
                "pending_question": "What size was it?" if pending_followup else None,
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": recent_meals
            if recent_meals is not None
            else [
                {
                    "meal_thread_id": 77,
                    "meal_version_id": 88,
                    "meal_title": "milk tea",
                    "local_date": "2026-04-29",
                }
            ],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": None,
                "meal_version_id": None,
                "meal_title": None,
                "target_resolution_source": "none",
                "correction_confidence": "low",
            },
            "SESSION_SUMMARY": {},
        },
    )


def _answer_only_attachment() -> AttachmentDecision:
    return AttachmentDecision(
        disposition="answer_only",
        target_object_type="none",
        target_object_id=None,
        reason="no_attachment_signal",
        confidence="low",
        ambiguity_flag=True,
        allowed_transition_class="none",
    )


def _answer_only_guard() -> TransitionGuardResult:
    return TransitionGuardResult(
        verdict="answer_only",
        reason="no_state_mutation_allowed",
        blocked_mutation="meal_mutation",
        affected_object_type="none",
        affected_object_id=None,
    )


def test_shadow_runtime_builds_non_authoritative_payload_for_single_plausible_chat_candidate() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=_state(),
    )

    result = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=_answer_only_attachment(),
        transition_guard_result=_answer_only_guard(),
    )

    assert result.created is True
    assert result.manager_payload is not None
    assert result.manager_payload["role"] == "tentative_non_authoritative"
    assert result.manager_payload["mutation_authority"] is False
    assert result.manager_payload["candidate_target_object_id"] == "77"
    assert result.manager_payload["candidate_intent"] == "back_reference"
    assert "target_object_id" not in result.manager_payload
    assert result.trace_payload()["created"] is True
    assert result.trace_payload()["candidate_target_object_id"] == "77"


def test_shadow_runtime_skips_explicit_ui_target() -> None:
    event = InteractionEvent(
        source="ui",
        surface_mode="ui_anchored_action",
        event_type="edit_item",
        raw_text="half sugar",
        target_object_type="meal_thread",
        target_object_id="77",
    )
    context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=_state(),
        interaction_event=event,
    )

    result = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=_answer_only_attachment(),
        transition_guard_result=_answer_only_guard(),
    )

    assert result.created is False
    assert result.skip_reason == "explicit_ui_target"
    assert result.manager_payload is None


def test_shadow_runtime_skips_resolved_pending_followup() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=_state(pending_followup=True),
    )
    attachment = AttachmentDecision(
        disposition="attach_existing_thread",
        target_object_type="meal_thread",
        target_object_id="77",
        reason="pending_followup_answer",
        confidence="high",
        ambiguity_flag=False,
        allowed_transition_class="interpretation_update",
    )
    guard = TransitionGuardResult(
        verdict="pass",
        reason="phase_a_attachment_allowed",
        affected_object_type="meal_thread",
        affected_object_id="77",
    )

    result = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=attachment,
        transition_guard_result=guard,
    )

    assert result.created is False
    assert result.skip_reason == "resolved_pending_followup"


def test_shadow_runtime_skips_multiple_plausible_targets() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=_state(
            recent_meals=[
                {
                    "meal_thread_id": 77,
                    "meal_version_id": 88,
                    "meal_title": "milk tea",
                    "local_date": "2026-04-29",
                },
                {
                    "meal_thread_id": 78,
                    "meal_version_id": 89,
                    "meal_title": "milk tea",
                    "local_date": "2026-04-29",
                },
            ]
        ),
    )

    result = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=_answer_only_attachment(),
        transition_guard_result=_answer_only_guard(),
    )

    assert result.created is False
    assert result.skip_reason == "multiple_plausible_targets"


def test_shadow_runtime_does_not_change_attachment_or_guard_verdicts() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="that milk tea half sugar",
        resolved_state=_state(),
    )
    attachment = _answer_only_attachment()
    guard = _answer_only_guard()
    attachment_before = attachment.model_dump(mode="json")
    guard_before = guard.model_dump(mode="json")

    result = build_shadow_hypothesis_runtime(
        current_turn_context=context,
        attachment_decision=attachment,
        transition_guard_result=guard,
    )

    assert result.created is True
    assert attachment.model_dump(mode="json") == attachment_before
    assert guard.model_dump(mode="json") == guard_before
    assert result.current_turn_context.model_dump(mode="json") == context.model_dump(mode="json")
