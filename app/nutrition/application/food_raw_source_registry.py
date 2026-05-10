from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.nutrition.application.food_raw_source_policy import (
    OFF_API_DOC_URL,
    SOURCE_CLASS_POLICY,
    TFDA_DATASET_URL,
    TFDA_LICENSE,
    USDA_FDC_URL,
)

NON_CLAIM_FLAGS = {
    "food_kb_truth_updated": False,
    "nutrition_seed_created": False,
    "exact_card_created": False,
    "packet_truth_created": False,
    "canonical_eval_promoted": False,
}


@dataclass(frozen=True)
class RawSourceDefinition:
    source_id: str
    filename: str
    source_class: str
    intended_roles: tuple[str, ...]
    source_role: str = "raw_source"
    candidate_role: str = "source_evidence_only"
    source_url_or_origin: str = ""
    license_or_terms: str = ""
    macro_support: str = "unknown_or_candidate_only"
    promotion_requires: tuple[str, ...] = ()
    do_not_use_for: tuple[str, ...] = ()
    runtime_truth: bool = False
    runtime_truth_allowed_default: bool = False
    macro_truth_allowed_default: bool = False
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "filename": self.filename,
            "source_class": self.source_class,
            "source_class_policy_ref": self.source_class,
            "source_role": self.source_role,
            "candidate_role": self.candidate_role,
            "intended_roles": list(self.intended_roles),
            "source_url_or_origin": self.source_url_or_origin,
            "license_or_terms": self.license_or_terms,
            "macro_support": self.macro_support,
            "promotion_requires": list(self.promotion_requires),
            "do_not_use_for": list(self.do_not_use_for),
            "runtime_truth": self.runtime_truth,
            "runtime_truth_allowed_default": self.runtime_truth_allowed_default,
            "macro_truth_allowed_default": self.macro_truth_allowed_default,
            "notes": self.notes,
        }


# Preserve legacy introspection/pickle identity after moving the implementation.
RawSourceDefinition.__module__ = "app.nutrition.application.food_raw_source_inventory"


