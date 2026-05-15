from __future__ import annotations

from typing import Any

from app.composition.intake_execution_response import finalized_budget_summary
from app.composition.intake_manager_tool_batch import nutrition_tool_output


def build_refreshed_intake_tool_outputs(
    *,
    raw_user_input: str,
    nutrition_artifact: Any | None,
    correction_target: dict[str, Any],
    budget_summary: dict[str, Any] | None,
    manager_tool_results: tuple[dict[str, Any], ...] | list[dict[str, Any]],
    state_mutation_summary: dict[str, Any],
    commit_boundary_blocked: bool,
    guard_blocked_for_side_effects: bool,
    state_before: Any,
    state_after: Any,
) -> tuple[dict[str, Any], dict[str, Any] | None]:
    refreshed_tool_results = [dict(item) for item in manager_tool_results]
    if nutrition_artifact is not None:
        refreshed_tool_results = _replace_or_append_nutrition_output(
            raw_user_input=raw_user_input,
            nutrition_artifact=nutrition_artifact,
            correction_target=correction_target,
            budget_summary=budget_summary,
            refreshed_tool_results=refreshed_tool_results,
        )
    tool_outputs = {"tool_results": refreshed_tool_results}
    if budget_summary is not None and (
        state_mutation_summary.get("canonical_commit") or commit_boundary_blocked or guard_blocked_for_side_effects
    ):
        budget_summary = finalized_budget_summary(
            budget_summary=budget_summary,
            state_before=state_before,
            state_after=state_after,
        )
        tool_outputs["budget_summary"] = budget_summary
    return tool_outputs, budget_summary


def _replace_or_append_nutrition_output(
    *,
    raw_user_input: str,
    nutrition_artifact: Any,
    correction_target: dict[str, Any],
    budget_summary: dict[str, Any] | None,
    refreshed_tool_results: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    refreshed_nutrition_output = nutrition_tool_output(
        raw_user_input=raw_user_input,
        nutrition_artifact=nutrition_artifact,
        correction_target=correction_target,
        budget_summary=budget_summary,
    )
    for index, item in enumerate(refreshed_tool_results):
        tool_name = str(item.get("tool_name") or "").strip()
        if tool_name in {"estimate_nutrition", "user_provided_kcal_evidence"}:
            refreshed_tool_results[index] = {**refreshed_nutrition_output, "tool_name": tool_name}
            return refreshed_tool_results
    refreshed_tool_results.append(refreshed_nutrition_output)
    return refreshed_tool_results
