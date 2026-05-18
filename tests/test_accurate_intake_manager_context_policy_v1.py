from __future__ import annotations

from app.intake.application.manager_context_policy import (
    MANAGER_CONTEXT_POLICY_VERSION,
    build_manager_context_packet_v1,
)
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent


def _context(*, recent_chat_turns: list[dict] | None = None) -> CurrentTurnContextV1:
    return CurrentTurnContextV1(
        user_utterance="有豆干、海帶、貢丸",
        last_system_question="請列出滷味品項。",
        recent_chat_turns=recent_chat_turns or [],
        pending_followup={
            "is_open": True,
            "meal_thread_id": 77,
            "runtime_turn_id": "turn-luwei-ask",
            "assistant_message_id": "msg-assistant-ask",
            "expected_answer_type": "listed_basket_components",
        },
        current_budget_snapshot={
            "target_kcal": 1600,
            "consumed_kcal": 420,
            "remaining_kcal": 1180,
            "read_only": True,
            "truth_owner": "budget_read_model",
        },
        recent_item_targets=[
            {"item_id": "item-1", "display_name": "雞肉飯", "meal_thread_id": "meal-1"},
            {"item_id": "item-2", "display_name": "湯", "meal_thread_id": "meal-1"},
        ],
        target_resolution_posture={"mutation_authority": False},
        current_interaction_event=InteractionEvent(
            source="chat",
            event_type="user_message",
            raw_text="有豆干、海帶、貢丸",
        ),
    )


def test_manager_context_packet_bounds_recent_chat_and_records_policy_version() -> None:
    turns = [
        {"message_id": i, "role": "user" if i % 2 else "assistant", "content": f"turn-{i}"}
        for i in range(12)
    ]

    packet = build_manager_context_packet_v1(
        current_turn_context=_context(recent_chat_turns=turns),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        max_recent_messages=8,
        max_recent_chars=1000,
    )

    assert packet["metadata"]["context_policy_version"] == MANAGER_CONTEXT_POLICY_VERSION
    assert packet["recent_chat_window"]["policy"] == {
        "mode": "token_budgeted",
        "max_messages_safety_cap": 8,
        "last_messages": 8,
        "max_chars": 1000,
        "hard_pins_preserved": True,
        "summary_role": "reference_only",
    }
    assert [turn["message_id"] for turn in packet["recent_chat_window"]["messages"]] == list(range(4, 12))
    assert all(turn["read_only"] is True for turn in packet["recent_chat_window"]["messages"])
    assert all(turn["mutation_authority"] is False for turn in packet["recent_chat_window"]["messages"])


def test_manager_context_packet_defaults_to_last_20_messages_and_6000_char_cap() -> None:
    turns = [
        {"message_id": i, "role": "user", "content": f"message-{i:02d}"}
        for i in range(25)
    ]

    packet = build_manager_context_packet_v1(
        current_turn_context=_context(recent_chat_turns=turns),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
    )

    artifact = packet["context_loading_artifact"]
    assert packet["recent_chat_window"]["policy"] == {
        "mode": "token_budgeted",
        "max_messages_safety_cap": 20,
        "last_messages": 20,
        "max_chars": 6000,
        "hard_pins_preserved": True,
        "summary_role": "reference_only",
    }
    assert [turn["message_id"] for turn in packet["recent_chat_window"]["messages"]] == list(range(5, 25))
    assert artifact["loaded_message_count"] == 20
    assert artifact["omitted_count"] == 5
    assert artifact["loaded_char_count"] == sum(len(f"message-{i:02d}") for i in range(5, 25))
    assert artifact["char_truncated"] is False
    assert artifact["token_budget_status"] == "within_budget"
    assert artifact["loaded_context_summary"] == {
        "recent_chat_messages": 20,
        "pending_followup_present": True,
        "pending_draft_present": False,
        "target_candidate_count": 2,
        "interaction_event_present": True,
    }
    assert artifact["omitted_context_summary"]["policy_excluded_context_ids"] == [
        "debug_artifacts",
        "dogfood_review_artifacts",
        "raw_trace_dump",
        "food_gap_candidates_as_truth",
        "full_day_transcript_by_default",
        "long_term_memory",
        "proactive_context",
        "rescue_context",
        "recommendation_context",
    ]


