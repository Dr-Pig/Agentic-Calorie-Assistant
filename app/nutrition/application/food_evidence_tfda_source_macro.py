from __future__ import annotations

from typing import Any

from app.nutrition.application.food_evidence_candidate_macro_validation import (
    MACRO_SCHEMA_FIELDS,
)

SOURCE_EVIDENCE_MACRO_FIELDS = (
    "protein_g_per_100g",
    "carbs_g_per_100g",
    "fat_g_per_100g",
    "source_denominator",
    "macro_basis",
    "macro_confidence",
    "macro_source_strength",
    "macro_visibility_candidate",
    "macro_null_reason",
    "macro_truth_allowed",
)


def source_evidence_macro_fields(candidate: dict[str, Any]) -> dict[str, Any]:
    macro_candidate = _macro_candidate_fields(candidate)
    return {
        "protein_g_per_100g": macro_candidate["protein_g_point"],
        "carbs_g_per_100g": macro_candidate["carbs_g_point"],
        "fat_g_per_100g": macro_candidate["fat_g_point"],
        "source_denominator": _source_denominator(candidate.get("serving_basis")),
        "macro_basis": macro_candidate["macro_basis"],
        "macro_confidence": macro_candidate["macro_confidence"],
        "macro_source_strength": macro_candidate["macro_source_strength"],
        "macro_visibility_candidate": macro_candidate["macro_visibility_candidate"],
        "macro_null_reason": macro_candidate["macro_null_reason"],
        "macro_truth_allowed": False,
    }


def _macro_candidate_fields(candidate: dict[str, Any]) -> dict[str, Any]:
    if all(field in candidate for field in MACRO_SCHEMA_FIELDS):
        return {field: candidate.get(field) for field in MACRO_SCHEMA_FIELDS}
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


def _source_denominator(serving_basis: Any) -> str:
    if isinstance(serving_basis, dict):
        label = str(serving_basis.get("label") or "").strip()
        if label:
            return label
    return "per_100g_edible_portion"


__all__ = ["SOURCE_EVIDENCE_MACRO_FIELDS", "source_evidence_macro_fields"]
