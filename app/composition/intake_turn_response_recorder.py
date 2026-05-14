from __future__ import annotations

from typing import Any

from app.composition.conversation_turn_trace import record_runtime_turn_messages
from app.intake.application.intake_turn_support import intake_turn_manager_decision_payload


def build_record_and_return_intake_turn_response(
    db: Any,
    *,
    user_external_id: str,
    request_id: str,
    local_date: str,
    raw_user_input: str | None,
    assistant_message: str,
    state_before: Any,
    current_turn_context: Any,
    manager_context_packet_v1: dict[str, Any] | None,
    state_after: Any,
    phase_a_trace: dict[str, Any] | None,
    manager_decision: Any,
    remaining_budget: Any,
    sidecar: dict[str, Any],
    state_delta: dict[str, Any],
    trace_refs: dict[str, Any],
    latency_tracking: dict[str, Any],
) -> dict[str, Any]:
    response = {
        "request_id": request_id,
        "assistant_message": assistant_message,
        "manager_decision": intake_turn_manager_decision_payload(manager_decision),
        "intake_execution_manager": {"decision_1": None, "decision_2": None},
        "remaining_budget": {
            "status": remaining_budget.status,
            "daily_target_kcal": remaining_budget.daily_target_kcal,
            "consumed_kcal": remaining_budget.consumed_kcal,
            "remaining_kcal": remaining_budget.remaining_kcal,
            "meal_count": remaining_budget.meal_count,
        },
        "sidecar": sidecar,
        "state_delta": state_delta,
        "audit": trace_refs,
        "hard_fail_conditions": [],
        "shadow_mode": True,
        "latency_tracking": latency_tracking,
    }
    record_runtime_turn_messages(
        db,
        user_external_id=user_external_id,
        request_id=request_id,
        local_date=local_date,
        raw_user_input=raw_user_input,
        assistant_message=assistant_message,
        state_before=state_before,
        current_turn_context=current_turn_context,
        manager_context_packet_v1=manager_context_packet_v1,
        state_after=state_after,
        phase_a_trace=phase_a_trace,
        result=response,
    )
    return response


__all__ = ["build_record_and_return_intake_turn_response"]
