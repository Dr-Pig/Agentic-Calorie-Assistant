from __future__ import annotations

from datetime import datetime
from types import SimpleNamespace

from app.composition.state_resolver import RECENT_CHAT_SOURCE_TAIL_LIMIT, _recent_chat_turns
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
    current_budget: dict[str, object] | None = None,
    active_body_plan: dict[str, object] | None = None,
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
            "CURRENT_BUDGET": current_budget
            if current_budget is not None
            else {
                "budget_kcal": 0,
                "consumed_kcal": 0,
                "remaining_kcal": 0,
                "active_meal_count": 0,
            },
            "ACTIVE_BODY_PLAN": active_body_plan
            if active_body_plan is not None
            else {
                "body_plan_id": None,
                "goal_type": None,
                "daily_budget_kcal": 0,
            },
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


def test_recent_chat_turn_context_is_current_day_only_read_only_evidence() -> None:
    messages = [
        SimpleNamespace(
            id=1,
            role="user",
            content="昨天的訊息",
            created_at=datetime(2026, 4, 28, 12, 0, 0),
            trace_id="turn-yesterday",
            linked_meal_log_id=None,
            trace_json={"runtime_turn_trace": {"local_date": "2026-04-28"}},
        ),
        SimpleNamespace(
            id=2,
            role="assistant",
            content="請列出滷味品項與大致份量。",
            created_at=datetime(2026, 4, 29, 12, 0, 0),
            trace_id="turn-today",
            linked_meal_log_id=10,
            trace_json={
                "runtime_turn_trace": {
                    "local_date": "2026-04-29",
                    "assistant_response": {"structured_followup_question": "請列出滷味品項與大致份量。"},
                }
            },
        ),
    ]

    turns = _recent_chat_turns(messages, local_date="2026-04-29")

    assert [turn["trace_id"] for turn in turns] == ["turn-today"]
    assert turns[0]["structured_followup_question"] == "請列出滷味品項與大致份量。"
    assert turns[0]["source"] == "sqlite_message_buffer"
    assert turns[0]["read_only"] is True
    assert turns[0]["mutation_authority"] is False


def test_recent_chat_source_tail_feeds_token_budgeted_context_window() -> None:
    messages = [
        SimpleNamespace(
            id=index,
            role="user" if index % 2 else "assistant",
            content=f"turn-{index:02d}",
            created_at=datetime(2026, 4, 29, 12, index % 60, 0),
            trace_id=f"trace-{index}",
            linked_meal_log_id=None,
            trace_json={"runtime_turn_trace": {"local_date": "2026-04-29"}},
        )
        for index in range(RECENT_CHAT_SOURCE_TAIL_LIMIT + 5)
    ]

    turns = _recent_chat_turns(messages, local_date="2026-04-29")

    assert len(turns) == RECENT_CHAT_SOURCE_TAIL_LIMIT
    assert [turn["message_id"] for turn in turns[:2]] == [5, 6]
    assert [turn["message_id"] for turn in turns[-2:]] == [
        RECENT_CHAT_SOURCE_TAIL_LIMIT + 3,
        RECENT_CHAT_SOURCE_TAIL_LIMIT + 4,
    ]
    assert all(turn["read_only"] is True for turn in turns)
    assert all(turn["mutation_authority"] is False for turn in turns)


def test_current_turn_context_uses_token_budgeted_recent_chat_window() -> None:
    resolved_state = _resolved_state(
        pending_followup={
            "is_open": True,
            "meal_id": 10,
            "meal_thread_id": 77,
            "pending_question": "What portion was it?",
        }
    )
    resolved_state.injected_context["RECENT_CHAT_TURNS"] = [
        {
            "message_id": index,
            "role": "user" if index % 2 else "assistant",
            "content": f"turn-{index:02d}",
            "created_at": f"2026-04-29T12:{index:02d}:00+08:00",
            "trace_id": f"trace-{index}",
            "local_date": "2026-04-29",
        }
        for index in range(25)
    ]

    context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=resolved_state,
    )

    summary = context.source_views["recent_chat_turns"].summary
    artifact = context.current_turn_runtime_summary["recent_chat_loading_artifact"]
    assert [turn["message_id"] for turn in context.recent_chat_turns] == list(range(5, 25))
    assert all(turn["read_only"] is True for turn in context.recent_chat_turns)
    assert all(turn["mutation_authority"] is False for turn in context.recent_chat_turns)
    assert summary["policy"] == "token_budgeted"
    assert summary["token_budget"] == 2000
    assert artifact["loaded_message_count"] == 20
    assert artifact["omitted_count"] == 5
    assert artifact["canonical_state_reinjected_after_history_trim"] is True


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


