from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.composition.non_fooddb_read_tool_executor import execute_non_fooddb_read_tool_calls
from app.intake.application.intake_trace_tools import append_trace_event_tool
from app.runtime.agent.manager import IntakeManagerResult


NON_FOODDB_READ_ONLY_MANAGER_TOOLS = (
    "budget.get_today_summary",
    "budget.get_remaining_calories",
    "budget.get_day_meal_log",
    "body.get_active_plan",
    "body.get_latest_observation",
    "calibration.get_pending_proposal",
    "app.answer_usage_question",
)


_LEGACY_PUBLIC_TOOL_COMPAT = {
    "body.get_active_plan": ("read_body_plan",),
    "app.answer_usage_question": ("answer_usage_question",),
    "budget.get_day_meal_log": ("read_day_budget",),
    "body.get_latest_observation": ("read_latest_weight_observation",),
    "calibration.get_pending_proposal": ("read_calibration_pending_proposal",),
}


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


def _tool_result_matches(tool_result: Any, names: set[str]) -> bool:
    if not isinstance(tool_result, dict):
        return False
    tool_name = str(tool_result.get("tool_name") or "")
    provenance = tool_result.get("provenance") if isinstance(tool_result.get("provenance"), dict) else {}
    canonical_tool_name = str(provenance.get("canonical_tool_name") or "")
    return tool_name in names or canonical_tool_name in names


def _has_tool_result(manager_decision: IntakeManagerResult, *names: str) -> bool:
    name_set = set(names)
    return any(_tool_result_matches(tool_result, name_set) for tool_result in manager_decision.tool_results)


def _has_public_tool_result(manager_decision: IntakeManagerResult, public_name: str) -> bool:
    return _has_tool_result(
        manager_decision,
        public_name,
        *_LEGACY_PUBLIC_TOOL_COMPAT.get(public_name, ()),
    )


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
        and _has_public_tool_result(manager_decision, "body.get_active_plan")
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
        and _has_public_tool_result(manager_decision, "app.answer_usage_question")
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
    if (
        manager_decision.intent_type == "general_chat"
        and manager_decision.workflow_effect == "answer_day_meal_log_without_state_mutation"
        and _has_public_tool_result(manager_decision, "budget.get_day_meal_log")
    ):
        assistant_message_override = str(
            manager_decision.answer_contract.get("reply_text")
            or manager_decision.response_summary
            or "I can answer the current day meal log here, but I will not change state from this path."
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_general_chat_day_meal_log_read_only",
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
        and manager_decision.workflow_effect == "answer_latest_weight_without_state_mutation"
        and _has_public_tool_result(manager_decision, "body.get_latest_observation")
    ):
        assistant_message_override = str(
            manager_decision.answer_contract.get("reply_text")
            or manager_decision.response_summary
            or "I can answer the latest weight here, but I will not change state from this path."
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_general_chat_latest_weight_read_only",
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
        and manager_decision.workflow_effect == "answer_calibration_pending_proposal_without_state_mutation"
        and _has_public_tool_result(manager_decision, "calibration.get_pending_proposal")
    ):
        assistant_message_override = str(
            manager_decision.answer_contract.get("reply_text")
            or manager_decision.response_summary
            or "I can answer pending calibration proposal status, but I will not change state from this path."
        )
        append_trace_event(
            request_id=request_id,
            stage="v2_general_chat_calibration_pending_proposal_read_only",
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
