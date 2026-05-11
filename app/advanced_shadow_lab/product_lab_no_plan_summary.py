from __future__ import annotations

from typing import Any, Mapping


def turn_no_plan_summary(turn_artifact: Mapping[str, Any]) -> dict[str, Any]:
    no_plan = _mapping(turn_artifact.get("product_lab_no_plan_degraded_artifact"))
    today = _mapping(no_plan.get("today_ui_mirror"))
    budget = _mapping(no_plan.get("budget_query_packet"))
    active = no_plan.get("status") == "pass"
    return {
        "lab_no_plan_degraded_turn": active,
        "lab_no_plan_intake_logging_allowed": (
            no_plan.get("intake_logging_allowed_without_plan") is True
        ),
        "lab_no_plan_budget_query_degraded": budget.get("status") == "onboarding_required",
        "lab_no_plan_today_ui_hides_target_and_remaining": (
            today.get("daily_target_visible") is False
            and today.get("remaining_budget_visible") is False
            and today.get("daily_target_kcal") is None
            and today.get("remaining_kcal") is None
        ),
        "lab_no_plan_onboarding_cta_visible": bool(
            _mapping(budget.get("onboarding_cta")).get("action")
        ),
    }


def session_no_plan_summary(turn_summaries: list[Mapping[str, Any]]) -> dict[str, Any]:
    rows = [item for item in turn_summaries if item.get("lab_no_plan_degraded_turn") is True]
    return {
        "lab_no_plan_degraded_turn_count": len(rows),
        "lab_no_plan_intake_logging_allowed": _any(rows, "lab_no_plan_intake_logging_allowed"),
        "lab_no_plan_budget_query_degraded": _any(rows, "lab_no_plan_budget_query_degraded"),
        "lab_no_plan_today_ui_hides_target_and_remaining": _any(
            rows,
            "lab_no_plan_today_ui_hides_target_and_remaining",
        ),
        "lab_no_plan_onboarding_cta_visible": _any(rows, "lab_no_plan_onboarding_cta_visible"),
    }


def _any(rows: list[Mapping[str, Any]], key: str) -> bool:
    return any(item.get(key) is True for item in rows)


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["session_no_plan_summary", "turn_no_plan_summary"]
