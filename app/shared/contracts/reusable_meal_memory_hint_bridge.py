from __future__ import annotations

from typing import Any, Mapping


def build_reusable_meal_memory_hint_bridge(
    *,
    memory_summary: Mapping[str, Any],
    reusable_meal_candidate_ids: list[str],
) -> dict[str, Any]:
    suggested_candidate_ids = [
        candidate_id
        for candidate_id in reusable_meal_candidate_ids
        if candidate_id in {
            str(item)
            for item in memory_summary.get("suggested_reusable_meal_candidate_ids") or []
        }
    ]
    return {
        "artifact_type": "shared_reusable_meal_memory_hint_bridge",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "memory_is_not_truth_owner": True,
        "memory_hint_used": bool(suggested_candidate_ids),
        "suggested_candidate_ids": suggested_candidate_ids,
        "candidate_truth_must_be_validated_separately": True,
        "blockers": [],
    }


def build_reusable_meal_memory_hint_bridge_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_reusable_meal_memory_hint_bridge_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "memory_role": "suggest_reusable_meal_candidates_only",
        "memory_must_not_assert_nutrition_truth": True,
        "validator_required_after_memory_hint": True,
        "blockers": [],
    }


__all__ = [
    "build_reusable_meal_memory_hint_bridge",
    "build_reusable_meal_memory_hint_bridge_contract",
]