RAW_SOURCE_DEFINITIONS: tuple[RawSourceDefinition, ...] = (
    RawSourceDefinition(
        source_id="tfda_fda_food_nutrition_2024",
        filename="FDA_food_nutrition_2024.xlsx",
        source_class="taiwan_tfda_open_data",
        candidate_role="source_evidence_only",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        source_url_or_origin=TFDA_DATASET_URL,
        license_or_terms=TFDA_LICENSE,
        macro_support="per_100g_and_per_unit_source_evidence_candidate",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["do_not_use_for"]),
        notes="TFDA/FDA nutrition Excel inventory only; not packet truth.",
    ),
    RawSourceDefinition(
        source_id="tfda_tnfcds_consumer_detail",
        filename="tnfcds_consumer_detail.xlsx",
        source_class="taiwan_tfda_open_data",
        candidate_role="source_evidence_only",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        source_url_or_origin=TFDA_DATASET_URL,
        license_or_terms=TFDA_LICENSE,
        macro_support="per_100g_and_per_unit_source_evidence_candidate",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["do_not_use_for"]),
        notes="TNFCDS consumer detail raw/staging source inventory only.",
    ),
    RawSourceDefinition(
        source_id="tfda_tnfcds_consumer_items",
        filename="tnfcds_consumer_items.xlsx",
        source_class="taiwan_tfda_open_data",
        candidate_role="source_evidence_only",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        source_url_or_origin=TFDA_DATASET_URL,
        license_or_terms=TFDA_LICENSE,
        macro_support="per_100g_and_per_unit_source_evidence_candidate",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["do_not_use_for"]),
        notes="TNFCDS consumer items raw/staging source inventory only.",
    ),
    RawSourceDefinition(
        source_id="newtaipei_brand_candidates",
        filename="newtaipei_brand_candidates.json",
        source_class="official_brand_chain_page",
        source_role="staging_candidate_only",
        candidate_role="exact_item_candidate",
        intended_roles=("exact_card_candidate",),
        source_url_or_origin="local_staged_official_brand_page_extract",
        license_or_terms="source-specific official page terms; manual audit required",
        macro_support="label_macro_candidate_if_source_provides_it",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["official_brand_chain_page"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["official_brand_chain_page"]["do_not_use_for"]),
        notes="Official page-derived brand candidates only; no runtime truth.",
    ),
    RawSourceDefinition(
        source_id="local_tw_packaged_extract_188_2",
        filename="188_2.csv",
        source_class="local_taiwan_packaged_extract",
        source_role="staging_candidate_only",
        candidate_role="exact_item_candidate",
        intended_roles=("exact_card_candidate",),
        source_url_or_origin="local_staged_packaged_product_extract",
        license_or_terms="source-specific label or page terms; manual audit required",
        macro_support="extracted_label_macro_candidate_if_source_provides_it",
        promotion_requires=tuple(
            SOURCE_CLASS_POLICY["local_taiwan_packaged_extract"]["promotion_requires"]
        ),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["local_taiwan_packaged_extract"]["do_not_use_for"]),
        notes=(
            "Local extracted CSV packaged-product trace only; candidate review only "
            "and never runtime truth in this slice."
        ),
    ),
    RawSourceDefinition(
        source_id="openfoodfacts_taiwan_small",
        filename="openfoodfacts_taiwan_small.json",
        source_class="open_food_facts",
        candidate_role="user_contributed_packaged_candidate",
        intended_roles=("packaged_candidate",),
        source_url_or_origin=OFF_API_DOC_URL,
        license_or_terms="Open Database License; contents license; user-contributed data",
        macro_support="user_contributed_macro_candidate_only",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["open_food_facts"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["open_food_facts"]["do_not_use_for"]),
        notes="OpenFoodFacts Taiwan sample inventory only.",
    ),
    RawSourceDefinition(
        source_id="usda_food_list_sample",
        filename="usda_food_list_sample.json",
        source_class="usda_fallback",
        candidate_role="fallback_source_evidence_only",
        intended_roles=("fallback_anchor",),
        source_url_or_origin=USDA_FDC_URL,
        license_or_terms="U.S. public-domain FoodData Central records",
        macro_support="source_macro_candidate_only_with_data_type_preserved",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["usda_fallback"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["usda_fallback"]["do_not_use_for"]),
        notes="USDA fallback sample inventory only.",
    ),
    RawSourceDefinition(
        source_id="base_nutrition_db",
        filename="base_nutrition_db.json",
        source_class="existing_repo_seed",
        source_role="candidate_only",
        candidate_role="alias_coverage_prior",
        intended_roles=("alias_coverage_prior",),
        source_url_or_origin="repo_existing_seed",
        license_or_terms="repo-local legacy seed; replace with source-backed records before promotion",
        macro_support="not_macro_truth",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["existing_repo_seed"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["existing_repo_seed"]["do_not_use_for"]),
        notes="Existing repo seed used as alias coverage prior only.",
    ),
    RawSourceDefinition(
        source_id="tfda_base_candidates",
        filename="tfda_base_candidates.json",
        source_class="taiwan_tfda_open_data",
        source_role="staging_candidate_only",
        candidate_role="generic_anchor_candidate",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        source_url_or_origin=TFDA_DATASET_URL,
        license_or_terms=TFDA_LICENSE,
        macro_support="per_100g_and_per_unit_source_evidence_candidate",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["do_not_use_for"]),
        notes="Existing TFDA staging candidates only.",
    ),
    RawSourceDefinition(
        source_id="tfda_base_review_candidates",
        filename="tfda_base_review_candidates.json",
        source_class="taiwan_tfda_open_data",
        source_role="staging_candidate_only",
        candidate_role="generic_anchor_candidate",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        source_url_or_origin=TFDA_DATASET_URL,
        license_or_terms=TFDA_LICENSE,
        macro_support="per_100g_and_per_unit_source_evidence_candidate",
        promotion_requires=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["promotion_requires"]),
        do_not_use_for=tuple(SOURCE_CLASS_POLICY["taiwan_tfda_open_data"]["do_not_use_for"]),
        notes="Existing TFDA review staging candidates only.",
    ),
)


def pipeline_stage_boundary() -> dict[str, Any]:
    return {
        "implemented_stage": "raw_source_inventory",
        "next_stages_not_implemented": [
            "candidate",
            "validator_passed",
            "auto_eligible_packet_candidate",
            "packet_ready",
        ],
    }


def build_raw_source_registry_artifact() -> dict[str, Any]:
    return {
        "artifact_type": "accurate_intake_food_raw_source_registry",
        "artifact_schema_version": "1.0",
        "claim_scope": "raw_source_registry_only",
        "truth_owner": "none",
        "semantic_owner": "none",
        "runtime_truth": False,
        **NON_CLAIM_FLAGS,
        "pipeline_stage_boundary": pipeline_stage_boundary(),
        "source_class_policy": SOURCE_CLASS_POLICY,
        "sources": [definition.as_dict() for definition in RAW_SOURCE_DEFINITIONS],
    }


__all__ = [
    "NON_CLAIM_FLAGS",
    "RAW_SOURCE_DEFINITIONS",
    "RawSourceDefinition",
    "SOURCE_CLASS_POLICY",
    "build_raw_source_registry_artifact",
    "pipeline_stage_boundary",
]
