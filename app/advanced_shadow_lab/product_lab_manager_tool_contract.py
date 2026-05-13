from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_memory_tools import (
    SUPPORTED_TOOLS as MEMORY_TOOL_NAMES,
)
from app.shared.contracts.capability_registry import build_shared_capability_registry
from app.shared.contracts.manager_style_convergence import (
    MANAGER_ACTIONS,
    ORCHESTRATION_STANCE,
    build_shared_manager_style_convergence_contract,
)
from app.shared.contracts.recommendation_tool_arguments import (
    build_recommendation_tool_argument_contract,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_manager_tool_contract"
)

PRODUCT_TOOL_NAMES = {
    "intake.run",
    "query.run",
    "recommendation.run",
    "reusable_meal.search",
    "rescue.run",
    "proactive.run",
}
MANAGER_TOOL_NAMES = tuple(sorted((*MEMORY_TOOL_NAMES, *PRODUCT_TOOL_NAMES)))
TOOL_MODES = {
    "query.run": "read_only_context",
    "memory.search": "read_only_context",
    "memory.get": "read_only_context",
    "conversation_recall.search": "read_only_context",
    "intake.run": "contract_backed_intake_handoff",
    "reusable_meal.search": "read_only_context",
    "recommendation.run": "candidate_context",
    "rescue.run": "proposal_candidate",
    "proactive.run": "chat_first_no_send_candidate",
}
TOOL_FAMILIES = {
    "query.run": "query",
    "memory.search": "long_term_memory",
    "memory.get": "long_term_memory",
    "conversation_recall.search": "long_term_memory",
    "intake.run": "intake",
    "reusable_meal.search": "reusable_meal",
    "recommendation.run": "recommendation",
    "rescue.run": "rescue",
    "proactive.run": "proactive",
}
FINAL_FORBIDDEN_TRUE_FIELDS = set(FALSE_FLAGS) | {
    "served_to_mainline_user",
    "scheduler_enqueued",
    "production_scheduler_delivery_allowed",
    "production_db_migration_allowed",
    "canonical_mutation_requested",
    "canonical_product_mutation_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
}


def dormant_activation_fields() -> dict[str, bool]:
    return {
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
    }


def build_product_lab_manager_tool_registry() -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_manager_tool_registry",
        "artifact_schema_version": "1.0",
        "status": "pass",
        "orchestration_stance": ORCHESTRATION_STANCE,
        "manager_actions": list(MANAGER_ACTIONS),
        "shared_manager_style_convergence": build_shared_manager_style_convergence_contract(),
        "shared_capability_registry": build_shared_capability_registry(),
        "tool_names": list(MANAGER_TOOL_NAMES),
        "tool_specs": [_tool_spec(name) for name in MANAGER_TOOL_NAMES],
        "session_history_is_not_memory_store": True,
        "tool_results_must_return_to_manager_pass": True,
        "deterministic_guards_own_mutation_legality": True,
        **dormant_activation_fields(),
        "blockers": [],
    }


def _tool_spec(tool_name: str) -> dict[str, Any]:
    spec = {
        "tool_name": tool_name,
        "capability_family": TOOL_FAMILIES[tool_name],
        "tool_mode": TOOL_MODES[tool_name],
        "lab_only": True,
        "requires_scope": True,
        "mainline_activation_enabled": False,
        "canonical_mutation_allowed": False,
    }
    if tool_name == "recommendation.run":
        spec["argument_contract"] = build_recommendation_tool_argument_contract()
    return spec


__all__ = [
    "FINAL_FORBIDDEN_TRUE_FIELDS",
    "MANAGER_TOOL_NAMES",
    "MEMORY_TOOL_NAMES",
    "PRODUCT_TOOL_NAMES",
    "SIDECAR_ACTIVATION_CONTRACT",
    "TOOL_FAMILIES",
    "TOOL_MODES",
    "build_product_lab_manager_tool_registry",
    "dormant_activation_fields",
]
