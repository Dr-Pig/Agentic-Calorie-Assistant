from __future__ import annotations

from types import SimpleNamespace

from app.intake.application.attachment_resolver import resolve_attachment_decision
from app.intake.application.current_turn_context_assembler import build_current_turn_context_v1
from app.intake.application.history_expansion_runtime import activate_pre_manager_history_expansion
from app.intake.application.transition_guard import resolve_transition_guard


def _retrieved_meal_chunk(
    *,
    meal_id: int,
    meal_thread_id: int,
    meal_version_id: int,
    title: str,
    content: str,
    timestamp: str,
    local_date: str,
    matched_terms: list[str],
    relative_time_label: str | None = None,
) -> dict[str, object]:
    return {
        "chunk_id": f"meal:{meal_id}",
        "source_type": "meal_record",
        "source_id": meal_id,
        "content": content,
        "timestamp": timestamp,
        "linked_meal_id": meal_id,
        "score": 10.0,
        "matched_terms": matched_terms,
        "metadata": {
            "title": title,
            "meal_thread_id": meal_thread_id,
            "meal_version_id": meal_version_id,
            "local_date": local_date,
            "relative_time_label": relative_time_label,
        },
    }


def _resolved_state(
    *,
    local_date: str = "2026-04-29",
    recent_committed_meals: list[dict[str, object]] | None = None,
    target_meal_reference: dict[str, object] | None = None,
    session_summary: dict[str, object] | None = None,
    retrieved_meal_records: list[dict[str, object]] | None = None,
    historical_meal_chunks: list[dict[str, object]] | None = None,
    transcript_chunks: list[dict[str, object]] | None = None,
) -> object:
    conversation_state = SimpleNamespace(
        retrieved_meal_records=retrieved_meal_records or [],
        historical_meal_chunks=historical_meal_chunks or [],
        transcript_chunks=transcript_chunks or [],
        session_summary=SimpleNamespace(**(session_summary or {})),
    )
    return SimpleNamespace(
        onboarding_ready=True,
        user_external_id="phase-a-user",
        user_id=1,
        local_date=local_date,
        active_meal=None,
        conversation_state=conversation_state,
        injected_context={
            "ACTIVE_MEAL": None,
            "PENDING_FOLLOWUP": {
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
            "SESSION_SUMMARY": session_summary or {},
        },
    )


def test_recent_correction_history_activation_upgrades_to_target_committed_thread() -> None:
    resolved_state = _resolved_state(
        recent_committed_meals=[],
        retrieved_meal_records=[
            _retrieved_meal_chunk(
                meal_id=501,
                meal_thread_id=77,
                meal_version_id=88,
                title="milk tea",
                content="milk tea bubble tea half sugar",
                timestamp="2026-04-29T09:00:00Z",
                local_date="2026-04-29",
                matched_terms=["milk", "tea"],
                relative_time_label="today",
            )
        ],
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="actually change that milk tea to half sugar",
        resolved_state=resolved_state,
    )
    pre_attachment = resolve_attachment_decision(current_turn_context)
    pre_guard = resolve_transition_guard(current_turn_context, pre_attachment)

    result = activate_pre_manager_history_expansion(
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
        pre_attachment_decision=pre_attachment,
        pre_transition_guard_result=pre_guard,
    )

    assert pre_attachment.disposition == "answer_only"
    assert pre_guard.verdict == "clarify_required"
    assert result.applied is True
    assert result.request is not None
    assert result.request.reason == "correction_reference"
    assert result.request.scope == "recent_meals"
    assert result.atomic_blocks_status == "not_supplied"
    assert result.resolution_gain is True
    assert result.post_attachment_decision.disposition == "target_committed_thread"
    assert result.post_attachment_decision.target_object_id == "77"
    assert result.post_transition_guard_result.verdict == "pass"
    assert result.selected_candidate_ids == ("77",)
    assert result.enriched_current_turn_context.candidate_attachment_targets[0]["target_object_id"] == "77"


def test_older_meal_history_activation_upgrades_single_historical_target() -> None:
    resolved_state = _resolved_state(
        local_date="2026-04-29",
        retrieved_meal_records=[
            _retrieved_meal_chunk(
                meal_id=700,
                meal_thread_id=99,
                meal_version_id=101,
                title="lunch box",
                content="yesterday lunch box rice chicken",
                timestamp="2026-04-28T12:00:00Z",
                local_date="2026-04-28",
                matched_terms=["rice"],
                relative_time_label="yesterday lunch",
            )
        ],
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="yesterday that one, change rice to half bowl",
        resolved_state=resolved_state,
    )

    result = activate_pre_manager_history_expansion(
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
    )

    assert result.applied is True
    assert result.request is not None
    assert result.request.reason == "older_meal_reference"
    assert result.request.scope == "committed_meals"
    assert result.resolution_gain is True
    assert result.post_attachment_decision.disposition == "target_committed_thread"
    assert result.post_attachment_decision.target_object_id == "99"


def test_multiple_history_candidates_remain_conservative_and_trace_ambiguity() -> None:
    resolved_state = _resolved_state(
        local_date="2026-04-29",
        retrieved_meal_records=[
            _retrieved_meal_chunk(
                meal_id=701,
                meal_thread_id=100,
                meal_version_id=102,
                title="lunch box",
                content="yesterday lunch box rice chicken",
                timestamp="2026-04-28T12:00:00Z",
                local_date="2026-04-28",
                matched_terms=["rice"],
                relative_time_label="yesterday lunch",
            ),
            _retrieved_meal_chunk(
                meal_id=702,
                meal_thread_id=101,
                meal_version_id=103,
                title="lunch plate",
                content="yesterday lunch plate rice pork",
                timestamp="2026-04-28T18:00:00Z",
                local_date="2026-04-28",
                matched_terms=["rice"],
                relative_time_label="yesterday dinner",
            ),
        ],
    )
    current_turn_context = build_current_turn_context_v1(
        raw_user_input="yesterday that one, change rice to half bowl",
        resolved_state=resolved_state,
    )

    result = activate_pre_manager_history_expansion(
        current_turn_context=current_turn_context,
        resolved_state=resolved_state,
    )

    assert result.applied is True
    assert result.resolution_gain is False
    assert result.post_attachment_decision.disposition == "answer_only"
    assert result.post_transition_guard_result.verdict == "clarify_required"
    assert result.ambiguity_detected is True
    assert result.selected_candidate_ids == ()
