from __future__ import annotations

from typing import Any


def _followup_range_text(*, estimated_kcal: int) -> str:
    lower = max(0, int(round(estimated_kcal * 0.8 / 10.0) * 10))
    upper = max(lower, int(round(estimated_kcal * 1.2 / 10.0) * 10))
    return f"約 {lower}-{upper} kcal。"


def _component_text(component_estimates: list[Any]) -> str:
    return "、".join(
        f"{component.name} {int(component.estimated_kcal or 0)} kcal"
        for component in component_estimates
    )


def _remaining_text(remaining_budget: Any | None) -> str:
    if remaining_budget is None or remaining_budget.status != "ready":
        return ""
    remaining_kcal = int(remaining_budget.remaining_kcal or 0)
    if remaining_kcal < 0:
        return f"今天超出約 {abs(remaining_kcal)} kcal。"
    return f"今天還剩約 {remaining_kcal} kcal。"


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
            f"已建立你的計畫。TDEE 約 {onboarding_result.target_result.estimated_tdee_kcal} kcal，"
            f"每日目標約 {onboarding_result.target_result.recommended_target_kcal} kcal。"
        )
    if intent_type == "answer_remaining_budget" and remaining_budget is not None:
        if remaining_budget.status == "onboarding_required":
            return "你還沒建立每日目標，所以我目前只能記錄飲食，不能準確回答剩餘熱量。"
        tdee = int(getattr(active_body_plan_view, "estimated_tdee", 0) or 0)
        tdee_prefix = f"TDEE 約 {tdee} kcal。" if tdee > 0 else ""
        return (
            f"{tdee_prefix}今天目標 {remaining_budget.daily_target_kcal} kcal，"
            f"已記錄 {remaining_budget.consumed_kcal} kcal，"
            f"還剩約 {remaining_budget.remaining_kcal} kcal。"
        )
    if intent_type == "set_manual_daily_target" and remaining_budget is not None:
        return (
            f"已把今天目標改成 {remaining_budget.daily_target_kcal} kcal。"
            f"今天已記錄 {remaining_budget.consumed_kcal} kcal，"
            f"還剩約 {remaining_budget.remaining_kcal} kcal。"
        )
    if intent_type == "onboarding_required":
        return "請先在 Body 建立身體資料與每日目標；建立後我就能同步計算今天剩餘熱量。"
    if intent_type == "manager_unavailable":
        return "這次我沒辦法可靠判斷你的意思，所以沒有記錄到日記裡。"
    if intent_type in {"log_meal", "correct_meal"} and nutrition_payload is not None:
        if manager_final_action == "no_commit":
            return "這次我沒有記錄到日記裡。你可以再補一句餐點內容，我再幫你估。"
        component_estimates = list(getattr(nutrition_payload, "component_estimates", []) or [])
        if component_estimates:
            item_parts = _component_text(component_estimates)
            total_kcal = int(getattr(nutrition_payload, "estimated_kcal", 0) or 0)
            if manager_final_action == "ask_followup":
                reply_text = getattr(nutrition_payload, "reply_text", None)
                followup_question = str(getattr(nutrition_payload, "followup_question", None) or "").strip()
                budget_part = ""
                if remaining_budget is not None and remaining_budget.status == "ready":
                    budget_part = f"這餐約 {total_kcal} kcal。{_remaining_text(remaining_budget)}"

                if reply_text and followup_question:
                    digits = [char for char in str(reply_text) if char.isdigit()]
                    has_range = "-" in str(reply_text) or "約" in str(reply_text)
                    if digits and not has_range:
                        return f"{_followup_range_text(estimated_kcal=total_kcal)}{budget_part} {followup_question}"
                if reply_text and followup_question and followup_question not in str(reply_text):
                    return f"{reply_text}{budget_part} {followup_question}"
                if reply_text:
                    return f"{reply_text}{budget_part}"
                if followup_question:
                    return f"{followup_question}{budget_part}"
            logged_prefix = (
                "已記錄："
                if persistence_result is not None and getattr(persistence_result, "canonical_commit", None) is not None
                else ""
            )
            if manager_final_action == "correction_applied":
                return f"已更新上一筆餐點：{item_parts}。這餐約 {total_kcal} kcal。{_remaining_text(remaining_budget)}"
            if remaining_budget is not None and remaining_budget.status == "ready":
                remaining_kcal = int(remaining_budget.remaining_kcal or 0)
                if manager_final_action == "overshoot_note":
                    over_by = abs(int((budget_summary or {}).get("predicted_remaining_kcal_after") or 0))
                    if over_by <= 0:
                        over_by = abs(remaining_kcal)
                    return f"{logged_prefix}{item_parts}。這餐約 {total_kcal} kcal。今天超出約 {over_by} kcal。"
                if remaining_kcal < 0:
                    return f"{logged_prefix}{item_parts}。這餐約 {total_kcal} kcal。今天超出約 {abs(remaining_kcal)} kcal。"
                return f"{logged_prefix}{item_parts}。這餐約 {total_kcal} kcal。今天還剩約 {remaining_kcal} kcal。"
            return f"{logged_prefix}{item_parts}。這餐約 {total_kcal} kcal。"
        if (
            persistence_result is not None
            and getattr(persistence_result, "canonical_commit", None) is None
            and getattr(nutrition_payload, "reply_text", None)
        ):
            return str(nutrition_payload.reply_text)
        if getattr(nutrition_payload, "reply_text", None):
            return str(nutrition_payload.reply_text)
        meal_title = nutrition_payload.meal_title or "meal"
        return f"已記錄 {meal_title}，估計約 {nutrition_payload.estimated_kcal} kcal。"
    return "這次已處理完成，但沒有可顯示的回覆內容。"
