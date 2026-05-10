from __future__ import annotations

from typing import Any

MACRO_SCHEMA_FIELDS = (
    "protein_g_point",
    "protein_g_range",
    "carbs_g_point",
    "carbs_g_range",
    "fat_g_point",
    "fat_g_range",
    "macro_basis",
    "macro_confidence",
    "macro_source_strength",
    "macro_visibility_candidate",
    "macro_null_reason",
)
MACRO_POINT_FIELDS = ("protein_g_point", "carbs_g_point", "fat_g_point")
MACRO_RANGE_FIELDS = ("protein_g_range", "carbs_g_range", "fat_g_range")
MACRO_VISIBILITY_CANDIDATES = {
    "hidden_missing_source",
    "hidden_until_approval",
    "partial_candidate_pending_review",
}


def macro_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return {field: candidate.get(field) for field in MACRO_SCHEMA_FIELDS}


def macro_validation_reasons(candidate: dict[str, Any]) -> list[str]:
    if any(field not in candidate for field in MACRO_SCHEMA_FIELDS):
        return ["missing_macro_schema"]

    visibility = str(candidate.get("macro_visibility_candidate") or "")
    if visibility not in MACRO_VISIBILITY_CANDIDATES:
        return ["macro_visibility_candidate_invalid"]

    reasons: list[str] = []
    point_values = [candidate.get(field) for field in MACRO_POINT_FIELDS]
    range_values = [candidate.get(field) for field in MACRO_RANGE_FIELDS]
    present_point_count = sum(value is not None for value in point_values)
    present_range_count = sum(value is not None for value in range_values)

    if visibility == "hidden_missing_source":
        if present_point_count or present_range_count:
            reasons.append("hidden_missing_macro_has_value")
        if str(candidate.get("macro_null_reason") or "") != "missing_source_macro":
            reasons.append("hidden_missing_macro_null_reason_invalid")
    elif visibility == "hidden_until_approval":
        if present_point_count != len(MACRO_POINT_FIELDS):
            reasons.append("macro_candidate_missing_required_points")
        if candidate.get("macro_null_reason") is not None:
            reasons.append("macro_candidate_null_reason_must_be_null")
    elif visibility == "partial_candidate_pending_review":
        if present_point_count == 0 or present_point_count == len(MACRO_POINT_FIELDS):
            reasons.append("partial_macro_candidate_point_count_invalid")
        if str(candidate.get("macro_null_reason") or "") != "partial_source_macro":
            reasons.append("partial_macro_null_reason_invalid")

    for field in (*MACRO_POINT_FIELDS, *MACRO_RANGE_FIELDS):
        value = candidate.get(field)
        if value is not None and not _valid_non_negative_number(value):
            reasons.append(f"invalid_macro_value:{field}")
    return reasons


def _valid_non_negative_number(value: Any) -> bool:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return False
    return number >= 0


__all__ = ["macro_projection", "macro_validation_reasons"]