def test_manager_context_packet_records_char_truncation_and_omitted_count() -> None:
    turns = [
        {"message_id": 1, "role": "user", "content": "a" * 3000},
        {"message_id": 2, "role": "assistant", "content": "b" * 3000},
        {"message_id": 3, "role": "user", "content": "c" * 3000},
    ]

    packet = build_manager_context_packet_v1(
        current_turn_context=_context(recent_chat_turns=turns),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        max_recent_messages=20,
        max_recent_chars=6000,
    )

    artifact = packet["context_loading_artifact"]
    assert [turn["message_id"] for turn in packet["recent_chat_window"]["messages"]] == [2, 3]
    assert artifact["loaded_message_count"] == 2
    assert artifact["omitted_count"] == 1
    assert artifact["loaded_char_count"] == 6000
    assert artifact["char_truncated"] is True
    assert artifact["token_budget_status"] == "at_hard_cap"
    assert artifact["omitted_context_summary"]["recent_chat_messages_omitted"] == 1


def test_manager_context_packet_hard_pins_pending_followup_and_draft() -> None:
    packet = build_manager_context_packet_v1(
        current_turn_context=_context(recent_chat_turns=[]),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        pending_draft={
            "draft_id": "draft-luwei",
            "food_family": "滷味",
            "created_at_turn_id": "turn-luwei-ask",
        },
    )

    assert packet["hard_pins"]["pending_followup"]["expected_answer_type"] == "listed_basket_components"
    assert packet["hard_pins"]["pending_followup"]["runtime_turn_id"] == "turn-luwei-ask"
    assert packet["hard_pins"]["pending_draft"]["draft_id"] == "draft-luwei"
    assert packet["hard_pins"]["last_assistant_question"] == "請列出滷味品項。"


def test_manager_context_packet_overrides_nested_mutation_authority_flags() -> None:
    context = _context(
        recent_chat_turns=[
            {
                "message_id": "unsafe-history",
                "role": "assistant",
                "content": "historical text",
                "read_only": False,
                "mutation_authority": True,
            }
        ]
    )
    context.pending_followup["read_only"] = False
    context.pending_followup["mutation_authority"] = True

    packet = build_manager_context_packet_v1(
        current_turn_context=context,
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        pending_draft={
            "draft_id": "unsafe-draft",
            "read_only": False,
            "mutation_authority": True,
        },
    )

    recent_message = packet["recent_chat_window"]["messages"][0]
    assert recent_message["read_only"] is True
    assert recent_message["mutation_authority"] is False
    assert packet["hard_pins"]["pending_followup"]["read_only"] is True
    assert packet["hard_pins"]["pending_followup"]["mutation_authority"] is False
    assert packet["hard_pins"]["pending_draft"]["read_only"] is True
    assert packet["hard_pins"]["pending_draft"]["mutation_authority"] is False


def test_manager_context_packet_excludes_review_debug_and_deferred_memory_context() -> None:
    packet = build_manager_context_packet_v1(
        current_turn_context=_context(),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        debug_artifacts={"state_before": {"unsafe": "large-debug"}},
        dogfood_review_artifacts={"classification": "food_evidence_gap"},
        raw_trace_dump={"manager_rounds": []},
        food_gap_candidates=[{"gap_family": "bubble_tea"}],
        long_term_memory={"favorite": "latte"},
        proactive_context={"nudge": "drink water"},
        rescue_context={"suggestion": "walk"},
        recommendation_context={"dinner": "salad"},
    )

    assert "debug_artifacts" not in packet
    assert "dogfood_review_artifacts" not in packet
    assert "raw_trace_dump" not in packet
    assert "food_gap_candidates" not in packet
    assert "long_term_memory" not in packet
    assert "proactive_context" not in packet
    assert "rescue_context" not in packet
    assert "recommendation_context" not in packet
    assert {item["context_id"] for item in packet["omitted_context"]} == {
        "debug_artifacts",
        "dogfood_review_artifacts",
        "raw_trace_dump",
        "food_gap_candidates",
        "long_term_memory",
        "proactive_context",
        "rescue_context",
        "recommendation_context",
    }
    assert packet["context_loading_artifact"]["omitted_context_summary"]["policy_excluded_context_ids"] == [
        "debug_artifacts",
        "dogfood_review_artifacts",
        "raw_trace_dump",
        "food_gap_candidates_as_truth",
        "full_day_transcript_by_default",
        "long_term_memory",
        "proactive_context",
        "rescue_context",
        "recommendation_context",
    ]


