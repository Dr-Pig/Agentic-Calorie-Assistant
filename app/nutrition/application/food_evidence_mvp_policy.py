from __future__ import annotations

from typing import Any


def build_food_evidence_mvp_policy_manifest() -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_mvp_policy_manifest",
        "claim_scope": "food_evidence_policy_before_first_truth_promotion",
        "estimate_output_policy": {
            "exact_card": {
                "output": "point_kcal",
                "only_when": [
                    "official_or_existing_exact_card_source",
                    "brand_variant_matches",
                    "portion_size_matches",
                    "item_level_human_approval",
                ],
            },
            "generic_taiwan_anchor": {
                "output": "point_kcal_plus_uncertainty_range",
                "requires": [
                    "source_class_compatible_with_generic_anchor",
                    "source_provenance_complete",
                    "portion_default_reviewed",
                    "item_level_human_approval",
                ],
            },
        },
        "basket_policy": {
            "bare_basket": {
                "manager_expected_posture": "ask_followup",
                "estimate_allowed": False,
                "mutation_allowed": False,
            },
            "listed_basket": {
                "manager_expected_posture": "estimate_components",
                "estimate_allowed_only_if": "approved_component_evidence_exists",
                "component_truth_required": True,
            },
        },
        "source_posture": {
            "existing_repo_seed": "current_baseline_requires_review_for_expansion",
            "taiwan_tfda_open_data": "generic_taiwan_anchor_support",
            "official_brand_chain_page": "exact_card_support_when_variant_and_portion_match",
            "open_food_facts": "packaged_candidate_only",
            "usda_fallback": "fallback_generic_normalization_only",
            "dogfood_user_correction": "review_candidate_only",
        },
        "truth_promotion_policy": {
            "approval_unit": "item_level",
            "family_level_bulk_approval_allowed": False,
            "human_approval_required": True,
            "llm_extraction_can_approve": False,
            "deterministic_policy_can_create_truth": False,
        },
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "not_claiming": [
            "fooddb_truth_promoted",
            "one_day_dogfood_pass",
            "product_readiness",
            "private_self_use_approval",
        ],
    }


def evaluate_food_evidence_mvp_policy_request(request: dict[str, Any]) -> dict[str, Any]:
    requested_truth_type = str(request.get("requested_truth_type") or "")
    source_class = str(request.get("source_class") or "")
    blockers: list[str] = []

    if request.get("human_review_status") != "approved" or not request.get(
        "item_level_approval_id"
    ):
        blockers.append("item_level_human_approval_required")

    if source_class == "open_food_facts":
        blockers.append("open_food_facts_is_packaged_candidate_only")
    if source_class == "usda_fallback" and requested_truth_type == "exact_card":
        blockers.append("usda_fallback_cannot_create_exact_card")
    if source_class == "dogfood_user_correction":
        blockers.append("dogfood_user_correction_is_review_candidate_only")

    if requested_truth_type == "generic_taiwan_anchor":
        if source_class not in {"existing_repo_seed", "taiwan_tfda_open_data", "usda_fallback"}:
            blockers.append("source_class_not_compatible_with_generic_anchor")
        if request.get("has_point_kcal") is not True:
            blockers.append("point_kcal_required")
        if request.get("has_uncertainty_range") is not True:
            blockers.append("uncertainty_range_required")
        if request.get("portion_default_reviewed") is not True:
            blockers.append("portion_default_review_required")
    elif requested_truth_type == "exact_card":
        if source_class not in {"existing_repo_seed", "official_brand_chain_page"}:
            blockers.append("source_class_not_compatible_with_exact_card")
        if request.get("brand_variant_matches") is not True:
            blockers.append("brand_variant_match_required")
        if request.get("portion_size_matches") is not True:
            blockers.append("portion_size_match_required")
    else:
        blockers.append("unsupported_requested_truth_type")

    return {
        "candidate_id": request.get("candidate_id"),
        "requested_truth_type": requested_truth_type,
        "source_class": source_class,
        "policy_allows_future_truth_promotion": not blockers,
        "blockers": blockers,
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
    }


__all__ = [
    "build_food_evidence_mvp_policy_manifest",
    "evaluate_food_evidence_mvp_policy_request",
]
