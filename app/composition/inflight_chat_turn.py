from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.conversation_turn_trace import record_runtime_turn_messages

PENDING_ASSISTANT_MESSAGE = "處理中..."


def record_inflight_intake_chat_turn(
    db: Session,
    *,
    user_external_id: str,
    request_id: str,
    local_date: str,
    raw_user_input: str | None,
    state_before: Any,
    current_turn_context: Any | None,
    manager_context_packet_v1: dict[str, Any] | None,
    phase_a_trace: dict[str, Any] | None,
) -> dict[str, Any]:
    """Persist a visible in-flight turn before slow provider work begins."""
    return record_runtime_turn_messages(
        db,
        user_external_id=user_external_id,
        request_id=request_id,
        local_date=local_date,
        raw_user_input=raw_user_input,
        assistant_message=PENDING_ASSISTANT_MESSAGE,
        state_before=state_before,
        current_turn_context=current_turn_context,
        manager_context_packet_v1=manager_context_packet_v1,
        state_after=state_before,
        phase_a_trace={**dict(phase_a_trace or {}), "runtime_turn_status": "in_progress"},
        result={
            "manager_decision": {"intent_type": "pending", "workflow_effect": "in_progress", "tool_calls": []},
            "intake_execution_manager": {"final": {"final_action": "pending", "workflow_effect": "in_progress"}},
            "state_delta": {},
            "sidecar": {"runtime_turn_status": "in_progress"},
        },
    )


__all__ = ["PENDING_ASSISTANT_MESSAGE", "record_inflight_intake_chat_turn"]
