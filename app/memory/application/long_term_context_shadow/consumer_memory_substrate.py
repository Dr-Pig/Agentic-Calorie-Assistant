from __future__ import annotations

from typing import Any

from app.memory.application.long_term_context_shadow.consumer_memory_bundles import (
    consumer_memory_bundles,
)
from app.memory.application.long_term_context_shadow.contracts import _base_artifact
from app.memory.domain.long_term_context_candidates import LongTermContextCandidate


def _consumer_memory_substrate_shadow_artifact(
    fixture: dict[str, Any],
    candidates: list[LongTermContextCandidate],
) -> dict[str, Any]:
    return _base_artifact(
        artifact_type="consumer_memory_substrate_shadow_eval",
        fixture=fixture,
        extra={
            "source_specs": [
                "docs/specs/L4A_MEMORY_MODEL_SPEC.md",
                "docs/specs/L4C_CONTEXT_PACKING_SPEC.md",
                "docs/specs/L4D_MEMORY_PROMOTION_DEMOTION_SPEC.md",
                "docs/specs/L3_2_RECOMMENDATION_RUNTIME_INTERFACE_CONTRACT_SPEC.md",
                "docs/specs/L3_3A_DEFICIT_EXPENDITURE_CALIBRATION_MODEL_SPEC.md",
                "docs/specs/L3_4_RESCUE_RUNTIME_CONTRACT_SPEC.md",
                "docs/specs/L3_6_PROACTIVE_SCHEDULER_SPEC.md",
            ],
            "memory_layers": _memory_layers(),
            "global_selection_policy": _global_selection_policy(),
            "consumer_memory_bundles": consumer_memory_bundles(candidates),
        },
    )


def _memory_layers() -> list[dict[str, Any]]:
    return [
        {
            "layer_id": "l1_typed_history",
            "runtime_truth_owner": "canonical_product_objects",
            "selection_role": "source_refs_and_audit_base",
            "activation_allowed_now": True,
            "durable_write_allowed_now": False,
        },
        {
            "layer_id": "l2a_statistical_pattern",
            "runtime_truth_owner": "shadow_deterministic_consolidation",
            "selection_role": "deterministic_consumer_signal",
            "activation_allowed_now": True,
            "durable_write_allowed_now": False,
        },
        {
            "layer_id": "l2b_semantic_pattern",
            "runtime_truth_owner": "future_llm_extraction_review",
            "selection_role": "planned_soft_signal",
            "activation_allowed_now": False,
            "durable_write_allowed_now": False,
        },
        {
            "layer_id": "l3_confirmed_memory",
            "runtime_truth_owner": "future_human_reviewed_memory_store",
            "selection_role": "future_high_weight_preference_source",
            "activation_allowed_now": False,
            "durable_write_allowed_now": False,
        },
        {
            "layer_id": "derived_views",
            "runtime_truth_owner": "materialized_views_over_canonical_history",
            "selection_role": "summary_first_consumer_context",
            "activation_allowed_now": True,
            "runtime_materialization_allowed_now": False,
        },
    ]


def _global_selection_policy() -> dict[str, bool]:
    return {
        "negative_preference_overrides_positive": True,
        "temporary_preference_requires_validity_window": True,
        "golden_orders_are_materialized_views": True,
        "stale_pattern_downgraded_not_deleted": True,
        "confirmed_memory_requires_human_review": True,
        "raw_history_dump_forbidden": True,
    }


__all__ = ["_consumer_memory_substrate_shadow_artifact"]
