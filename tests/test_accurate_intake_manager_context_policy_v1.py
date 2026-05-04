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
    assert packet["recent_chat_window"]["policy"] == {"last_messages": 8, "max_chars": 1000}
    assert [turn["message_id"] for turn in packet["recent_chat_window"]["messages"]] == list(range(4, 12))
    assert all(turn["read_only"] is True for turn in packet["recent_chat_window"]["messages"])
    assert all(turn["mutation_authority"] is False for turn in packet["recent_chat_window"]["messages"])


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


def test_manager_context_packet_structures_target_candidates_without_authority() -> None:
    packet = build_manager_context_packet_v1(
        current_turn_context=_context(),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-1",
        target_candidates=[
            {"item_id": f"item-{i}", "display_name": f"item {i}", "meal_thread_id": "meal-1"}
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
