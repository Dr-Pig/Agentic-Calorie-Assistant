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
        "websearch_live_case_matrix_to_live_extract_preflight",
        "exact_candidate_chain_status_to_live_runner_readiness_packet",
        "live_extract_preflight_to_live_runner_readiness_packet",
        "live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic",
        "live_extract_preflight_to_websearch_live_diagnostic_report",
        "websearch_live_report_to_manager_contract_probe",
        "websearch_contract_probe_to_repair_pack",
        "websearch_repair_pack_to_contract_handoff",
        "websearch_contract_handoff_to_candidate_lane_status",
        "listed_components_to_approved_runtime_anchors",
    }

    assert edges["manager_decision_to_retrieval_intent"]["current_status"] == "contract_backed"
    assert edges["retrieval_router_to_sqlite_fts_adapter"]["current_status"] == "contract_backed"
    assert edges["retrieval_router_to_websearch_candidate"]["current_status"] == "contract_backed"
    assert (
        "app.nutrition.application.websearch_source_adapter_guard.build_websearch_source_adapter_guard"
        in edges["retrieval_router_to_websearch_candidate"]["evidence"]
    )
    assert "tests.test_websearch_source_adapter_guard" in edges[
        "retrieval_router_to_websearch_candidate"
    ]["evidence"]
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
        edges["websearch_live_case_matrix_to_live_extract_preflight"]["manager_style_guard"]
        == "live_preflight_requires_fixed_anti_overfit_case_matrix_not_ad_hoc_happy_path"
    )
    assert (
        "tests.test_websearch_live_extract_preflight.test_live_extract_preflight_blocks_case_level_matrix_overclaims"
        in edges["websearch_live_case_matrix_to_live_extract_preflight"]["evidence"]
    )
    assert (
        edges["exact_candidate_chain_status_to_live_runner_readiness_packet"][
            "manager_style_guard"
        ]
        == "live_runner_readiness_requires_chain_status_proof_before_explicit_live_diagnostic"
    )
    assert (
        "tests.test_websearch_live_runner_readiness_packet.test_websearch_live_runner_readiness_blocks_chain_not_clear"
        in edges["exact_candidate_chain_status_to_live_runner_readiness_packet"]["evidence"]
    )
    assert (
        edges["live_extract_preflight_to_live_runner_readiness_packet"][
            "manager_style_guard"
        ]
        == "live_runner_readiness_requires_clear_preflight_without_granting_runtime_truth"
    )
    assert (
        "app.nutrition.application.websearch_live_runner_readiness_checks.is_websearch_live_runner_readiness_clear"
        in edges["live_extract_preflight_to_live_runner_readiness_packet"]["evidence"]
    )
    assert (
        edges["live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic"][
            "manager_style_guard"
        ]
        == "live_runner_readiness_may_open_explicit_grokfast_diagnostic_but_not_runtime_truth_or_websearch_tool_loop"
    )
    assert (
        "tests.test_grokfast_websearch_packet_smoke.test_grokfast_websearch_packet_smoke_live_requires_runner_readiness_packet"
        in edges["live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic"][
            "evidence"
        ]
    )
    assert (
        edges["live_extract_preflight_to_websearch_live_diagnostic_report"]["manager_style_guard"]
        == "live_report_may_classify_seam_status_but_cannot_claim_websearch_truth_or_readiness"
    )
    assert (
        "scripts.run_accurate_intake_grokfast_websearch_packet_smoke.main"
        in edges["live_extract_preflight_to_websearch_live_diagnostic_report"]["evidence"]
    )
    assert (
        "tests.test_grokfast_websearch_packet_smoke.test_grokfast_websearch_packet_smoke_live_blocks_same_ref_packet_drift"
        in edges["live_extract_preflight_to_websearch_live_diagnostic_report"]["evidence"]
    )
    assert (
        edges["websearch_live_report_to_manager_contract_probe"]["manager_style_guard"]
        == "websearch_live_diagnostic_may_identify_contract_blockers_but_not_repair_manager_semantics"
    )
    assert (
        edges["websearch_contract_probe_to_repair_pack"]["manager_style_guard"]
        == "repair_pack_hands_off_contract_evidence_without_prompt_schema_or_semantic_changes"
    )
    assert (
        edges["websearch_repair_pack_to_contract_handoff"]["manager_style_guard"]
        == "handoff_may_route_contract_blockers_to_manager_owner_but_cannot_patch_manager_semantics"
    )
    assert (
        edges["websearch_contract_handoff_to_candidate_lane_status"]["manager_style_guard"]
        == "candidate_lane_may_block_or_forward_contract_status_but_cannot_decide_manager_semantics"
    )
    assert (
        "app.nutrition.application.websearch_candidate_lane_handoff_gate.compact_websearch_manager_contract_gate"
        in edges["websearch_contract_handoff_to_candidate_lane_status"]["evidence"]
    )
    assert (
        "verified handoff proof"
        in edges["websearch_contract_handoff_to_candidate_lane_status"]["stop_condition"]
    )
    assert (
        edges["listed_components_to_approved_runtime_anchors"]["manager_style_guard"]
        == "listed_basket_components_may_estimate_only_when_runtime_anchor_is_approved"
    )
    assert matrix["summary"]["contract_backed"] == 22
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
    assert "WebSearch GrokFast case matrix -> live extract preflight" in content
    assert "exact candidate chain status -> live runner readiness packet" in content
    assert "live extract preflight -> live runner readiness packet" in content
    assert "live runner readiness packet -> GrokFast WebSearch packet live diagnostic runner" in content
    assert "live extract preflight -> WebSearch live diagnostic report" in content
    assert "WebSearch live diagnostic report -> Manager contract probe" in content
    assert "WebSearch Manager contract probe -> repair pack" in content
    assert "WebSearch Manager contract repair pack -> handoff" in content
    assert "WebSearch Manager contract handoff -> candidate lane status" in content
    assert "packet -> mutation guard" in content
    assert "exact candidate -> no mutation" in content
    assert "2026-05-05_grokfast_websearch_packet_live_diagnostic" in content
    assert "seam_status: live_diagnostic_pass" in content
    assert "can_expand_websearch_candidate_pipeline: true" in content
