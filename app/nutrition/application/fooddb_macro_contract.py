from __future__ import annotations

MACRO_PACKET_FIELDS = [
    "protein_g",
    "carbs_g",
    "fat_g",
    "macro_visibility_status",
    "macro_source_basis",
    "macro_confidence",
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
MACRO_CONTRACT = {
    "packet_fields": MACRO_PACKET_FIELDS,
    "macro_truth_owner": "fooddb_approved_packet",
    "missing_macro_policy": "preserve_null_do_not_invent",
    "macro_runtime_policy": MACRO_RUNTIME_POLICY,
    "source_class_policy": MACRO_SOURCE_CLASS_POLICY,
}
APPROVED_PACKET_READY_SCHEMA_VERSION = "fooddb_approved_packet_ready_artifact_v1"
APPROVED_PACKET_READY_SOURCE_QUALITY = "packet_ready_approved"


__all__ = [
    "APPROVED_PACKET_READY_SCHEMA_VERSION",
    "APPROVED_PACKET_READY_SOURCE_QUALITY",
    "MACRO_CONTRACT",
    "MACRO_PACKET_FIELDS",
    "MACRO_RUNTIME_POLICY",
    "MACRO_SOURCE_CLASS_POLICY",
]
