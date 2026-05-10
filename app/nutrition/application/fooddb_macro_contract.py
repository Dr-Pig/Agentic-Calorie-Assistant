from __future__ import annotations

MACRO_PACKET_FIELDS = [
    "protein_g",
    "carbs_g",
    "fat_g",
    "macro_visibility_status",
    "macro_source_basis",
    "macro_confidence",
]
MACRO_REVIEW_DECISION_REQUIRED = [
    "source_class_macro_policy_review",
    "macro_basis_review",
    "macro_source_strength_review",
    "macro_confidence_review",
    "macro_visibility_or_null_review",
    "do_not_infer_macro_from_food_name_kcal_or_llm",
]
FORBIDDEN_MACRO_SOURCES = [
    "food_name",
    "kcal_reverse_inference",
    "llm_hint",
    "websearch_snippet",
]
MACRO_RUNTIME_POLICY = {
    "calorie_first": True,
    "macro_aware": True,
    "missing_macro_blocks_kcal_logging": False,
    "manager_may_infer_macro_from_food_name": False,
}
MACRO_SOURCE_CLASS_POLICY = {
    "exact_brand_item": {
        "macro_truth_allowed": True,
        "preferred_macro_basis": "official_label_or_menu",
        "allowed_macro_values": ["point", "null_unknown"],
    },
    "generic_common_serving": {
        "macro_truth_allowed": True,
        "truth_condition": "validated_common_serving_anchor",
        "allowed_macro_values": ["point", "range", "null_unknown"],
    },
    "listed_component": {
        "macro_truth_allowed": True,
        "truth_condition": "validated_component_anchor",
        "preferred_macro_granularity": "per_unit",
        "allowed_macro_values": ["point", "range", "null_unknown"],
    },
    "basket_family_alias_modifier": {
        "macro_truth_allowed": False,
        "runtime_role": "query_portion_or_visibility_modifier_only",
    },
    "source_evidence_candidate": {
        "macro_truth_allowed": False,
        "runtime_role": "evidence_candidate_not_serving_truth",
        "source_classes": ["TFDA_per_100g", "USDA", "OpenFoodFacts", "WebSearch"],
    },
}
MACRO_SHADOW_SCHEMA = {
    "exact_brand_item": {
        "macro_fields": [
            "protein_g",
            "carbs_g",
            "fat_g",
            "macro_basis",
            "macro_confidence",
            "macro_source_strength",
            "nutrition_label_basis",
            "source_url",
            "source_accessed_at",
        ],
        "truth_condition": "official_label_or_menu",
        "values_may_be_null": True,
    },
    "generic_common_serving": {
        "macro_fields": [
            "protein_g_point",
            "protein_g_range",
            "carbs_g_point",
            "carbs_g_range",
            "fat_g_point",
            "fat_g_range",
            "macro_basis",
            "macro_confidence",
            "macro_source_strength",
        ],
        "truth_condition": "validated_common_serving_anchor",
        "values_may_be_null": True,
    },
    "listed_component": {
        "macro_fields": [
            "protein_g_per_unit",
            "protein_g_range",
            "carbs_g_per_unit",
            "carbs_g_range",
            "fat_g_per_unit",
            "fat_g_range",
            "unit_phrase",
            "macro_basis",
            "macro_confidence",
            "macro_source_strength",
        ],
        "truth_condition": "validated_component_anchor",
        "preferred_macro_granularity": "per_unit",
        "values_may_be_null": True,
    },
    "basket_family_alias_modifier": {
        "macro_fields": [],
        "runtime_role": "query_portion_or_visibility_modifier_only",
        "runtime_truth_allowed": False,
    },
    "source_evidence_candidate": {
        "candidate_fields": [
            "protein_g_per_100g",
            "carbs_g_per_100g",
            "fat_g_per_100g",
            "source_denominator",
            "source_class",
            "source_record_id",
        ],
        "runtime_role": "evidence_candidate_not_serving_truth",
        "runtime_truth_allowed": False,
    },
}
MACRO_CONTRACT = {
    "packet_fields": MACRO_PACKET_FIELDS,
    "macro_truth_owner": "fooddb_approved_packet",
    "missing_macro_policy": "preserve_null_do_not_invent",
    "macro_runtime_policy": MACRO_RUNTIME_POLICY,
    "source_class_policy": MACRO_SOURCE_CLASS_POLICY,
    "shadow_schema": MACRO_SHADOW_SCHEMA,
}
APPROVED_PACKET_READY_SCHEMA_VERSION = "fooddb_approved_packet_ready_artifact_v1"
APPROVED_PACKET_READY_SOURCE_QUALITY = "packet_ready_approved"


def build_macro_review_policy() -> dict:
    return {
        "packet_fields": list(MACRO_PACKET_FIELDS),
        "missing_macro_policy": MACRO_CONTRACT["missing_macro_policy"],
        "missing_macro_blocks_kcal_logging": MACRO_RUNTIME_POLICY[
            "missing_macro_blocks_kcal_logging"
        ],
        "review_candidate_can_create_macro_truth": False,
        "source_class_policy_choices": list(MACRO_SOURCE_CLASS_POLICY),
        "forbidden_macro_sources": list(FORBIDDEN_MACRO_SOURCES),
    }


__all__ = [
    "APPROVED_PACKET_READY_SCHEMA_VERSION",
    "APPROVED_PACKET_READY_SOURCE_QUALITY",
    "FORBIDDEN_MACRO_SOURCES",
    "MACRO_CONTRACT",
    "MACRO_PACKET_FIELDS",
    "MACRO_REVIEW_DECISION_REQUIRED",
    "MACRO_RUNTIME_POLICY",
    "MACRO_SHADOW_SCHEMA",
    "MACRO_SOURCE_CLASS_POLICY",
    "build_macro_review_policy",
]
