from __future__ import annotations

from typing import Any, Mapping

from app.recommendation.application.five_node_shadow_fixture import (
    build_fixture_recommendation_five_node_input,
)
from app.recommendation.application.three_node_shadow_policy import (
    candidate_guard,
    empty_candidate_guard,
    source_refs,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.five_node_shadow_runner"
)

NODE_ORDER = [
    "recommendation_context_fixture",
    "candidate_spec_fixture",
    "deterministic_candidate_retrieval",
    "ranking_synthesis_fixture",
    "response_offer_fixture",
]
LLM_NODES = [
    "recommendation_context_fixture",
    "candidate_spec_fixture",
    "ranking_synthesis_fixture",
    "response_offer_fixture",
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


def run_recommendation_five_node_lab_runner(
    payload: Mapping[str, Any],
) -> dict[str, Any]:
    llm_blockers = _llm_node_blockers(payload)
    if llm_blockers:
        return _artifact(
            status="blocked",
            blockers=llm_blockers,
            retrieval=empty_candidate_guard(),
            ranking=None,
            response_packet=None,
        )

    retrieval = candidate_guard(payload)
    allowed_ids = set(retrieval["allowed_candidate_ids"])
    ranking = _mapping(payload.get("ranking_synthesis_fixture"))
    response = _mapping(payload.get("response_offer_fixture"))

    blockers = _ranking_blockers(ranking, allowed_ids)
    blockers.extend(_response_blockers(response, allowed_ids))
    if blockers:
        return _artifact(
            status="blocked",
            blockers=blockers,
            retrieval=retrieval,
            ranking=_ranking_summary(ranking),
            response_packet=None,
        )

    selected_candidate_id = str(ranking.get("selected_candidate_id", ""))
    return _artifact(
        status="pass",
        blockers=[],
        retrieval=retrieval,
        ranking=_ranking_summary(ranking),
        response_packet={
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
    retrieval: dict[str, Any],
    ranking: dict[str, Any] | None,
    response_packet: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_five_node_lab_runner_artifact",
        "status": status,
        "runner_role": "lab_observability_only",
        "blockers": blockers,
        "node_order": NODE_ORDER,
        "llm_owned_nodes": LLM_NODES,
        "deterministic_nodes": ["deterministic_candidate_retrieval"],
        "candidate_retrieval": retrieval,
        "ranking_synthesis": ranking,
        "response_offer_packet": response_packet,
        "node_trace": _node_trace(),
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


def _ranking_blockers(ranking: Mapping[str, Any], allowed_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    selected_id = str(ranking.get("selected_candidate_id", ""))
    if selected_id not in allowed_ids:
        blockers.append(
            f"ranking_synthesis_fixture.selected_candidate_not_allowed:{selected_id}"
        )
    for candidate_id in _ranked_candidate_ids(ranking):
        if candidate_id not in allowed_ids:
            blockers.append(
                f"ranking_synthesis_fixture.ranked_candidate_not_allowed:{candidate_id}"
            )
    return blockers


def _response_blockers(response: Mapping[str, Any], allowed_ids: set[str]) -> list[str]:
    blockers: list[str] = []
    candidate_id = str(response.get("candidate_id", ""))
    if candidate_id not in allowed_ids:
        blockers.append(f"response_offer_fixture.candidate_not_allowed:{candidate_id}")
    if response.get("recommendation_served") is True:
        blockers.append("response_offer_fixture.recommendation_served_not_allowed")
    if response.get("is_canonical_truth") is True:
        blockers.append("response_offer_fixture.is_canonical_truth_not_allowed")
    if response.get("intake_commit_requested") is True:
        blockers.append("response_offer_fixture.intake_commit_requested_not_allowed")
    return blockers


def _ranking_summary(ranking: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "selected_candidate_id": str(ranking.get("selected_candidate_id", "")),
        "ranked_candidate_ids": _ranked_candidate_ids(ranking),
    }


def _ranked_candidate_ids(ranking: Mapping[str, Any]) -> list[str]:
    values = ranking.get("ranked_candidate_ids")
    return [str(value) for value in values] if isinstance(values, list) else []


def _node_trace() -> list[dict[str, str]]:
    return [
        {
            "node": node,
            "owner": "deterministic"
            if node == "deterministic_candidate_retrieval"
            else "llm_fixture",
        }
        for node in NODE_ORDER
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_fixture_recommendation_five_node_input",
    "run_recommendation_five_node_lab_runner",
]
