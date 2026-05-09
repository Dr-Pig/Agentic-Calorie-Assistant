from __future__ import annotations

import json

from app.runtime.agent.manager_context_payload import manager_context_packet_v1_prompt_payload


def test_post_tool_context_reference_compacts_active_day_state_and_hard_pins() -> None:
    packet = {
        "metadata": {
            "local_date": "2026-05-09",
            "context_policy_version": "accurate_intake_mvp_context_policy_v1",
            "claim_scope": "current_session_current_day_manager_input_evidence",
        },
        "context_loading_artifact": {
            "loaded_message_count": 3,
            "omitted_count": 1,
            "char_truncated": False,
            "token_budget_status": "within_budget",
        },
        "current_turn": {
            "channel": "web_shell",
            "manager_mode": "live_diagnostic",
            "interaction_event": {
                "event_type": "chat_message",
                "raw_text": "半糖中杯",
                "target_object_type": "meal_thread",
                "target_object_id": "thread-77",
            },
        },
        "recent_chat_window": {"messages": [{"role": "user", "content": "x" * 5000}]},
        "hard_pins": {
            "pending_followup": {
                "runtime_turn_id": "turn-1",
                "meal_thread_id": 77,
                "meal_item_id": 501,
                "expected_answer_type": "drink_size_sugar",
                "question": "多大杯、甜度多少？",
                "full_prompt_debug_blob": "x" * 5000,
            },
            "pending_draft": {
                "draft_id": "draft-1",
                "meal_thread_id": 77,
                "items": [{"debug_blob": "x" * 5000}],
            },
            "last_assistant_question": "多大杯、甜度多少？",
        },
        "active_day_state": {
            "budget_summary": {
                "status": "ready",
                "daily_target_kcal": 1800,
                "consumed_kcal": 520,
                "remaining_kcal": 1280,
                "show_macro": False,
                "macro_guard_reason": "missing_source",
                "debug_blob": "x" * 5000,
            },
            "active_meal_thread_ref": {
                "meal_thread_id": 77,
                "meal_version_id": 88,
                "meal_item_id": 501,
                "canonical_name": "bubble_milk_tea",
                "items": [{"debug_blob": "x" * 5000}],
            },
            "recent_correction_removal_summary": [{"debug_blob": "x" * 5000}],
            "read_only": True,
            "mutation_authority": False,
        },
        "target_candidates": {
            "for_correction_or_removal": [
                {"meal_thread_id": 77, "meal_item_id": 501, "debug_blob": "x" * 5000}
            ]
        },
        "constraints": ["frontend_cannot_infer_semantics"],
    }

    payload = manager_context_packet_v1_prompt_payload(
        packet,
        tool_results=[{"tool_name": "estimate_nutrition"}],
    )

    assert payload is not None
    rendered = json.dumps(payload, ensure_ascii=False)
    assert len(rendered) < len(json.dumps(packet, ensure_ascii=False))
    assert "debug_blob" not in rendered
    assert "full_prompt_debug_blob" not in rendered
    assert "messages" not in payload["recent_chat_window"]
    assert "for_correction_or_removal" not in payload["target_candidates"]

    hard_pins = payload["hard_pins"]
    assert hard_pins["hard_pins_compacted_after_tool_evidence"] is True
    assert hard_pins["pending_followup"] == {
        "runtime_turn_id": "turn-1",
        "meal_thread_id": 77,
        "meal_item_id": 501,
        "expected_answer_type": "drink_size_sugar",
        "question": "多大杯、甜度多少？",
    }
    assert hard_pins["pending_draft"] == {"draft_id": "draft-1", "meal_thread_id": 77}
    assert hard_pins["read_only"] is True
    assert hard_pins["mutation_authority"] is False

    active_day_state = payload["active_day_state"]
    assert active_day_state["active_day_state_compacted_after_tool_evidence"] is True
    assert active_day_state["budget_summary"] == {
        "status": "ready",
        "daily_target_kcal": 1800,
        "consumed_kcal": 520,
        "remaining_kcal": 1280,
        "show_macro": False,
        "macro_guard_reason": "missing_source",
    }
    assert active_day_state["active_meal_thread_ref"] == {
        "meal_thread_id": 77,
        "meal_version_id": 88,
        "meal_item_id": 501,
        "canonical_name": "bubble_milk_tea",
        "item_count": 1,
    }
    assert active_day_state["recent_correction_removal_count"] == 1
    assert active_day_state["read_only"] is True
    assert active_day_state["mutation_authority"] is False
