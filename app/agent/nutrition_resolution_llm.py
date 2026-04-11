from __future__ import annotations

from typing import Any

from ..schemas import TurnIntentResult


def render_primary_system_prompt(
    *,
    stable_prompt: str,
    dynamic_addition: dict[str, Any],
    template_context: str,
    driver_context: str,
    latest_log: Any | None,
    planner_result: TurnIntentResult,
    active_meal_context_allowed: bool,
    thin_sanitized_input: str,
    boundary_followup_question: str,
) -> str:
    parts = [stable_prompt.rstrip(), "\n\n[DYNAMIC_SYSTEM_ADDITION]\n", str(dynamic_addition)]
    if latest_log and active_meal_context_allowed:
        display_components = latest_log.components_json or [{"name": latest_log.meal_title, "portion_hint": "1 serving"}]
        parts.extend(
            [
                "\n\n[ACTIVE_MEAL_CONTEXT]\n",
                f"title: {latest_log.meal_title}\n",
                f"latest_kcal: {latest_log.kcal}\n",
                f"components: {display_components}\n",
                f"current_input: {thin_sanitized_input}\n",
                "Use this only because the planner already decided the user is still talking about the same meal.\n",
            ]
        )
    elif planner_result.meal_boundary == "boundary_clarification":
        parts.extend(
            [
                "\n\n[BOUNDARY_NOTE]\n",
                f"If you cannot safely estimate yet, the best clarification direction is: {boundary_followup_question}\n",
                "Do not merge old meal components unless the planner already allowed it.\n",
            ]
        )
    if template_context:
        parts.extend(["\n\n[TEMPLATE_CONTEXT]\n", template_context])
    if driver_context:
        parts.extend(["\n\n[DRIVER_CONTEXT]\n", driver_context])
    return "".join(parts)
