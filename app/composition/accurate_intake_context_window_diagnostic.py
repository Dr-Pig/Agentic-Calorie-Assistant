from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from app.intake.application.manager_context_policy import (
    build_manager_context_packet_v1,
)
from app.runtime.contracts.phase_a import CurrentTurnContextV1, InteractionEvent


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _fixture_current_turn_context() -> CurrentTurnContextV1:
    recent_chat_turns = [
        {
            "message_id": f"msg-{index}",
            "role": "user" if index % 2 else "assistant",
            "content": f"fixture context message {index} " + ("x" * 360),
        }
        for index in range(25)
    ]
    return CurrentTurnContextV1(
        user_utterance="fixture correction turn",
        last_system_question="What was in the basket?",
        recent_chat_turns=recent_chat_turns,
        pending_followup={
            "is_open": True,
            "runtime_turn_id": "turn-pending-followup",
            "expected_answer_type": "listed_basket_components",
        },
        current_budget_snapshot={
            "target_kcal": 1600,
            "consumed_kcal": 420,
            "remaining_kcal": 1180,
            "read_only": True,
        },
        recent_item_targets=[
            {"meal_item_id": 1, "display_name": "tofu", "meal_thread_id": "meal-1"},
            {"meal_item_id": 2, "display_name": "rice", "meal_thread_id": "meal-1"},
        ],
        target_resolution_posture={"mutation_authority": False},
        current_interaction_event=InteractionEvent(
            source="chat",
            event_type="user_message",
            raw_text="fixture correction turn",
        ),
    )


def build_context_window_diagnostic_artifact() -> dict[str, Any]:
    packet = build_manager_context_packet_v1(
        current_turn_context=_fixture_current_turn_context(),
        user_id="local-user",
        local_date="2026-05-04",
        session_id="session-context-window",
        pending_draft={"draft_id": "draft-basket", "runtime_turn_id": "turn-pending-followup"},
        raw_trace_dump={"excluded": True},
        long_term_memory={"excluded": True},
        proactive_context={"excluded": True},
        rescue_context={"excluded": True},
    )
    loading = packet["context_loading_artifact"]
    omitted = loading["omitted_context_summary"]
    hard_pins = packet["hard_pins"]
    return _json_safe(
        {
            "artifact_schema_version": "1.0",
            "artifact_type": "accurate_intake_context_window_diagnostic",
            "status": "generated",
            "generated_at_utc": datetime.now(UTC).isoformat(),
            "claim_scope": "local_context_window_diagnostic",
            "local_only": True,
            "diagnostic_only": True,
            "context_policy_version": packet["metadata"]["context_policy_version"],
            "recent_window_policy": packet["recent_chat_window"]["policy"],
            "recent_chat_messages_loaded": loading["loaded_message_count"],
            "recent_chat_messages_omitted": omitted["recent_chat_messages_omitted"],
            "loaded_char_count": loading["loaded_char_count"],
            "hard_char_cap": loading["hard_char_cap"],
            "char_limit_applied": loading["char_truncated"] is True
            or loading["token_budget_status"] == "at_hard_cap",
            "pending_followup_hard_pinned": bool(hard_pins.get("pending_followup")),
            "pending_draft_hard_pinned": bool(hard_pins.get("pending_draft")),
            "forbidden_context_excluded": omitted["policy_excluded_context_ids"],
            "long_term_memory_used": False,
            "proactive_or_rescue_used": False,
            "mutation_authority": False,
            "manager_context_packet_schema_changed": False,
            "product_readiness_claimed": False,
            "private_self_use_approved": False,
            "packet_summary": {
                "loaded_context_summary": loading["loaded_context_summary"],
                "omitted_context_summary": omitted,
            },
        }
    )


__all__ = ["build_context_window_diagnostic_artifact"]
