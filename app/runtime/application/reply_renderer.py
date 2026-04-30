from __future__ import annotations

from typing import Any


def _followup_range_text(*, estimated_kcal: int) -> str:
    lower = max(0, int(round(estimated_kcal * 0.8 / 10.0) * 10))
    upper = max(lower, int(round(estimated_kcal * 1.2 / 10.0) * 10))
    return f"約 {lower}-{upper} kcal。"


def render_intake_reply(
    *,
    intent_type: str,
    onboarding_result: Any | None = None,
    remaining_budget: Any | None = None,
    active_body_plan_view: Any | None = None,
    nutrition_payload: Any | None = None,
    persistence_result: Any | None = None,
    manager_final_action: str | None = None,
    budget_summary: dict[str, Any] | None = None,
) -> str:
    if intent_type == "complete_onboarding" and onboarding_result is not None:
        return (
            f"Onboarding completed. TDEE about {onboarding_result.target_result.estimated_tdee_kcal} kcal. "
            f"Daily target {onboarding_result.target_result.recommended_target_kcal} kcal."
        )
    if intent_type == "answer_remaining_budget" and remaining_budget is not None:
        if remaining_budget.status == "onboarding_required":
            return "Onboarding is required before I can answer remaining budget."
        tdee = int(getattr(active_body_plan_view, "estimated_tdee", 0) or 0)
        tdee_prefix = f"TDEE about {tdee} kcal. " if tdee > 0 else ""
        return (
            f"{tdee_prefix}Today target {remaining_budget.daily_target_kcal} kcal, "
            f"consumed {remaining_budget.consumed_kcal} kcal, "
            f"remaining {remaining_budget.remaining_kcal} kcal."
        )
    if intent_type == "onboarding_required":
        return "Please complete onboarding first so I can seed your body plan and daily budget."
    if intent_type == "manager_unavailable":
        return "I could not safely complete that turn because the manager provider is unavailable. Nothing was committed."
    if intent_type == "log_meal" and nutrition_payload is not None:
        if manager_final_action == "no_commit":
            return "I could not safely complete that turn, so nothing was committed."
        component_estimates = list(getattr(nutrition_payload, "component_estimates", []) or [])
        if component_estimates:
            item_parts = [
                f"{component.name} {int(component.estimated_kcal or 0)} kcal"
                for component in component_estimates
            ]
            total_kcal = int(getattr(nutrition_payload, "estimated_kcal", 0) or 0)
            if manager_final_action == "ask_followup":
                reply_text = getattr(nutrition_payload, "reply_text", None)
                followup_question = str(getattr(nutrition_payload, "followup_question", None) or "").strip()
                budget_part = ""
                if remaining_budget is not None and remaining_budget.status == "ready":
                    remaining_kcal = int(remaining_budget.remaining_kcal or 0)
                    budget_part = f" Total {total_kcal} kcal. Remaining about {remaining_kcal} kcal today."
                
                if reply_text and followup_question:
                    digits = [char for char in str(reply_text) if char.isdigit()]
                    has_range = "-" in str(reply_text) or "到" in str(reply_text)
                    if digits and not has_range:
                        return f"{_followup_range_text(estimated_kcal=total_kcal)}{budget_part} {followup_question}"
                if reply_text and followup_question and followup_question not in str(reply_text):
                    return f"{reply_text}{budget_part} {followup_question}"
                if reply_text:
                    return f"{reply_text}{budget_part}"
                if followup_question:
                    return f"{followup_question}{budget_part}"
            logged_prefix = "Logged. " if persistence_result is not None and getattr(persistence_result, "canonical_commit", None) is not None else ""
            if manager_final_action == "correction_applied":
                budget_part = ""
                if remaining_budget is not None and remaining_budget.status == "ready":
                    remaining_kcal = int(remaining_budget.remaining_kcal or 0)
                    budget_part = f" Remaining about {remaining_kcal} kcal today."
                return f"Updated. {'; '.join(item_parts)}. Total {total_kcal} kcal.{budget_part}"
            if remaining_budget is not None and remaining_budget.status == "ready":
                remaining_kcal = int(remaining_budget.remaining_kcal or 0)
                if manager_final_action == "overshoot_note":
                    over_by = abs(int((budget_summary or {}).get("predicted_remaining_kcal_after") or 0))
                    if over_by <= 0:
                        over_by = abs(remaining_kcal)
                    return (
                        f"{logged_prefix}{'; '.join(item_parts)}. "
                        f"(Meal total: {total_kcal} kcal). "
                        f"Over by about {over_by} kcal today."
                    )
                if remaining_kcal < 0:
                    return (
                        f"{logged_prefix}{'; '.join(item_parts)}. "
                        f"(Meal total: {total_kcal} kcal). "
                        f"Over by about {abs(remaining_kcal)} kcal today."
                    )
                return (
                    f"{logged_prefix}{'; '.join(item_parts)}. "
                    f"(Meal total: {total_kcal} kcal). "
                    f"Remaining about {remaining_kcal} kcal today."
                )
            return f"{logged_prefix}{'; '.join(item_parts)}. Total {total_kcal} kcal."
        if persistence_result is not None and getattr(persistence_result, "canonical_commit", None) is None and getattr(nutrition_payload, "reply_text", None):
            return str(nutrition_payload.reply_text)
        if getattr(nutrition_payload, "reply_text", None):
            return str(nutrition_payload.reply_text)
        meal_title = nutrition_payload.meal_title or "meal"
        return f"Logged {meal_title}. Estimated {nutrition_payload.estimated_kcal} kcal."
    return "Intake manager completed without a renderable response."
