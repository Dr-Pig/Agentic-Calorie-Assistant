from __future__ import annotations

from pathlib import Path

from app.nutrition.application.fooddb_integration_readiness_matrix import (
    build_fooddb_integration_readiness_matrix,
)


DOC_PATH = Path("docs/quality/ACCURATE_INTAKE_FOODDB_WEBSEARCH_LLM_ACTIVATION_PLAN.md")


def test_fooddb_integration_readiness_matrix_covers_required_edges() -> None:
    matrix = build_fooddb_integration_readiness_matrix()

    assert matrix["artifact_type"] == "accurate_intake_fooddb_integration_readiness_matrix"
    assert matrix["claim_scope"] == "dependency_inversion_and_manager_style_integration_check"
    assert matrix["runtime_truth_changed"] is False
    assert matrix["mutation_changed"] is False
    assert matrix["shared_contract_changed"] is False

    edges = {edge["edge_id"]: edge for edge in matrix["check_edges"]}
    assert set(edges) == {
        "manager_decision_to_retrieval_intent",
        "retrieval_router_to_fooddb_local_adapter",
        "retrieval_router_to_sqlite_fts_adapter",
        "retrieval_router_to_websearch_candidate",
        "retriever_output_to_compact_packet",
        "packet_to_manager_seam",
        "packet_to_mutation_guard",
        "exact_candidate_to_no_mutation",
        "listed_components_to_approved_runtime_anchors",
    }

    assert edges["manager_decision_to_retrieval_intent"]["current_status"] == "contract_backed"
    assert edges["retrieval_router_to_sqlite_fts_adapter"]["current_status"] == "missing"
    assert edges["retrieval_router_to_websearch_candidate"]["current_status"] == "contract_backed"
    assert edges["packet_to_manager_seam"]["current_status"] == "contract_backed"
    assert (
        edges["exact_candidate_to_no_mutation"]["manager_style_guard"]
        == "exact_candidate_packets_remain_candidate_only_until_separate_promotion_lane"
    )
    assert (
        edges["listed_components_to_approved_runtime_anchors"]["manager_style_guard"]
        == "listed_basket_components_may_estimate_only_when_runtime_anchor_is_approved"
    )


def test_activation_plan_documents_integration_readiness_matrix() -> None:
    content = DOC_PATH.read_text(encoding="utf-8-sig")

    assert "integration_readiness_matrix_update" in content
    assert "Manager decision -> retrieval intent from manager decision" in content
    assert "retrieval router -> SQLite FTS adapter" in content
    assert "packet -> mutation guard" in content
    assert "exact candidate -> no mutation" in content
