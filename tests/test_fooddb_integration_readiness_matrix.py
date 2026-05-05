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
    assert matrix["manager_context_changed"] is False
    assert matrix["websearch_runtime_truth_allowed"] is False
    assert matrix["readiness_claimed"] is False
    assert set(matrix["non_claims"]) == {
        "no_runtime_truth_promotion",
        "no_packetizer_contract_change",
        "no_manager_context_change",
        "no_websearch_runtime_truth",
        "no_readiness_claim",
    }

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
        "websearch_candidate_to_selected_extract_request",
        "selected_extract_request_to_extract_result_candidate",
        "extract_result_candidate_to_exact_review_packet",
        "exact_review_packet_to_live_extract_preflight",
        "listed_components_to_approved_runtime_anchors",
    }

    assert edges["manager_decision_to_retrieval_intent"]["current_status"] == "contract_backed"
    assert edges["retrieval_router_to_sqlite_fts_adapter"]["current_status"] == "contract_backed"
    assert edges["retrieval_router_to_websearch_candidate"]["current_status"] == "contract_backed"
    assert edges["packet_to_manager_seam"]["current_status"] == "contract_backed"
    assert edges["packet_to_mutation_guard"]["current_status"] == "contract_backed"
    assert (
        "app.nutrition.application.fooddb_packet_mutation_guard_readiness.build_fooddb_packet_mutation_guard_readiness"
        in edges["packet_to_mutation_guard"]["evidence"]
    )
    assert (
        edges["exact_candidate_to_no_mutation"]["manager_style_guard"]
        == "exact_candidate_packets_remain_candidate_only_until_separate_promotion_lane"
    )
    assert (
        edges["websearch_candidate_to_selected_extract_request"]["manager_style_guard"]
        == "websearch_candidate_may_request_bounded_extract_but_cannot_become_truth"
    )
    assert (
        edges["selected_extract_request_to_extract_result_candidate"]["manager_style_guard"]
        == "bounded_extract_result_is_evidence_candidate_not_exact_card_truth"
    )
    assert (
        edges["extract_result_candidate_to_exact_review_packet"]["manager_style_guard"]
        == "exact_review_packet_is_review_only_not_manager_truth"
    )
    assert (
        edges["exact_review_packet_to_live_extract_preflight"]["manager_style_guard"]
        == "live_extract_preflight_authorizes_diagnostic_only_not_runtime_truth"
    )
    assert (
        edges["listed_components_to_approved_runtime_anchors"]["manager_style_guard"]
        == "listed_basket_components_may_estimate_only_when_runtime_anchor_is_approved"
    )
    assert matrix["summary"]["contract_backed"] == 13
    assert matrix["summary"]["draft"] == 0
    assert matrix["summary"]["missing"] == 0
    assert matrix["summary"]["next_required_slices"] == ["manager_fooddb_packet_seam_smoke"]


def test_activation_plan_documents_integration_readiness_matrix() -> None:
    content = DOC_PATH.read_text(encoding="utf-8-sig")

    assert "integration_readiness_matrix_update" in content
    assert "Manager decision -> retrieval intent from manager decision" in content
    assert "retrieval router -> SQLite FTS adapter" in content
    assert "WebSearch candidate -> selected extract request" in content
    assert "selected extract request -> extract result review candidate" in content
    assert "extract result review candidate -> exact-card review packet" in content
    assert "exact-card review packet -> live extract preflight" in content
    assert "packet -> mutation guard" in content
    assert "exact candidate -> no mutation" in content
