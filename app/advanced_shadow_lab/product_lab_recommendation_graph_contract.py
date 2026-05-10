from __future__ import annotations

from typing import Any, Mapping


OWNERSHIP_BOUNDARIES = [
    "llm_planning_to_deterministic_guard",
    "deterministic_guard_to_llm_offer_synthesis",
]
NODE_CONTRACTS = [
    {
        "node": "recommendation_planning",
        "owner": "llm",
        "llm_semantic_authority": True,
        "may_filter_candidates": False,
        "may_create_user_intent": False,
        "may_mutate_canonical_state": False,
    },
    {
        "node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
        "llm_semantic_authority": False,
        "may_filter_candidates": True,
        "may_create_user_intent": False,
        "may_mutate_canonical_state": False,
    },
    {
        "node": "offer_synthesis",
        "owner": "llm",
        "llm_semantic_authority": True,
        "may_filter_candidates": False,
        "may_create_user_intent": False,
        "may_mutate_canonical_state": False,
    },
]
ANTI_OVERENGINEERING_GUARD = {
    "five_node_pass_chain_rejected": True,
    "node_split_requires_new_ownership_boundary": True,
    "generic_workflow_engine_required": False,
}


def build_recommendation_graph_contract(
    *,
    physical_node_order: list[str],
    logical_stage_trace: list[Mapping[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_graph_contract",
        "physical_node_count": len(physical_node_order),
        "physical_node_order": list(physical_node_order),
        "conceptual_step_count": len(logical_stage_trace),
        "conceptual_step_trace": [dict(row) for row in logical_stage_trace],
        "ownership_boundaries": list(OWNERSHIP_BOUNDARIES),
        "node_contracts": [dict(row) for row in NODE_CONTRACTS],
        "anti_overengineering_guard": dict(ANTI_OVERENGINEERING_GUARD),
        "mainline_activation_enabled": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": graph_contract_blockers(physical_node_order, logical_stage_trace),
    }


def graph_contract_blockers(
    physical_node_order: list[str],
    logical_stage_trace: list[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if len(physical_node_order) != 3:
        blockers.append("physical_node_count.not_three")
    if len(logical_stage_trace) != 5:
        blockers.append("conceptual_step_count.not_five")
    if "candidate_retrieval_guard_scoring" not in physical_node_order:
        blockers.append("deterministic_guard_node.missing")
    return blockers


__all__ = ["build_recommendation_graph_contract"]
