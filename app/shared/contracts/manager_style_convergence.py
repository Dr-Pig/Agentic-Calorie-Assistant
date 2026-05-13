from __future__ import annotations

from typing import Any


MANAGER_ACTIONS = ("call_tools", "final")
ORCHESTRATION_STANCE = "bounded_manager_react_loop"
HARNESS_SHAPES_ALLOWED = (
    "scripted_manager_passes",
    "pass1_pass2_harness",
    "direct_runtime_artifact_builders",
)
BRANCH_DIVERGENCE_ALLOWED_ONLY_IN = (
    "activation_posture",
    "evidence_source",
    "lab_only_surface",
)
FORBIDDEN_BRANCH_DIVERGENCE = (
    "second_orchestration_model",
    "second_truth_owner_map",
    "second_tool_vocabulary",
)
SHARED_TRUTH_OWNERS = (
    "meal_thread",
    "day_budget_ledger",
    "body_plan",
    "proposal",
    "memory_record",
    "reusable_meal_entity",
)


def build_shared_manager_style_convergence_contract() -> dict[str, Any]:
    return {
        "artifact_type": "shared_manager_style_convergence_contract",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "orchestration_stance": ORCHESTRATION_STANCE,
        "manager_actions": list(MANAGER_ACTIONS),
        "harness_shapes_allowed": list(HARNESS_SHAPES_ALLOWED),
        "harness_shapes_are_not_product_architecture": True,
        "branch_divergence_allowed_only_in": list(BRANCH_DIVERGENCE_ALLOWED_ONLY_IN),
        "forbidden_branch_divergence": list(FORBIDDEN_BRANCH_DIVERGENCE),
        "shared_truth_owners": list(SHARED_TRUTH_OWNERS),
        "session_history_is_not_memory_store": True,
        "deterministic_legality_layer_required": True,
        "one_manager_contract_required": True,
        "one_tool_vocabulary_required": True,
        "blockers": [],
    }


__all__ = [
    "BRANCH_DIVERGENCE_ALLOWED_ONLY_IN",
    "FORBIDDEN_BRANCH_DIVERGENCE",
    "HARNESS_SHAPES_ALLOWED",
    "MANAGER_ACTIONS",
    "ORCHESTRATION_STANCE",
    "SHARED_TRUTH_OWNERS",
    "build_shared_manager_style_convergence_contract",
]
