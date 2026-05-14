from __future__ import annotations

from typing import Any

from app.runtime.agent.manager import IntakeManagerResult


def finalize_answer_query_read_only(
    *,
    manager_decision: IntakeManagerResult,
    request_id: str,
    append_trace_event: Any,
) -> dict[str, Any] | None:
    if not _is_answer_query_no_mutation(manager_decision):
        return None
    assistant_message_override = str(
        manager_decision.answer_contract.get("reply_text")
        or manager_decision.response_summary
        or ""
    ) or None
    append_trace_event(
        request_id=request_id,
        stage="v2_answer_query_read_only",
        status="ok",
        summary={
            "workflow_effect": manager_decision.workflow_effect,
            "intent_type": manager_decision.intent_type,
            "state_mutation": "none",
        },
    )
    return {
        "remaining_budget": None,
        "assistant_message_override": assistant_message_override,
    }


def _is_answer_query_no_mutation(manager_decision: IntakeManagerResult) -> bool:
    return (
        getattr(manager_decision, "intent_type", "") == "answer_query"
        and getattr(manager_decision, "workflow_effect", "") == "answer_only"
        and getattr(manager_decision, "final_action", "") == "answer_only"
        and not getattr(manager_decision, "tool_calls", ())
    )


__all__ = ["finalize_answer_query_read_only"]
