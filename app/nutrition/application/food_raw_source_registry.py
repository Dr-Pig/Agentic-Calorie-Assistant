from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
    runtime_truth: bool = False
    notes: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_id": self.source_id,
            "filename": self.filename,
            "source_class": self.source_class,
            "source_role": self.source_role,
            "intended_roles": list(self.intended_roles),
            "runtime_truth": self.runtime_truth,
            "notes": self.notes,
        }


# Preserve legacy introspection/pickle identity after moving the implementation.
RawSourceDefinition.__module__ = "app.nutrition.application.food_raw_source_inventory"


RAW_SOURCE_DEFINITIONS: tuple[RawSourceDefinition, ...] = (
    RawSourceDefinition(
        source_id="tfda_fda_food_nutrition_2024",
        filename="FDA_food_nutrition_2024.xlsx",
        source_class="taiwan_tfda_open_data",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        notes="TFDA/FDA nutrition Excel inventory only; not packet truth.",
    ),
    RawSourceDefinition(
        source_id="tfda_tnfcds_consumer_detail",
        filename="tnfcds_consumer_detail.xlsx",
        source_class="taiwan_tfda_open_data",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        notes="TNFCDS consumer detail raw/staging source inventory only.",
    ),
    RawSourceDefinition(
        source_id="tfda_tnfcds_consumer_items",
        filename="tnfcds_consumer_items.xlsx",
        source_class="taiwan_tfda_open_data",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        notes="TNFCDS consumer items raw/staging source inventory only.",
    ),
    RawSourceDefinition(
        source_id="newtaipei_brand_candidates",
        filename="newtaipei_brand_candidates.json",
        source_class="official_brand_chain_page",
        source_role="staging_candidate_only",
        intended_roles=("exact_card_candidate",),
        notes="Official page-derived brand candidates only; no runtime truth.",
    ),
    RawSourceDefinition(
        source_id="local_tw_packaged_extract_188_2",
        filename="188_2.csv",
        source_class="local_taiwan_packaged_extract",
        source_role="staging_candidate_only",
        intended_roles=("exact_card_candidate",),
        notes=(
            "Local extracted CSV packaged-product trace only; candidate review only "
            "and never runtime truth in this slice."
        ),
    ),
    RawSourceDefinition(
        source_id="openfoodfacts_taiwan_small",
        filename="openfoodfacts_taiwan_small.json",
        source_class="open_food_facts",
        intended_roles=("packaged_candidate",),
        notes="OpenFoodFacts Taiwan sample inventory only.",
    ),
    RawSourceDefinition(
        source_id="usda_food_list_sample",
        filename="usda_food_list_sample.json",
        source_class="usda_fallback",
        intended_roles=("fallback_anchor",),
        notes="USDA fallback sample inventory only.",
    ),
    RawSourceDefinition(
        source_id="base_nutrition_db",
        filename="base_nutrition_db.json",
        source_class="existing_repo_seed",
        source_role="candidate_only",
        intended_roles=("alias_coverage_prior",),
        notes="Existing repo seed used as alias coverage prior only.",
    ),
    RawSourceDefinition(
        source_id="tfda_base_candidates",
        filename="tfda_base_candidates.json",
        source_class="taiwan_tfda_open_data",
        source_role="staging_candidate_only",
        intended_roles=("generic_anchor", "listed_component_anchor"),
        notes="Existing TFDA staging candidates only.",
    ),
    RawSourceDefinition(
        source_id="tfda_base_review_candidates",
        filename="tfda_base_review_candidates.json",
        source_class="taiwan_tfda_open_data",
        source_role="staging_candidate_only",
        intended_roles=("generic_anchor", "listed_component_anchor"),
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
        "sources": [definition.as_dict() for definition in RAW_SOURCE_DEFINITIONS],
    }


__all__ = [
    "NON_CLAIM_FLAGS",
    "RAW_SOURCE_DEFINITIONS",
    "RawSourceDefinition",
    "build_raw_source_registry_artifact",
    "pipeline_stage_boundary",
]
