from __future__ import annotations

from typing import Any


def attach_remaining_query_runtime(
    runtime: dict[str, Any],
    *,
    request_trace: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
) -> None:
    if not _manager_answered_remaining_budget(manager_final, manager_decision):
        return
    if "remaining_source" not in runtime and _budget_read_model_evidence_present(request_trace, manager_final, manager_decision):
        runtime["remaining_source"] = "budget_read_model"
    if "rescue_plan_allowed" not in runtime:
        runtime["rescue_plan_allowed"] = False


def attach_remaining_query_ui(
    ui: dict[str, Any],
    *,
    request_trace: dict[str, Any],
) -> None:
    if "frontend_remaining_math_allowed" not in ui:
        ui["frontend_remaining_math_allowed"] = False
    if "chat_today_same_truth_required" not in ui and _budget_remaining_values_align(request_trace):
        ui["chat_today_same_truth_required"] = True


def _manager_answered_remaining_budget(
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
) -> bool:
    final = manager_final or manager_decision
    semantic = _dict(final.get("semantic_decision"))
    return (
        final.get("final_action") == "answer_remaining_budget"
        or semantic.get("final_action_candidate") == "answer_remaining_budget"
        or semantic.get("current_turn_intent") == "answer_remaining_budget"
    )


def _budget_read_model_evidence_present(
    request_trace: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
) -> bool:
    final = manager_final or manager_decision
    semantic = _dict(final.get("semantic_decision"))
    if semantic.get("source") == "budget_read_model":
        return True
    if _dict(_dict(request_trace.get("tool_outputs")).get("remaining_budget")).get("status") == "ready":
        return True
    current_budget = _dict(_dict(request_trace.get("state_after")).get("current_budget_view"))
    return current_budget.get("remaining_kcal") is not None


def _budget_remaining_values_align(request_trace: dict[str, Any]) -> bool:
    remaining_budget = _dict(_dict(request_trace.get("tool_outputs")).get("remaining_budget"))
    current_budget = _dict(_dict(request_trace.get("state_after")).get("current_budget_view"))
    if not remaining_budget or not current_budget:
        return False
    return (
        remaining_budget.get("remaining_kcal") == current_budget.get("remaining_kcal")
        and remaining_budget.get("consumed_kcal") == current_budget.get("consumed_kcal")
    )


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