def test_build_current_turn_context_v1_exposes_read_only_context_contract_fields() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="今天還剩多少",
        resolved_state=_resolved_state(
            active_meal={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_item_id": 990,
                "canonical_name": "milk tea",
                "meal_title": "milk tea",
                "item_resolution_source": "single_active_item",
            },
            target_meal_reference={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_item_id": 990,
                "canonical_name": "milk tea",
                "meal_title": "milk tea",
                "target_resolution_source": "active_meal_view",
                "correction_confidence": "medium",
                "item_resolution_source": "single_active_item",
            },
            current_budget={
                "budget_kcal": 1800,
                "consumed_kcal": 600,
                "remaining_kcal": 1200,
                "active_meal_count": 1,
            },
            active_body_plan={
                "body_plan_id": 5,
                "goal_type": "lose_weight",
                "daily_budget_kcal": 1800,
            },
        ),
    )

    assert context.current_budget_snapshot["budget_kcal"] == 1800
    assert context.current_budget_snapshot["consumed_kcal"] == 600
    assert context.current_budget_snapshot["remaining_kcal"] == 1200
    assert context.current_budget_snapshot["active_meal_count"] == 1
    assert context.current_budget_snapshot["has_active_plan"] is True
    assert context.current_budget_snapshot["source"] == "current_budget_view"
    assert context.current_budget_snapshot["truth_owner"] == "budget_read_model"
    assert context.current_budget_snapshot["read_only"] is True
    assert context.active_body_plan_snapshot["body_plan_id"] == 5
    assert context.active_body_plan_snapshot["truth_owner"] == "body_read_model"
    assert context.recent_item_targets == [
        {
            "target_object_type": "meal_item",
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "meal_item_id": 990,
            "canonical_name": "milk tea",
            "source": "active_meal_view",
            "confidence": "medium",
            "item_resolution_source": "single_active_item",
        }
    ]
    assert context.target_resolution_posture == {
        "target_resolution_source": "active_meal_view",
        "correction_confidence": "medium",
        "item_resolution_source": "single_active_item",
        "mutation_authority": False,
        "read_only": True,
    }
    assert context.context_freshness["current_budget_snapshot"] == "current_turn"
    assert context.context_freshness["active_body_plan_snapshot"] == "current_turn"
    assert context.source_views["current_budget_snapshot"].owner == "budget/current_budget_read_model"
    assert context.source_views["active_body_plan_snapshot"].owner == "body/active_body_plan_read_model"


def test_current_turn_context_preserves_resolver_budget_fields_without_recompute() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="今天還剩多少",
        resolved_state=_resolved_state(
            current_budget={
                "budget_kcal": 1800,
                "consumed_kcal": 500,
                "remaining_kcal": 1200,
                "active_meal_count": 2,
                "has_active_plan": True,
                "has_day_budget_ledger": True,
                "no_plan_posture": "not_applicable",
                "freshness_status": "stale",
            },
            active_body_plan={
                "body_plan_id": 5,
                "goal_type": "lose_weight",
                "daily_budget_kcal": 1800,
                "freshness_status": "stale",
            },
        ),
    )

    assert context.current_budget_snapshot["remaining_kcal"] == 1200
    assert context.current_budget_snapshot["freshness_status"] == "stale"
    assert context.current_budget_snapshot["has_day_budget_ledger"] is True
    assert context.context_freshness["current_budget_snapshot"] == "stale"
    assert context.active_body_plan_snapshot["freshness_status"] == "stale"


def test_current_turn_context_keeps_multi_item_candidates_non_authoritative() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="飯少一點",
        resolved_state=_resolved_state(
            recent_committed_meals=[
                {
                    "meal_thread_id": 77,
                    "meal_version_id": 88,
                    "meal_title": "rice and egg",
                    "item_resolution_source": "ambiguous_active_items",
                    "item_candidates": [
                        {
                            "meal_item_id": 901,
                            "canonical_name": "rice",
                            "item_index": 0,
                            "estimated_kcal": 260,
                            "mutation_authority": False,
                            "selected_target": False,
                        },
                        {
                            "meal_item_id": 902,
                            "canonical_name": "egg",
                            "item_index": 1,
                            "estimated_kcal": 90,
                            "mutation_authority": False,
                            "selected_target": False,
                        },
                    ],
                }
            ],
            target_meal_reference={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "rice and egg",
                "target_resolution_source": "active_meal_view",
                "correction_confidence": "medium",
                "item_resolution_source": "ambiguous_active_items",
            },
        ),
    )

    assert context.target_resolution_posture["item_resolution_source"] == "ambiguous_active_items"
    assert context.target_resolution_posture["mutation_authority"] is False
    assert context.target_resolution_posture["read_only"] is True
    assert context.recent_item_targets == [
        {
            "target_object_type": "meal_item_candidate",
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "meal_item_id": 901,
            "canonical_name": "rice",
            "item_index": 0,
            "estimated_kcal": 260,
            "source": "recent_committed_meal",
            "confidence": "medium",
            "item_resolution_source": "ambiguous_active_items",
            "mutation_authority": False,
            "selected_target": False,
        },
        {
            "target_object_type": "meal_item_candidate",
            "meal_thread_id": 77,
            "meal_version_id": 88,
            "meal_item_id": 902,
            "canonical_name": "egg",
            "item_index": 1,
            "estimated_kcal": 90,
            "source": "recent_committed_meal",
            "confidence": "medium",
            "item_resolution_source": "ambiguous_active_items",
            "mutation_authority": False,
            "selected_target": False,
        },
    ]


