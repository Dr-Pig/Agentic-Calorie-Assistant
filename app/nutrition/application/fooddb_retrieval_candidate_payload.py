from __future__ import annotations

from typing import Any

from .fooddb_retrieval_records import IndexedFoodRecord


MODIFIER_VALUE_EQUIVALENTS = {
    "rice_portion": {
        "less_rice": {"half", "small"},
        "half_rice": {"half", "small"},
    },
}


def _candidate_payload(
    match: dict[str, Any],
    *,
    query_component: str,
    modifier_hints: dict[str, str],
) -> dict[str, Any]:
    record: IndexedFoodRecord = match["record"]
    modifier_compatibility = _modifier_compatibility(record, modifier_hints)
    return {
        "anchor_id": record.anchor_id,
        "canonical_name": record.canonical_name,
        "query_component": query_component,
        "match_path": match["match_path"],
        "match_score": match["score"],
        "confidence": match["confidence"],
        "requires_manager_disambiguation": match["requires_manager_disambiguation"],
        "runtime_truth_allowed": record.runtime_truth_allowed,
        "runtime_role": record.runtime_role,
        "source_lane": record.source_lane,
        "kcal_point": record.kcal_point,
        "kcal_range": list(record.kcal_range) if record.kcal_range else None,
        "protein_g": record.protein_g,
        "carbs_g": record.carbs_g,
        "fat_g": record.fat_g,
        "macro_visibility_status": record.macro_visibility_status,
        "macro_source_basis": record.macro_source_basis,
        "macro_confidence": record.macro_confidence,
        "serving_basis": record.serving_basis,
        "portion_basis": record.portion_basis,
        "runtime_usage_boundary": record.runtime_usage_boundary,
        "followup_hints": list(record.followup_hints),
        "source_provenance": record.source_provenance,
        "approval_metadata": record.approval_metadata,
        "modifier_compatibility": modifier_compatibility,
        "ranking_reasons": _ranking_reasons(
            match,
            record=record,
            modifier_compatibility=modifier_compatibility,
        ),
    }


def _modifier_compatibility(
    record: IndexedFoodRecord,
    modifier_hints: dict[str, str],
) -> dict[str, str]:
    compatibility: dict[str, str] = {}
    modifier_values = {
        str(modifier.get("name") or ""): {str(value) for value in modifier.get("values") or []}
        for modifier in record.major_modifiers
        if isinstance(modifier, dict)
    }
    for modifier_name, modifier_value in modifier_hints.items():
        supported_values = modifier_values.get(modifier_name)
        equivalent_values = MODIFIER_VALUE_EQUIVALENTS.get(modifier_name, {}).get(
            modifier_value,
            set(),
        )
        if supported_values and modifier_value in supported_values:
            compatibility[modifier_name] = "compatible"
        elif supported_values and bool(equivalent_values & supported_values):
            compatibility[modifier_name] = "compatible_via_normalized_equivalent"
        else:
            compatibility[modifier_name] = "unsupported"
    return compatibility


def _ranking_reasons(
    match: dict[str, Any],
    *,
    record: IndexedFoodRecord,
    modifier_compatibility: dict[str, str],
) -> list[str]:
    reasons = [str(match["match_path"])]
    if record.runtime_truth_allowed:
        reasons.append("runtime_truth_allowed")
    if record.source_lane:
        reasons.append(f"source_lane:{record.source_lane}")
    if record.kcal_range:
        reasons.append("kcal_range_present")
    if record.serving_basis and record.serving_basis != "not_applicable":
        reasons.append("serving_basis_present")
    if record.portion_basis and record.portion_basis != "not_applicable":
        reasons.append("portion_basis_present")
    for modifier_name, status in modifier_compatibility.items():
        if status == "compatible":
            reasons.append(f"modifier_compatible:{modifier_name}")
    return reasons


def _rank_candidates(candidates: list[dict[str, Any]]) -> list[dict[str, Any]]:
    def key(item: dict[str, Any]) -> tuple[int, int, int, int, int, int, int, int, int, int, str]:
        path_rank = {
            "canonical_or_alias_exact": 0,
            "canonical_or_alias_substring": 1,
            "alias_expansion_exact": 2,
            "fuzzy_alias_expansion": 3,
            "fuzzy_alias": 4,
        }.get(str(item.get("match_path")), 9)
        modifier_compatibility = item.get("modifier_compatibility") or {}
        if not isinstance(modifier_compatibility, dict):
            modifier_compatibility = {}
        unsupported_modifier_count = sum(
            1 for status in modifier_compatibility.values() if status == "unsupported"
        )
        compatible_modifier_count = sum(
            1 for status in modifier_compatibility.values() if status == "compatible"
        )
        source_quality_score = 1 if item.get("source_provenance") else 0
        runtime_truth_score = 1 if item.get("runtime_truth_allowed") is True else 0
        serving_basis_score = 1 if item.get("serving_basis") else 0
        portion_basis_score = 1 if item.get("portion_basis") else 0
        ambiguity_penalty = 1 if item.get("requires_manager_disambiguation") else 0
        source_lane_rank = {
            "exact_item_card": 0,
            "generic_common_serving": 1,
            "listed_component": 2,
            "basket_family_semantic_only": 9,
        }.get(str(item.get("source_lane") or ""), 5)
        return (
            path_rank,
            unsupported_modifier_count,
            -compatible_modifier_count,
            source_lane_rank,
            -runtime_truth_score,
            -source_quality_score,
            -serving_basis_score,
            -portion_basis_score,
            -int(item.get("match_score") or 0),
            ambiguity_penalty,
            str(item.get("anchor_id") or ""),
        )

    return sorted(candidates, key=key)


def _ambiguity_reason(accepted: list[dict[str, Any]]) -> str | None:
    if len(accepted) <= 1:
        return None
    return "multiple_retrieval_candidates_require_manager_disambiguation"


def _vector_search_policy() -> dict[str, Any]:
    return {
        "allowed_for": "candidate_recall_later_only",
        "forbidden_for": [
            "truth_selection",
            "kcal_decision",
            "runtime_mutation",
        ],
    }


def _ranking_policy() -> dict[str, Any]:
    return {
        "features": [
            "lexical_match",
            "source_lane",
            "runtime_truth_allowed",
            "source_quality",
            "serving_basis",
            "portion_basis",
            "modifier_compatibility",
            "ambiguity_risk",
        ],
        "truth_selection": "forbidden",
        "manager_role": "disambiguate_or_synthesize_from_candidates",
    }
