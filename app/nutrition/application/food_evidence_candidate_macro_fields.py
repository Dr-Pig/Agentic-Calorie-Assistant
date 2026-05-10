from __future__ import annotations

from typing import Any

from app.nutrition.application.food_evidence_candidate_record_values import (
    first_text,
    number,
)

MACRO_POINT_FIELDS = {
    "protein_g_point": ("protein_g", "protein", "proteins_100g", "protein_g_100g"),
    "carbs_g_point": (
        "carbs_g",
        "carb_g",
        "carbohydrates_100g",
        "carbohydrate_g",
        "carbohydrates_g",
    ),
    "fat_g_point": ("fat_g", "fat", "fat_100g", "total_fat_g"),
}


def macro_fields_for_candidate(
    *,
    raw_record: dict[str, Any],
    serving_basis: dict[str, Any],
) -> dict[str, Any]:
    macro_points = {
        field: _macro_value(raw_record, keys)
        for field, keys in MACRO_POINT_FIELDS.items()
    }
    present_count = sum(value is not None for value in macro_points.values())
    if present_count == 0:
        return _missing_macro_fields()

    return {
        **macro_points,
        "protein_g_range": None,
        "carbs_g_range": None,
        "fat_g_range": None,
        "macro_basis": _macro_basis(raw_record, serving_basis),
        "macro_confidence": first_text(raw_record, ("macro_confidence", "confidence"))
        or "candidate",
        "macro_source_strength": "source_declared_candidate",
        "macro_visibility_candidate": (
            "hidden_until_approval"
            if present_count == len(MACRO_POINT_FIELDS)
            else "partial_candidate_pending_review"
        ),
        "macro_null_reason": None
        if present_count == len(MACRO_POINT_FIELDS)
        else "partial_source_macro",
    }


def _missing_macro_fields() -> dict[str, Any]:
    return {
        "protein_g_point": None,
        "protein_g_range": None,
        "carbs_g_point": None,
        "carbs_g_range": None,
        "fat_g_point": None,
        "fat_g_range": None,
        "macro_basis": "unknown",
        "macro_confidence": "unknown",
        "macro_source_strength": "unavailable",
        "macro_visibility_candidate": "hidden_missing_source",
        "macro_null_reason": "missing_source_macro",
    }


def _macro_value(raw_record: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    direct = _first_number(raw_record, keys)
    if direct is not None:
        return direct

    nutrition = raw_record.get("nutrition")
    if isinstance(nutrition, dict):
        nested = _first_number(nutrition, keys)
        if nested is not None:
            return nested

    nutriments = raw_record.get("nutriments")
    if isinstance(nutriments, dict):
        nested = _first_number(nutriments, keys)
        if nested is not None:
            return nested

    nutrients = raw_record.get("foodNutrients")
    if isinstance(nutrients, list):
        return _usda_macro_value(nutrients, keys)
    return None


def _first_number(record: dict[str, Any], keys: tuple[str, ...]) -> float | None:
    normalized = {_normalize_key(key): value for key, value in record.items()}
    for key in keys:
        value = number(normalized.get(_normalize_key(key)))
        if value is not None:
            return value
    return None


def _usda_macro_value(nutrients: list[Any], keys: tuple[str, ...]) -> float | None:
    aliases = {_normalize_key(key) for key in keys}
    for nutrient in nutrients:
        if not isinstance(nutrient, dict):
            continue
        unit_name = str(nutrient.get("unitName") or "").upper()
        if unit_name != "G":
            continue
        nutrient_name = _normalize_key(nutrient.get("nutrientName"))
        if any(alias in nutrient_name or nutrient_name in alias for alias in aliases):
            value = number(nutrient.get("value"))
            if value is not None:
                return value
    return None


def _macro_basis(raw_record: dict[str, Any], serving_basis: dict[str, Any]) -> str:
    return (
        first_text(raw_record, ("macro_basis", "nutrition_basis"))
        or str(serving_basis.get("label") or "").strip()
        or "unknown"
    )


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().casefold().replace("-", "_").replace(" ", "_")


__all__ = ["macro_fields_for_candidate"]
