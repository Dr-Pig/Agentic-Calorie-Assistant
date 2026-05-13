from __future__ import annotations

from typing import Any


def canonical_b1_case_family(case_family: str) -> str:
    return {
        "exact_item_macro_present": "common_food_item",
        "generic_common_drink_macro_missing": "common_commercial_drink",
        "common_commercial_meal_macro_missing": "common_commercial_meal",
        "listed_ingredient_basket_macro_missing": "listed_ingredient_basket",
    }.get(case_family, case_family)


def b1_case_family_from_packet_fields(
    *,
    case_id: str,
    expected_behavior: str,
    evidence_items: list[Any],
) -> str:
    if expected_behavior == "ask_followup_no_mutation" or not evidence_items:
        return "composition_unknown_self_selected_basket"
    if expected_behavior == "estimate_listed_components_only":
        return "listed_ingredient_basket"
    if expected_behavior == "generic_range_estimate_with_followup_hints":
        return "common_commercial_meal"
    if "boba" in case_id or expected_behavior in {
        "estimate_from_packet_with_uncertainty",
        "estimate_or_confirm_from_fuzzy_packet",
    }:
        return "common_commercial_drink"
    return "common_food_item"


__all__ = ["b1_case_family_from_packet_fields", "canonical_b1_case_family"]