def test_manager_context_packet_structures_target_candidates_without_authority() -> None:
    packet = build_manager_context_packet_v1(
        current_turn_context=_context(),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        target_candidates=[
            {"item_id": f"item-{i}", "display_name": f"item {i}", "meal_thread_id": "meal-1", "removable": True}
            for i in range(12)
        ],
        max_target_candidates=10,
    )

    candidates = packet["target_candidates"]["for_correction_or_removal"]
    assert len(candidates) == 10
    assert candidates[0] == {
        "item_id": "item-0",
        "display_name": "item 0",
        "meal_thread_id": "meal-1",
        "uniqueness_status": "candidate",
        "removable": True,
        "read_only": True,
        "mutation_authority": False,
    }
    assert packet["target_candidates"]["mutation_authority"] is False


def test_manager_context_packet_v1_exposes_ab_mechanism_fields_without_semantic_authority() -> None:
    context = _context(recent_chat_turns=[
        {"message_id": "m1", "role": "user", "content": "breakfast combo"},
        {"message_id": "m2", "role": "assistant", "content": "What is included?"},
    ])
    context.pending_followup.update(
        {
            "pending_type": "blocking_composition",
            "required_slots": [
                {
                    "slot_id": "composition_items",
                    "slot_kind": "composition_items",
                    "required_for_commit": True,
                    "current_value": None,
                    "source": "manager_pending_followup",
                    "resolution_condition": "user lists concrete items",
                    "asked_question": "What is included?",
                }
            ],
            "optional_slots": [
                {
                    "slot_id": "drink_sugar",
                    "slot_kind": "sugar_level",
                    "required_for_commit": False,
                    "current_value": None,
                    "source": "manager_pending_followup",
                    "resolution_condition": "user states sugar level",
                    "asked_question": "Optional drink refinement",
                }
            ],
        }
    )

    packet = build_manager_context_packet_v1(
        current_turn_context=context,
        user_id="local-user",
        local_date="2026-05-04",
        local_time="08:15:00",
        timezone="Asia/Taipei",
        session_id="session-1",
        turn_id="turn-1",
        trace_id_runtime_only="trace-1",
        queue_state={
            "processing_turn_id": "turn-0",
            "queued_inputs": [{"sequence_number": 2, "text": "add tea", "priority": "next"}],
            "sequence_number": 2,
            "priority": "next",
        },
        evidence_state={
            "fooddb": {"status": "generic_anchor_available"},
            "websearch": {"availability": "available_not_called"},
            "macro": {"macro_evidence_status": "hidden_missing_source"},
            "selected_extracts": [],
            "rejected_candidates": [],
        },
    )

    assert packet["metadata"]["turn_id"] == "turn-1"
    assert packet["metadata"]["trace_id_runtime_only"] == "trace-1"
    assert packet["metadata"]["local_time"] == "08:15:00"
    assert packet["metadata"]["timezone"] == "Asia/Taipei"
    assert packet["current_turn"]["user_utterance"] == context.user_utterance
    assert packet["current_turn"]["current_turn_first"] is True
    assert packet["recent_chat_window"]["policy"]["mode"] == "token_budgeted"
    assert packet["queue_state"]["processing_turn_id"] == "turn-0"
    assert packet["queue_state"]["queued_inputs"][0]["priority"] == "next"
    assert packet["queue_state"]["read_only"] is True
    assert packet["active_workflow"]["selection_owner"] == "manager"
    assert packet["active_workflow"]["pending_type"] == "blocking_composition"
    assert packet["active_workflow"]["required_slots"][0]["slot_kind"] == "composition_items"
    assert packet["active_workflow"]["optional_slots"][0]["slot_kind"] == "sugar_level"
    assert "determine_current_turn_relation_to_active_workflow" in packet["active_workflow"]["manager_must_decide"]
    assert packet["target_candidates"]["selection_owner"] == "manager"
    assert packet["target_candidates"]["mutation_authority"] is False
    assert packet["read_model_summary"]["budget"]["truth_owner"] == "budget_read_model"
    assert packet["evidence_state"]["fooddb"]["status"] == "generic_anchor_available"
    assert packet["evidence_state"]["macro"]["macro_evidence_status"] == "hidden_missing_source"
    assert packet["context_lineage"]["reinject_reason"] in {"none", "history_trimmed_with_hard_pins"}