def test_current_turn_context_builds_bounded_session_atomic_blocks_as_support_evidence() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="半糖",
        resolved_state=_resolved_state(
            pending_followup={
                "is_open": True,
                "meal_id": 10,
                "meal_thread_id": 77,
                "pending_question": "甜度是多少?",
            },
            target_meal_reference={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_item_id": 990,
                "canonical_name": "milk tea",
                "meal_title": "milk tea",
                "target_resolution_source": "pending_followup_state",
                "correction_confidence": "high",
                "item_resolution_source": "single_active_item",
            },
            session_summary={"latest_assistant_turns": ["甜度是多少?"]},
        ),
    )

    assert context.session_atomic_blocks == [
        {
            "block_type": "clarification_question_answer",
            "role": "support_evidence",
            "read_only": True,
            "mutation_authority": False,
            "question": "甜度是多少?",
            "answer": "半糖",
            "object_ref": {"meal_thread_id": 77, "meal_id": 10},
        },
        {
            "block_type": "pending_followup",
            "role": "support_evidence",
            "read_only": True,
            "mutation_authority": False,
            "pending_question": "甜度是多少?",
            "object_ref": {"meal_thread_id": 77, "meal_id": 10},
        },
        {
            "block_type": "correction_target_reference",
            "role": "support_evidence",
            "read_only": True,
            "mutation_authority": False,
            "object_ref": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_item_id": 990,
                "canonical_name": "milk tea",
            },
            "target_resolution_source": "pending_followup_state",
            "item_resolution_source": "single_active_item",
        },
    ]


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


def test_resolve_attachment_decision_keeps_pending_followup_answers_manager_owned() -> None:
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

    assert decision.disposition == "answer_only"
    assert decision.target_object_type == "none"
    assert decision.target_object_id is None
    assert decision.reason == "pending_followup_requires_manager_resolution"
    assert decision.allowed_transition_class == "none"
    assert decision.ambiguity_flag is False
    assert guard.verdict == "answer_only"


def test_resolve_attachment_decision_keeps_stale_pending_target_reference_manager_owned() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="half bowl of rice",
        resolved_state=_resolved_state(
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

    assert context.pending_followup is None
    assert context.candidate_attachment_targets
    assert context.open_workflow_type != "meal_correction"
    assert decision.disposition == "answer_only"
    assert decision.target_object_type == "none"
    assert decision.target_object_id is None
    assert decision.allowed_transition_class == "none"
    assert guard.verdict == "answer_only"


def test_resolve_attachment_decision_keeps_active_meal_back_reference_manager_owned() -> None:
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
    guard = resolve_transition_guard(context, decision)

    assert context.candidate_attachment_targets
    assert decision.disposition == "answer_only"
    assert decision.target_object_type == "none"
    assert decision.target_object_id is None
    assert decision.reason == "ambiguous_back_reference_requires_manager"
    assert decision.allowed_transition_class == "none"
    assert guard.verdict == "answer_only"


def test_resolve_attachment_decision_does_not_pick_recent_meal_from_raw_back_reference() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="change that to half sugar",
        resolved_state=_resolved_state(
            recent_committed_meals=[
                {
                    "meal_thread_id": 55,
                    "meal_version_id": 56,
                    "meal_title": "milk tea",
                    "occurred_at": "2026-04-28T19:00:00",
                }
            ],
        ),
    )

    decision = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, decision)

    assert decision.disposition == "answer_only"
    assert decision.target_object_id is None
    assert decision.reason == "ambiguous_back_reference_requires_manager"
    assert decision.ambiguity_flag is True
    assert guard.verdict == "answer_only"


def test_resolve_attachment_decision_does_not_finalize_manager_context_candidate() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="update this one",
        resolved_state=_resolved_state(
            target_meal_reference={
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_title": "breakfast plate",
                "target_resolution_source": "manager_context_candidates",
                "correction_confidence": "high",
            },
        ),
    )

    decision = resolve_attachment_decision(context)
    guard = resolve_transition_guard(context, decision)

    assert context.candidate_attachment_targets
    assert decision.disposition == "answer_only"
    assert decision.target_object_type == "none"
    assert decision.target_object_id is None
    assert decision.reason == "manager_target_candidate_requires_current_turn_resolution"
    assert decision.allowed_transition_class == "none"
    assert guard.verdict == "answer_only"


def test_current_turn_context_uses_resolved_target_reference_not_correction_keywords() -> None:
    context = build_current_turn_context_v1(
        raw_user_input="half sugar",
        resolved_state=_resolved_state(
            target_meal_reference={
                "meal_thread_id": 55,
                "meal_version_id": 56,
                "meal_title": "milk tea",
                "target_resolution_source": "manager_structured_target",
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
