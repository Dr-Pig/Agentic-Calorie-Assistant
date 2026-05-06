from __future__ import annotations

from app.nutrition.application.websearch_integration_readiness_matrix import (
    build_websearch_integration_readiness_matrix,
)


def test_websearch_integration_readiness_matrix_covers_required_edges() -> None:
    matrix = build_websearch_integration_readiness_matrix()

    assert matrix["artifact_type"] == "accurate_intake_websearch_integration_readiness_matrix"
    assert matrix["runtime_truth_changed"] is False
    assert matrix["mutation_changed"] is False
    assert matrix["shared_contract_changed"] is False
    assert matrix["manager_context_changed"] is False
    assert matrix["readiness_claimed"] is False

    edges = {edge["edge_id"]: edge for edge in matrix["check_edges"]}
    assert set(edges) == {
        "websearch_candidate_lane_status_to_websearch_status_packet",
        "exact_evidence_lane_status_to_websearch_status_packet",
        "websearch_contract_handoff_to_websearch_status_packet",
        "websearch_status_packet_to_retriever_router_readiness",
        "websearch_exact_candidate_chain_status_to_live_runner_readiness_packet",
        "websearch_live_extract_preflight_to_live_runner_readiness_packet",
        "websearch_live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic",
    }


def test_websearch_integration_readiness_matrix_keeps_manager_style_and_truth_boundaries() -> None:
    matrix = build_websearch_integration_readiness_matrix()
    edges = {edge["edge_id"]: edge for edge in matrix["check_edges"]}

    assert (
        "cannot_grant_runtime_truth_or_mutation"
        in edges["websearch_status_packet_to_retriever_router_readiness"][
            "manager_style_guard"
        ]
    )
    assert (
        "without_explicit_allow_live"
        in edges["websearch_live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic"][
            "stop_condition"
        ]
    )
    assert matrix["summary"]["next_required_slices"] == ["inspect_websearch_status_packet"]