def test_manager_context_packet_exposes_interaction_event_and_targets_as_read_only_support() -> None:
    context = _context()
    context.current_interaction_event = InteractionEvent(
        source="ui",
        event_type="tap_target",
        raw_text="remove this",
        target_object_type="meal_item",
        target_object_id="item-42",
        payload={"display_name": "soup"},
    )

    packet = build_manager_context_packet_v1(
        current_turn_context=context,
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        target_candidates=[
            {
                "target_object_type": "meal_item",
                "target_object_id": "item-42",
                "display_name": "soup",
                "selected_target": True,
                "mutation_authority": True,
            }
        ],
    )

    interaction_event = packet["current_turn"]["interaction_event"]
    candidate = packet["target_candidates"]["for_correction_or_removal"][0]
    assert interaction_event["target_object_type"] == "meal_item"
    assert interaction_event["target_object_id"] == "item-42"
    assert interaction_event["read_only"] is True
    assert interaction_event["mutation_authority"] is False
    assert candidate["target_object_id"] == "item-42"
    assert candidate["display_name"] == "soup"
    assert "selected_target" not in candidate
    assert candidate["mutation_authority"] is False


def test_manager_context_packet_strips_unsafe_interaction_and_target_fields() -> None:
    context = _context()
    context.current_interaction_event = InteractionEvent(
        source="ui",
        event_type="tap_target",
        raw_text="remove this",
        action_id="remove-item",
        target_object_type="meal_item",
        target_object_id="item-42",
        occurred_at="2026-05-04T12:00:00+08:00",
        payload={
            "display_name": "soup",
            "target_label": "Soup item",
            "semantic_decision": {"workflow_effect": "correction"},
            "mutation_authority": True,
        },
        metadata={
            "target_label": "Soup metadata label",
            "selected_target": True,
            "route_target": "commit",
        },
    )

    packet = build_manager_context_packet_v1(
        current_turn_context=context,
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        target_candidates=[
            {
                "target_object_type": "meal_item",
                "target_object_id": "item-42",
                "meal_item_id": 42,
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "display_name": "soup",
                "canonical_name": "soup",
                "eligible": True,
                "removable": True,
                "selected_target": True,
                "mutation_authority": True,
                "semantic_decision": {"workflow_effect": "correction"},
                "route_target": "commit",
                "payload": {"unsafe": "nested"},
            }
        ],
    )

    interaction_event = packet["current_turn"]["interaction_event"]
    candidate = packet["target_candidates"]["for_correction_or_removal"][0]
    assert interaction_event == {
        "source": "ui",
        "surface_mode": "ui_anchored_action",
        "event_type": "tap_target",
        "raw_text": "remove this",
        "action_id": "remove-item",
        "target_object_type": "meal_item",
        "target_object_id": "item-42",
        "occurred_at": "2026-05-04T12:00:00+08:00",
        "payload": {"display_name": "soup", "target_label": "Soup item"},
        "metadata": {"target_label": "Soup metadata label"},
        "read_only": True,
        "mutation_authority": False,
    }
    assert candidate == {
        "target_object_type": "meal_item",
        "target_object_id": "item-42",
        "meal_item_id": 42,
        "meal_thread_id": 77,
        "meal_version_id": 88,
        "display_name": "soup",
        "target_display_name": "soup",
        "canonical_name": "soup",
        "eligible": True,
        "removable": True,
        "uniqueness_status": "candidate",
        "read_only": True,
        "mutation_authority": False,
    }
