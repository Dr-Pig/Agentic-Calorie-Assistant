from __future__ import annotations

from typing import Any

from app.nutrition.application.fooddb_macro_contract import build_macro_review_policy

FIRST_BATCH_REVIEW_FAMILIES = [
    "breakfast_combo",
    "chicken_bento_rice_modifier",
    "bubble_tea_sugar_size_modifier",
    "luwei_listed_components",
]


def build_fooddb_quality_improvement_plan(
    *,
    inventory: dict[str, Any],
    food_gap_register: dict[str, Any] | None = None,
) -> dict[str, Any]:
    macro_review_policy = build_macro_review_policy()
    return {
        "artifact_type": "accurate_intake_fooddb_quality_improvement_plan",
        "artifact_schema_version": "1.0",
        "claim_scope": "fooddb_quality_planning_before_truth_promotion",
        "inventory_snapshot": {
            "repo_contained_seed_counts": dict(inventory.get("repo_contained_seed_counts") or {}),
            "missing_source_metadata_count": int(inventory.get("missing_source_metadata_count") or 0),
        },
        "food_gap_register_summary": _gap_register_summary(food_gap_register or {}),
        "first_batch_review_families": list(FIRST_BATCH_REVIEW_FAMILIES),
        "first_batch_macro_review_policy": macro_review_policy,
        "first_batch_review_packets": [
            {
                "gap_family": family,
                "status": "review_packet_only",
                "promotion_allowed": False,
                "macro_review_policy": dict(macro_review_policy),
                "requires": [
                    "source_class_selection",
                    "complete_provenance",
                    "human_review_approval",
                    "promotion_policy_pass",
                ],
            }
            for family in FIRST_BATCH_REVIEW_FAMILIES
        ],
        "later_truth_promotion_acceptance": [
            "source_quality_policy_green",
            "human_review_approved",
            "promotion_policy_allows_requested_stage",
            "source_metadata_complete",
            "food_seed_support_only_tests_green",
            "one_day_dogfood_rerun_after_truth_promotion",
        ],
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "bulk_food_db_expansion": False,
        "not_claiming": [
            "fooddb_quality_complete",
            "first_batch_truth_promoted",
            "one_day_dogfood_pass",
            "product_readiness",
        ],
    }


def _gap_register_summary(food_gap_register: dict[str, Any]) -> dict[str, Any]:
    candidates = [
        candidate
        for candidate in list(food_gap_register.get("food_gap_candidates") or [])
        if isinstance(candidate, dict)
    ]
    family_counts: dict[str, int] = {}
    for candidate in candidates:
        family = str(candidate.get("gap_family") or "unknown")
        family_counts[family] = family_counts.get(family, 0) + 1
    return {
        "candidate_count": len(candidates),
        "gap_candidates_by_family": family_counts,
        "promotion_ready_count": sum(1 for candidate in candidates if candidate.get("promotion_allowed") is True),
    }


__all__ = ["FIRST_BATCH_REVIEW_FAMILIES", "build_fooddb_quality_improvement_plan"]
