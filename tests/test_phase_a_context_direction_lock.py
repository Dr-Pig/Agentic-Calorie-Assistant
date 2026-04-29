from __future__ import annotations

from types import SimpleNamespace

from app.intake.application.context_injection_policy import (
    build_manager_context_pack,
    default_context_injection_policy,
)
from app.intake.application.current_turn_context_assembler import (
    build_chat_interaction_event,
    build_current_turn_context_v1,
)
from app.intake.application.history_expansion_policy import (
    build_history_expansion_request,
    build_history_expansion_result,
)
from app.intake.application.shadow_hypothesis import (
    advance_shadow_hypothesis,
    build_shadow_hypothesis,
)
from app.runtime.contracts.phase_a import InteractionEvent


def _resolved_state() -> object:
    return SimpleNamespace(
        onboarding_ready=True,
        conversation_state=None,
        injected_context={
            "ACTIVE_MEAL": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "milk tea",
            },
            "PENDING_FOLLOWUP": {
                "is_open": True,
                "meal_id": 10,
                "meal_thread_id": 77,
                "pending_question": "What size was it?",
            },
            "RECENT_COMMITTED_MEALS_SUMMARY": [
                {
                    "meal_thread_id": 77,
                    "meal_version_id": 88,
                    "meal_title": "milk tea",
                }
            ],
            "TARGET_MEAL_REFERENCE": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "milk tea",
                "target_resolution_source": "pending_followup_state",
                "correction_confidence": "high",
            },
            "SESSION_SUMMARY": {
                "latest_assistant_turns": ["What size was it?"],
            },
        },
    )


def test_interaction_event_defaults_surface_mode_from_source() -> None:
    ui_event = InteractionEvent(
        source="ui",
        event_type="edit_item",
        raw_text="change this",
        action_id="edit",
        target_object_type="meal_thread",
        target_object_id="meal-thread-123",
        payload={},
        metadata={},
    )
    chat_event = build_chat_interaction_event(raw_user_input="I ate oatmeal")

    assert ui_event.surface_mode == "ui_anchored_action"
    assert chat_event.surface_mode == "chat_freeform"


def test_build_manager_context_pack_uses_curated_context_and_excludes_trace_only_inputs() -> None:
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=_resolved_state(),
    )

    pack = build_manager_context_pack(
        current_turn_context=current_turn_context,
        recent_transcript_tail=["user: tea", "assistant: what size?", "user: half sugar"],
        verbose_resolver_diagnostics={"candidate_scores": [0.9, 0.2]},
        full_ledger_history=[{"day": "2026-04-29", "consumed_kcal": 900}],
        long_term_memory_blobs=[{"preference": "half sugar"}],
    )

    assert pack.policy == default_context_injection_policy()
    assert set(pack.manager_context.keys()) == {
        "interaction_event",
        "active_meal_thread_ref",
        "pending_followup",
        "candidate_attachment_targets",
    }
    assert set(pack.available_if_needed.keys()) == {
        "recent_committed_meal_refs",
        "last_system_question",
        "open_workflow_type",
    }
    assert "raw_transcript" not in pack.manager_context
    assert "long_term_memory_blobs" not in pack.manager_context
    assert "full_ledger_history" not in pack.manager_context
    assert pack.trace_only["raw_transcript"] == ["user: tea", "assistant: what size?", "user: half sugar"]
    assert pack.not_for_manager["long_term_memory_blobs"] == [{"preference": "half sugar"}]


def test_build_history_expansion_request_uses_wave1_default_budget() -> None:
    request = build_history_expansion_request(
        reason="target_ambiguity",
        scope="recent_meals",
    )

    assert request.reason == "target_ambiguity"
    assert request.scope == "recent_meals"
    assert request.max_results == 5
    assert request.max_atomic_blocks == 5
    assert request.max_transcript_snippets == 2


def test_build_history_expansion_result_prefers_structured_candidates_and_limits_transcript_support() -> None:
    result = build_history_expansion_result(
        meal_candidates=[
            {"meal_thread_id": "1", "label": "breakfast", "reason": "recent"},
            {"meal_thread_id": "2", "label": "lunch", "reason": "recent"},
            {"meal_thread_id": "3", "label": "dinner", "reason": "recent"},
            {"meal_thread_id": "4", "label": "snack", "reason": "recent"},
            {"meal_thread_id": "5", "label": "tea", "reason": "recent"},
            {"meal_thread_id": "6", "label": "dessert", "reason": "recent"},
        ],
        atomic_blocks=[
            {"block_type": "clarification_answer", "summary": "large cup", "object_ref": {"meal_thread_id": "1"}},
            {"block_type": "correction_request", "summary": "not that meal", "object_ref": {"meal_thread_id": "2"}},
        ],
        transcript_snippets=[
            {"snippet_id": "s1", "content": "first snippet"},
            {"snippet_id": "s2", "content": "second snippet"},
            {"snippet_id": "s3", "content": "third snippet"},
        ],
    )

    assert len(result.meal_candidates) == 5
    assert len(result.atomic_blocks) == 2
    assert len(result.transcript_snippets) == 2
    assert all(snippet.role == "support_only" for snippet in result.transcript_snippets)


def test_build_shadow_hypothesis_never_gains_mutation_authority() -> None:
    hypothesis = build_shadow_hypothesis(
        hypothesis_id="shadow-1",
        target_object_type="meal_thread",
        target_object_id="77",
        intent="correction",
        confidence="medium",
        created_from="chat_freeform_guess",
    )

    assert hypothesis.visibility_posture == "uncertainty_visible"
    assert hypothesis.mutation_authority is False


def test_shadow_hypothesis_lifecycle_survives_until_invalidated() -> None:
    hypothesis = build_shadow_hypothesis(
        hypothesis_id="shadow-2",
        target_object_type="meal_thread",
        target_object_id="77",
        intent="followup",
        confidence="high",
        created_from="pending_followup_state",
    )

    assert advance_shadow_hypothesis(hypothesis) == hypothesis
    assert advance_shadow_hypothesis(hypothesis, topic_reset=True) is None
    assert advance_shadow_hypothesis(hypothesis, idle_expired=True) is None
