from __future__ import annotations

from typing import Any

SOURCE_CLASS_POLICY: dict[str, dict[str, Any]] = {
    "taiwan_tfda_open_data": {
        "default_source_role": "source_evidence_only",
        "allowed_candidate_roles": [
            "source_evidence_only",
            "generic_anchor_candidate",
            "listed_component_candidate",
        ],
        "runtime_truth_allowed_default": False,
        "macro_truth_allowed_default": False,
        "macro_policy": "candidate_macro_only_until_anchor_approval",
        "data_quality_posture": "official_government_dataset",
        "promotion_requires": [
            "source_record_id_preserved",
            "per_100g_denominator_preserved",
            "unit_or_weight_basis_preserved",
            "serving_or_unit_mapping_review",
            "fooddb_batch_approval",
        ],
        "do_not_use_for": [
            "direct_runtime_truth",
            "exact_brand_identity_without_label",
            "generic_common_serving_without_portion_mapping",
            "macro_visibility_without_anchor_approval",
        ],
    },
    "official_brand_chain_page": {
        "default_source_role": "staging_candidate_only",
        "allowed_candidate_roles": ["exact_item_candidate"],
        "runtime_truth_allowed_default": False,
        "macro_truth_allowed_default": False,
        "macro_policy": "label_macro_candidate_only_until_exact_item_approval",
        "data_quality_posture": "official_brand_or_chain_source",
        "promotion_requires": [
            "official_identity_match",
            "serving_size_or_denominator_preserved",
            "kcal_and_macro_label_audit",
            "source_freshness_recorded",
            "fooddb_batch_approval",
        ],
        "do_not_use_for": [
            "direct_runtime_truth",
            "near_match_brand_substitution",
            "generic_anchor_without_separate_serving_mapping",
        ],
    },
    "local_taiwan_packaged_extract": {
        "default_source_role": "staging_candidate_only",
        "allowed_candidate_roles": ["exact_item_candidate"],
        "runtime_truth_allowed_default": False,
        "macro_truth_allowed_default": False,
        "macro_policy": "extract_macro_candidate_only_until_source_audit",
        "data_quality_posture": "local_extract_requires_source_audit",
        "promotion_requires": [
            "original_label_or_official_page_ref",
            "serving_size_or_denominator_preserved",
            "extract_quality_review",
            "fooddb_batch_approval",
        ],
        "do_not_use_for": [
            "direct_runtime_truth",
            "official_source_claim_without_source_ref",
            "macro_visibility_without_label_audit",
        ],
    },
    "open_food_facts": {
        "default_source_role": "raw_source",
        "allowed_candidate_roles": ["user_contributed_packaged_candidate"],
        "runtime_truth_allowed_default": False,
        "macro_truth_allowed_default": False,
        "macro_policy": "user_contributed_candidate_only_until_manual_audit",
        "data_quality_posture": "user_contributed",
        "promotion_requires": [
            "barcode_or_product_identity_match",
            "manual_source_audit",
            "serving_size_or_100g_denominator_preserved",
            "fooddb_batch_approval",
        ],
        "do_not_use_for": [
            "direct_runtime_truth",
            "official_label_claim_without_review",
            "macro_visibility_without_manual_audit",
        ],
    },
    "usda_fallback": {
        "default_source_role": "raw_source",
        "allowed_candidate_roles": ["fallback_source_evidence_only"],
        "runtime_truth_allowed_default": False,
        "macro_truth_allowed_default": False,
        "macro_policy": "fallback_candidate_only_until_local_anchor_review",
        "data_quality_posture": "external_government_dataset",
        "promotion_requires": [
            "fdc_id_and_data_type_preserved",
            "food_matching_review",
            "locale_fallback_reason",
            "unit_denominator_preserved",
            "fooddb_batch_approval",
        ],
        "do_not_use_for": [
            "direct_runtime_truth",
            "taiwan_local_exact_identity",
            "generic_anchor_without_food_matching_review",
        ],
    },
    "existing_repo_seed": {
        "default_source_role": "candidate_only",
        "allowed_candidate_roles": ["alias_coverage_prior"],
        "runtime_truth_allowed_default": False,
        "macro_truth_allowed_default": False,
        "macro_policy": "not_macro_truth",
        "data_quality_posture": "legacy_repo_seed",
        "promotion_requires": [
            "replacement_with_source_backed_record",
            "fooddb_batch_approval",
        ],
        "do_not_use_for": [
            "direct_runtime_truth",
            "source_provenance_claim",
            "macro_visibility",
        ],
    },
}

TFDA_DATASET_URL = "https://data.gov.tw/en/datasets/8543"
TFDA_LICENSE = "Open Government Data License, version 1.0"
USDA_FDC_URL = "https://fdc.nal.usda.gov/index.html"
OFF_API_DOC_URL = "https://openfoodfacts.github.io/documentation/docs/Product-Opener/api/"


def source_policy_fields(
    *,
    source_class: str,
    candidate_role: str,
    source_url_or_origin: str,
    license_or_terms: str,
    macro_support: str,
) -> dict[str, Any]:
    policy = SOURCE_CLASS_POLICY[source_class]
    return {
        "candidate_role": candidate_role,
        "source_url_or_origin": source_url_or_origin,
        "license_or_terms": license_or_terms,
        "macro_support": macro_support,
        "promotion_requires": tuple(policy["promotion_requires"]),
        "do_not_use_for": tuple(policy["do_not_use_for"]),
    }


__all__ = [
    "OFF_API_DOC_URL",
    "SOURCE_CLASS_POLICY",
    "TFDA_DATASET_URL",
    "TFDA_LICENSE",
    "USDA_FDC_URL",
    "source_policy_fields",
]
