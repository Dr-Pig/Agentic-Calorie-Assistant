from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.three_node_shadow_policy import (
    build_fixture_recommendation_three_node_input,
    candidate_guard,
    empty_candidate_guard,
    offer_blockers,
    source_refs,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_shadow_contract"
)

NODE_ORDER = [
    "manager_recommendation_decision_fixture",
    "deterministic_candidate_guard",
    "shadow_offer_packet_fixture",
]
PHYSICAL_NODE_ORDER = [
    "recommendation_planning",
    "candidate_retrieval_guard_scoring",
    "offer_synthesis",
]
LLM_NODES = [
    "manager_recommendation_decision_fixture",
    "shadow_offer_packet_fixture",
]
LOGICAL_STAGE_TRACE = [
    {
        "logical_stage": "recommendation_context_result",
        "physical_node": "recommendation_planning",
        "owner": "llm_fixture",
    },
    {
        "logical_stage": "candidate_spec",
        "physical_node": "recommendation_planning",
        "owner": "llm_fixture",
    },
    {
        "logical_stage": "candidate_retrieval_guard_scoring",
        "physical_node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
    },
    {
        "logical_stage": "ranking_result",
        "physical_node": "offer_synthesis",
        "owner": "llm_fixture",
    },
    {
        "logical_stage": "recommendation_response_result",
        "physical_node": "offer_synthesis",
        "owner": "llm_fixture",
    },
]
FALSE_ACTIVATION_FLAGS = {
    "runtime_effect_allowed": False,
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "durable_product_memory_written": False,
    "manager_context_packet_changed": False,
    "user_facing_behavior_changed": False,
    "live_provider_used": False,
    "recommendation_served": False,
    "intake_committed": False,
    "product_readiness_claimed": False,
}


def run_recommendation_three_node_shadow(payload: Mapping[str, Any]) -> dict[str, Any]:
    llm_blockers = _llm_node_blockers(payload)
    if llm_blockers:
        return _artifact(
            status="blocked",
            blockers=llm_blockers,
            guard=empty_candidate_guard(),
            selected_candidate_id=None,
            offer_packet=None,
        )

    guard = candidate_guard(payload)
    allowed_ids = set(guard["allowed_candidate_ids"])
    decision = _mapping(payload.get("manager_recommendation_decision_fixture"))
    offer = _mapping(payload.get("shadow_offer_packet_fixture"))
    selected_candidate_id = str(decision.get("top_candidate_id", ""))

    blockers = _selection_blockers(selected_candidate_id, allowed_ids)
    blockers.extend(offer_blockers(offer, allowed_ids))
    if blockers:
        return _artifact(
            status="blocked",
            blockers=blockers,
            guard=guard,
            selected_candidate_id=selected_candidate_id or None,
            offer_packet=None,
        )

    return _artifact(
        status="pass",
        blockers=[],
        guard=guard,
        selected_candidate_id=selected_candidate_id,
        offer_packet={
            "candidate_id": selected_candidate_id,
            "is_canonical_truth": False,
            "recommendation_served": False,
            "intake_commit_requested": False,
            "source_refs": source_refs(payload, selected_candidate_id),
        },
    )


def _artifact(
    *,
    status: str,
    blockers: list[str],
    guard: dict[str, Any],
    selected_candidate_id: str | None,
    offer_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_three_node_shadow_artifact",
        "status": status,
        "blockers": blockers,
        "node_order": NODE_ORDER,
        "physical_graph_profile": "three_node_recommendation_planning_guard_offer",
        "physical_node_order": list(PHYSICAL_NODE_ORDER),
        "logical_stage_trace": [dict(item) for item in LOGICAL_STAGE_TRACE],
        "legacy_five_node_artifact_source": False,
        "llm_owned_nodes": LLM_NODES,
        "deterministic_nodes": ["deterministic_candidate_guard"],
        "candidate_guard": guard,
        "selected_candidate_id": selected_candidate_id,
        "shadow_offer_packet": offer_packet,
        "activation_flags": dict(FALSE_ACTIVATION_FLAGS),
    }


def _llm_node_blockers(payload: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for node in LLM_NODES:
        value = _mapping(payload.get(node))
        if not value:
            blockers.append(f"{node}.missing_llm_fixture")
        elif value.get("decision_mode") != "llm_fixture":
            blockers.append(f"{node}.decision_mode_not_llm_fixture")
    return blockers


def _selection_blockers(candidate_id: str, allowed_ids: set[str]) -> list[str]:
    if candidate_id in allowed_ids:
        return []
    return [
        "manager_recommendation_decision_fixture."
        f"top_candidate_not_allowed:{candidate_id}"
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_fixture_recommendation_three_node_input",
    "run_recommendation_three_node_shadow",
]
