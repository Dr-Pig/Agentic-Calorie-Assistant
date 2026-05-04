from __future__ import annotations

from copy import deepcopy
from typing import Any

FOOD_EVIDENCE_SOURCE_CLASSES: dict[str, dict[str, Any]] = {
    "existing_repo_seed": {
        "role": "current_internal_baseline",
        "can_support": ["candidate_evidence"],
        "confidence_posture": "current_repo_baseline",
        "required_provenance": ["seed_file_path", "record_id"],
        "caveats": ["requires_review_for_expansion"],
        "human_review_required": True,
    },
    "taiwan_tfda_open_data": {
        "role": "generic_taiwan_anchor",
        "can_support": ["generic_anchor"],
        "confidence_posture": "medium_high",
        "required_provenance": ["dataset_name", "retrieved_or_reviewed_date", "food_name"],
        "caveats": ["may_not_match_restaurant_or_vendor_preparation"],
        "human_review_required": True,
    },
    "official_brand_chain_page": {
        "role": "exact_card",
        "can_support": ["exact_item_evidence"],
        "confidence_posture": "high",
        "required_provenance": [
            "source_url",
            "reviewed_date",
            "variant_name",
            "portion_size",
        ],
        "caveats": ["only_valid_for_matching_brand_variant_and_portion"],
        "human_review_required": True,
    },
    "local_taiwan_packaged_extract": {
        "role": "local_packaged_exact_candidate",
        "can_support": ["exact_item_candidate_evidence"],
        "confidence_posture": "medium_high",
        "required_provenance": [
            "source_file",
            "record_id",
            "product_name",
            "package_size",
            "nutrition_basis",
        ],
        "caveats": ["candidate_only_until_exact_review_and portion_match_confirmation"],
        "human_review_required": True,
    },
    "open_food_facts": {
        "role": "packaged_candidate",
        "can_support": ["candidate_only_unless_quality_flags_pass"],
        "confidence_posture": "variable",
        "required_provenance": ["barcode_or_product_id", "retrieved_or_reviewed_date"],
        "requires_quality_flags": True,
        "caveats": ["community_data_quality_varies"],
        "human_review_required": True,
    },
    "usda_fallback": {
        "role": "fallback_generic_normalization",
        "can_support": ["fallback_anchor"],
        "confidence_posture": "medium",
        "required_provenance": ["fdc_id_or_food_name", "retrieved_or_reviewed_date"],
        "caveats": ["non_taiwan_specific"],
        "human_review_required": True,
    },
    "dogfood_user_correction": {
        "role": "review_candidate",
        "can_support": ["gap_candidate", "human_label"],
        "cannot_support_until_approved": ["nutrition_truth", "canonical_eval_truth"],
        "confidence_posture": "pending_review",
        "required_provenance": ["trace_id", "turn_id", "reviewer_id"],
        "caveats": ["observation_not_truth_until_human_review"],
        "human_review_required": True,
    },
}


def build_food_evidence_source_quality_policy() -> dict[str, Any]:
    return {
        "artifact_schema_version": "1.0",
        "artifact_type": "accurate_intake_food_evidence_source_quality_policy",
        "claim_scope": "source_quality_gate_before_food_kb_expansion",
        "source_classes": deepcopy(FOOD_EVIDENCE_SOURCE_CLASSES),
        "promotion_policy": {
            "food_gap_candidate_can_update_truth": False,
            "human_review_required_before_food_kb_truth": True,
            "source_provenance_required": True,
            "source_quality_class_required": True,
        },
        "food_kb_truth_updated": False,
        "nutrition_seed_created": False,
        "exact_card_created": False,
        "packet_truth_created": False,
        "canonical_eval_promoted": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
    }


__all__ = [
    "FOOD_EVIDENCE_SOURCE_CLASSES",
    "build_food_evidence_source_quality_policy",
]
