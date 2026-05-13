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
from app.advanced_shadow_lab.product_lab_recommendation_feedback import (
    recommendation_feedback_fields,
)
from app.advanced_shadow_lab.product_lab_recommendation_provider import (
    FixtureProductLabRecommendationProvider,
)
from app.recommendation.application.turn_plan_input_adapter import (
    build_recommendation_planning_input,
    inactive_recommendation_planning_input_adapter,
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
    manager_turn_plan: Mapping[str, Any] | None = None,
    tool_arguments: Mapping[str, Any] | None = None,
    provider: FixtureProductLabRecommendationProvider | None = None,
) -> dict[str, Any]:
    active_provider = provider or FixtureProductLabRecommendationProvider()
    planning_input_adapter = _planning_input_adapter(
        manager_turn_plan=manager_turn_plan,
        tool_arguments=tool_arguments,
        memory_context_pack=memory_context_pack,
    )
    planning = active_provider.plan(
        turn=_turn_with_planning_input(turn, planning_input_adapter),
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
        *_blockers("planning_input_adapter", planning_input_adapter),
        *_blockers("planning", planning),
        *_blockers("candidate_retrieval_guard_scoring", retrieval_guard_scoring),
        *_blockers("offer_synthesis", offer_synthesis),
    ]
    primary = _mapping(offer_synthesis.get("selected_primary"))
    feedback_fields = recommendation_feedback_fields(turn=turn, primary_candidate=primary)
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
        "planning_input_adapter": planning_input_adapter,
        "planning": planning,
        "retrieval_guard_scoring": retrieval_guard_scoring,
        "offer_synthesis": offer_synthesis,
        "intake_handoff_packet": _intake_handoff(primary),
        "pending_intake_handoff_packet": pending_handoff,
        **feedback_fields,
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


def _planning_input_adapter(
    *,
    manager_turn_plan: Mapping[str, Any] | None,
    tool_arguments: Mapping[str, Any] | None,
    memory_context_pack: Mapping[str, Any],
) -> dict[str, Any]:
    if manager_turn_plan is None:
        return inactive_recommendation_planning_input_adapter()
    return build_recommendation_planning_input(
        manager_turn_plan=manager_turn_plan,
        tool_arguments=tool_arguments or {},
        memory_context_pack=memory_context_pack,
    )


def _turn_with_planning_input(
    turn: Mapping[str, Any],
    planning_input_adapter: Mapping[str, Any],
) -> Mapping[str, Any]:
    planning_input = _mapping(planning_input_adapter.get("planning_input"))
    user_goal = str(planning_input.get("user_goal") or "")
    if planning_input_adapter.get("status") != "pass" or not user_goal:
        return turn
    return {**dict(turn), "semantic_intent_fixture": user_goal}


def _blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [f"{prefix}.{blocker}" for blocker in artifact.get("blockers") or []]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["run_product_lab_recommendation"]
