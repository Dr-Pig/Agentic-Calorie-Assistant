from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.product_lab_recommendation_candidates import (
    build_candidate_retrieval_guard_scoring,
)
from app.advanced_shadow_lab.product_lab_recommendation_graph_contract import (
    build_recommendation_graph_contract,
)
from app.advanced_shadow_lab.product_lab_recommendation_handoff import (
    build_pending_intake_handoff_packet,
)
from app.advanced_shadow_lab.product_lab_recommendation_provider import (
    FixtureProductLabRecommendationProvider,
)


PHYSICAL_NODE_ORDER = [
    "recommendation_planning",
    "candidate_retrieval_guard_scoring",
    "offer_synthesis",
]
LOGICAL_STAGE_TRACE = [
    {
        "logical_stage": "recommendation_context_result",
        "physical_node": "recommendation_planning",
        "owner": "llm",
    },
    {
        "logical_stage": "candidate_spec",
        "physical_node": "recommendation_planning",
        "owner": "llm",
    },
    {
        "logical_stage": "candidate_retrieval_guard_scoring",
        "physical_node": "candidate_retrieval_guard_scoring",
        "owner": "deterministic",
    },
    {
        "logical_stage": "ranking_result",
        "physical_node": "offer_synthesis",
        "owner": "llm",
    },
    {
        "logical_stage": "recommendation_response_result",
        "physical_node": "offer_synthesis",
        "owner": "llm",
    },
]


def run_product_lab_recommendation(
    *,
    turn: Mapping[str, Any],
    fixture_inputs: Mapping[str, Any],
    memory_context_pack: Mapping[str, Any],
    provider: FixtureProductLabRecommendationProvider | None = None,
) -> dict[str, Any]:
    active_provider = provider or FixtureProductLabRecommendationProvider()
    planning = active_provider.plan(
        turn=turn,
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_context_pack,
    )
    retrieval_guard_scoring = build_candidate_retrieval_guard_scoring(
        planning=planning,
        fixture_inputs=fixture_inputs,
        memory_context_pack=memory_context_pack,
    )
    offer_synthesis = active_provider.synthesize_offer(
        retrieval_guard_scoring=retrieval_guard_scoring,
    )
    graph_contract = build_recommendation_graph_contract(
        physical_node_order=PHYSICAL_NODE_ORDER,
        logical_stage_trace=LOGICAL_STAGE_TRACE,
    )
    blockers = [
        *_blockers("graph_contract", graph_contract),
        *_blockers("planning", planning),
        *_blockers("candidate_retrieval_guard_scoring", retrieval_guard_scoring),
        *_blockers("offer_synthesis", offer_synthesis),
    ]
    primary = _mapping(offer_synthesis.get("selected_primary"))
    pending_handoff = build_pending_intake_handoff_packet(
        primary_candidate=primary,
        ux_packet=_mapping(offer_synthesis.get("ux_packet")),
    )
    blockers = [
        *blockers,
        *_blockers("pending_intake_handoff", pending_handoff),
    ]
    served_to_lab = (
        not bool(blockers)
        and bool(primary.get("candidate_id"))
        and offer_synthesis.get("status") != "omitted"
    )
    return {
        "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "physical_node_order": list(PHYSICAL_NODE_ORDER),
        "logical_stage_trace": [dict(row) for row in LOGICAL_STAGE_TRACE],
        "graph_contract": graph_contract,
        "provider_profile": active_provider.profile(),
        "planning": planning,
        "retrieval_guard_scoring": retrieval_guard_scoring,
        "offer_synthesis": offer_synthesis,
        "intake_handoff_packet": _intake_handoff(primary),
        "pending_intake_handoff_packet": pending_handoff,
        "recommendation_served_to_lab": served_to_lab,
        "proactive_recommendation_candidate_allowed": (
            served_to_lab
            and retrieval_guard_scoring.get("pool_decision")
            in {"primary_plus_backup", "offer"}
        ),
        "lab_user_facing_behavior_changed": served_to_lab,
        "recommendation_intent_state_created": False,
        "pending_intake_handoff_created": (
            pending_handoff.get("lab_intake_intent_created") is True
        ),
        "external_location_search_used": False,
        "raw_user_text_semantic_inference_performed": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "served_to_mainline_user": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "manager_context_packet_changed": False,
        "blockers": blockers,
    }


def _intake_handoff(primary: Mapping[str, Any]) -> dict[str, Any]:
    candidate_id = str(primary.get("candidate_id") or "")
    return {
        "candidate_id": candidate_id,
        "requires_explicit_user_intake_action": True,
        "canonical_commit_requested": False,
    }


def _blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [f"{prefix}.{blocker}" for blocker in artifact.get("blockers") or []]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_recommendation"]
