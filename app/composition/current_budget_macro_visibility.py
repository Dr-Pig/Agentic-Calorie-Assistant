from __future__ import annotations

from typing import Any

from app.intake.infrastructure.models import MealItemRecord, MealVersionRecord
from app.runtime.application.execution_guard import evaluate_macro_display
from app.shared.domain import CurrentBudgetMealSummary


def build_meal_macro_summary(version: MealVersionRecord, items: list[MealItemRecord]) -> dict[str, Any]:
    if not items:
        return _hidden_macro("no_macro_data")
    item_summaries = [_item_macro_summary(item) for item in items]
    visible_count = sum(1 for summary in item_summaries if summary["display_status"] == "show")
    if visible_count == 0:
        if _version_has_authorized_macro_evidence(items):
            return _version_macro_summary(version)
        return _hidden_macro(_hidden_reason(item_summaries))
    values = _summed_visible_macros(item_summaries)
    if visible_count < len(item_summaries):
        return {
            "display_status": "partial",
            "guard_reason": "partial_meal_macro",
            "source_basis": "canonical_item_evidence",
            **values,
        }
    display = evaluate_macro_display(
        estimated_kcal=int(version.total_kcal or 0),
        protein_g=values["protein_g"],
        carb_g=values["carb_g"],
        fat_g=values["fat_g"],
    )
    if display.display_status != "show":
        return _hidden_macro(display.guard_reason)
    return {
        "display_status": "show",
        "guard_reason": display.guard_reason,
        "source_basis": "canonical_item_evidence",
        **values,
    }


def build_day_macro_summary(meals: list[CurrentBudgetMealSummary]) -> dict[str, Any]:
    visible_meals = [meal for meal in meals if meal.macro_display_status in {"show", "partial"}]
    if not visible_meals:
        return _hidden_macro(
            _hidden_reason([{"guard_reason": meal.macro_guard_reason} for meal in meals])
        )
    values = {
        "protein_g": sum(int(meal.consumed_protein or 0) for meal in visible_meals),
        "carb_g": sum(int(meal.consumed_carbs or 0) for meal in visible_meals),
        "fat_g": sum(int(meal.consumed_fat or 0) for meal in visible_meals),
        "eligible_kcal": sum(int(meal.total_kcal or 0) for meal in visible_meals),
    }
    if len(visible_meals) < len(meals) or any(meal.macro_display_status == "partial" for meal in visible_meals):
        return {
            "display_status": "partial",
            "guard_reason": "partial_day_macro",
            "source_basis": "canonical_item_evidence",
            **values,
        }
    display = evaluate_macro_display(
        estimated_kcal=sum(int(meal.total_kcal or 0) for meal in meals),
        protein_g=values["protein_g"],
        carb_g=values["carb_g"],
        fat_g=values["fat_g"],
    )
    if display.display_status != "show":
        return _hidden_macro(display.guard_reason)
    return {
        "display_status": "show",
        "guard_reason": display.guard_reason,
        "source_basis": "canonical_item_evidence",
        **values,
    }


def _version_macro_summary(version: MealVersionRecord) -> dict[str, Any]:
    display = evaluate_macro_display(
        estimated_kcal=int(version.total_kcal or 0),
        protein_g=int(version.protein_g or 0),
        carb_g=int(version.carb_g or 0),
        fat_g=int(version.fat_g or 0),
    )
    if display.display_status != "show":
        return _hidden_macro(display.guard_reason)
    return {
        "display_status": "show",
        "guard_reason": display.guard_reason,
        "source_basis": "authorized_version_macro_evidence",
        "protein_g": int(version.protein_g or 0),
        "carb_g": int(version.carb_g or 0),
        "fat_g": int(version.fat_g or 0),
        "eligible_kcal": int(version.total_kcal or 0),
    }


def _item_macro_summary(item: MealItemRecord) -> dict[str, Any]:
    if not _has_macro_values(item):
        return _hidden_macro("no_macro_data")
    evidence_ids = item.evidence_ids_json if isinstance(item.evidence_ids_json, list) else []
    if not evidence_ids:
        return _hidden_macro("unsupported_macro_source")
    display = evaluate_macro_display(
        estimated_kcal=int(item.estimated_kcal or 0),
        protein_g=int(item.protein_g or 0),
        carb_g=int(item.carb_g or 0),
        fat_g=int(item.fat_g or 0),
    )
    if display.display_status != "show":
        return _hidden_macro(display.guard_reason)
    return {
        "display_status": "show",
        "guard_reason": display.guard_reason,
        "source_basis": "canonical_item_evidence",
        "protein_g": int(item.protein_g or 0),
        "carb_g": int(item.carb_g or 0),
        "fat_g": int(item.fat_g or 0),
        "eligible_kcal": int(item.estimated_kcal or 0),
    }


def _has_macro_values(item: MealItemRecord) -> bool:
    return any((item.protein_g, item.carb_g, item.fat_g))


def _version_has_authorized_macro_evidence(items: list[MealItemRecord]) -> bool:
    for item in items:
        evidence_ids = item.evidence_ids_json if isinstance(item.evidence_ids_json, list) else []
        if any(str(evidence_id).startswith("display_macro_breakdown:") for evidence_id in evidence_ids):
            return True
    return False


def _hidden_macro(reason: str) -> dict[str, Any]:
    return {
        "display_status": "hide",
        "guard_reason": reason,
        "source_basis": "unavailable",
        "protein_g": 0,
        "carb_g": 0,
        "fat_g": 0,
        "eligible_kcal": 0,
    }


def _summed_visible_macros(items: list[dict[str, Any]]) -> dict[str, int]:
    visible = [item for item in items if item["display_status"] == "show"]
    return {
        "protein_g": sum(int(item["protein_g"]) for item in visible),
        "carb_g": sum(int(item["carb_g"]) for item in visible),
        "fat_g": sum(int(item["fat_g"]) for item in visible),
        "eligible_kcal": sum(int(item["eligible_kcal"]) for item in visible),
    }


def _hidden_reason(summaries: list[dict[str, Any]]) -> str:
    reasons = {str(summary.get("guard_reason") or "") for summary in summaries}
    if "macro_alignment_fail" in reasons:
        return "macro_alignment_fail"
    if "unsupported_macro_source" in reasons:
        return "unsupported_macro_source"
    return "no_macro_data"


__all__ = ["build_day_macro_summary", "build_meal_macro_summary"]
