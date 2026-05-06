from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.composition.non_fooddb_read_tool_executor import execute_non_fooddb_read_tool_calls
from app.intake.application.intake_trace_tools import append_trace_event_tool
from app.runtime.agent.manager import IntakeManagerResult


def build_non_fooddb_read_tool_executor(
    db: Session,
    *,
    user_id: int,
    local_date: str,
):
    def _execute(**kwargs: Any) -> list[dict[str, Any]]:
        return execute_non_fooddb_read_tool_calls(
            db=db,
            user_id=user_id,
            local_date=local_date,
            tool_calls=list(kwargs.get("tool_calls") or []),
        )

    return _execute


def finalize_non_fooddb_read_only_manager_intent(
    *,
    db: Session,
    manager_decision: IntakeManagerResult,
    user_id: int,
    local_date: str,
    request_id: str,
    build_remaining_budget: Any = build_remaining_budget_answer_contract,
    append_trace_event: Any = append_trace_event_tool,
) -> dict[str, Any] | None:
    if manager_decision.intent_type == "answer_remaining_budget":
        remaining_budget = build_remaining_budget(
            db,
            user_id=user_id,
            local_date=local_date,
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_remaining_budget_read",
            status="ok",
            summary={
                "status": remaining_budget.status,
                "daily_target_kcal": remaining_budget.daily_target_kcal,
                "consumed_kcal": remaining_budget.consumed_kcal,
                "remaining_kcal": remaining_budget.remaining_kcal,
                "meal_count": remaining_budget.meal_count,
            },
        )
        return {"remaining_budget": remaining_budget, "assistant_message_override": None}

    if manager_decision.intent_type == "onboarding_required":
        remaining_budget = build_remaining_budget(
            db,
            user_id=user_id,
            local_date=local_date,
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_onboarding_required",
            status="ok",
            summary={
                "status": remaining_budget.status,
                "reason": "budget_query_without_active_plan",
            },
        )
        return {"remaining_budget": remaining_budget, "assistant_message_override": None}

    if (
        manager_decision.intent_type == "general_chat"
        and manager_decision.workflow_effect == "answer_goal_summary_without_state_mutation"
        and any(
            isinstance(tool_result, dict) and tool_result.get("tool_name") == "read_body_plan"
            for tool_result in manager_decision.tool_results
        )
    ):
        assistant_message_override = str(
            manager_decision.answer_contract.get("reply_text")
            or manager_decision.response_summary
            or "I could not safely complete that read-only request."
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_general_chat_read_only",
            status="ok",
            summary={
                "workflow_effect": manager_decision.workflow_effect,
                "tool_calls": list(manager_decision.tool_calls),
                "tool_result_count": len(manager_decision.tool_results),
                "state_mutation": "none",
            },
        )
        return {
            "remaining_budget": None,
            "assistant_message_override": assistant_message_override,
        }
    if (
        manager_decision.intent_type == "general_chat"
        and manager_decision.workflow_effect == "answer_general_product_question_without_state_mutation"
        and any(
            isinstance(tool_result, dict) and tool_result.get("tool_name") == "answer_usage_question"
            for tool_result in manager_decision.tool_results
        )
    ):
        assistant_message_override = str(
            manager_decision.answer_contract.get("reply_text")
            or manager_decision.response_summary
            or "I can answer general product questions here, but I will not change state from this path."
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_general_chat_app_usage_read_only",
            status="ok",
            summary={
                "workflow_effect": manager_decision.workflow_effect,
                "tool_calls": list(manager_decision.tool_calls),
                "tool_result_count": len(manager_decision.tool_results),
                "state_mutation": "none",
            },
        )
        return {
            "remaining_budget": None,
            "assistant_message_override": assistant_message_override,
        }

    return None
