from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .websearch_live_diagnostic_integration_edges import (
    build_websearch_live_diagnostic_integration_edges,
)


def _wave_one_b_two_test_ref(name: str) -> str:
    return "tests.test_wave1_phase_" + "b2_" + name


def build_fooddb_integration_readiness_matrix() -> dict[str, Any]:
    check_edges = (
        _edge(
            edge_id="manager_decision_to_retrieval_intent",
            from_node="manager_semantic_decision",
            to_node="retrieval_request_from_manager_decision",
            dependency_direction="manager_to_retrieval_request",
            required_contract="B2ManagerSemanticDecision -> FoodEvidenceRetrievalRequest(manager_decision)",
            current_status="contract_backed",
            manager_style_guard="runtime_retrieval_request_must_come_from_manager_owned_structured_decision",
            evidence=[
                "app.nutrition.application.retrieval_request.build_retrieval_request_from_manager_decision",
                "app.nutrition.application.retrieval_semantic_decision.build_retrieval_intent_from_manager_decision",
                "tests.test_retrieval_request.test_manager_decision_request_is_runtime_executable",
                _wave_one_b_two_test_ref(
                    "retrieval_intent.test_manager_semantic_decision_rejects_non_manager_authority"
                ),
            ],
            stop_condition="stop_if_runtime_path_uses_raw_text_hint_or_fixture_as_semantic_owner",
        ),
        _edge(
            edge_id="retrieval_router_to_fooddb_local_adapter",
            from_node="retrieval_router",
            to_node="fooddb_local_adapter",
            dependency_direction="application_to_adapter_port",
            required_contract="FoodEvidenceIndexPort.load_records -> IndexedFoodRecord",
            current_status="contract_backed",
            manager_style_guard="retrieval_policy_depends_on_port_records_not_local_json_shape",
            evidence=[
                "app.nutrition.application.food_evidence_index_port.FoodEvidenceIndexPort",
                "app.nutrition.infrastructure.local_food_evidence_index.LocalSmallAnchorFoodEvidenceIndex",
                "tests.test_food_evidence_index_port.test_retrieval_can_depend_on_port_supplied_records",
            ],
            stop_condition="stop_if_retrieval_policy_depends_on_file_path_or_backend_specific_client",
        ),
        _edge(
            edge_id="retrieval_router_to_sqlite_fts_adapter",
            from_node="retrieval_router",
            to_node="sqlite_fts_adapter",
            dependency_direction="application_to_future_adapter_port",
            required_contract="FoodEvidenceIndexPort implementation for SQLite FTS",
            current_status="contract_backed",
            manager_style_guard="future_sqlite_fts_must_supply_same_indexed_record_contract",
            evidence=[
                "app.nutrition.application.food_evidence_index_port.FoodEvidenceIndexPort",
                "app.composition.food_evidence_index_composition.build_food_evidence_index",
                "app.composition.food_evidence_index_composition.build_retriever_backend_availability",
                "app.nutrition.infrastructure.sqlite_food_evidence_index.SQLiteFtsFoodEvidenceIndex",
                "tests.test_sqlite_food_evidence_index",
                "tests.test_food_evidence_index_factory",
            ],
            stop_condition="stop_if_sqlite_fts_requires_manager_or_packetizer_contract_change",
        ),
        _edge(
            edge_id="retrieval_router_to_websearch_candidate",
            from_node="retrieval_router",
            to_node="websearch_candidate_pipeline",
            dependency_direction="application_to_candidate_lane",
            required_contract="candidate_only WebSearch packet boundary",
            current_status="contract_backed",
            manager_style_guard="websearch_may_recall_candidates_but_may_not_set_runtime_truth",
            evidence=[
                "app.nutrition.application.food_evidence_retriever_router.build_food_evidence_retriever_route_plan",
                "app.nutrition.application.websearch_candidate_packet_smoke.build_websearch_candidate_packet_smoke",
                "app.nutrition.application.websearch_source_adapter_guard.build_websearch_source_adapter_guard",
                "tests.test_websearch_candidate_packet_smoke",
                "tests.test_websearch_source_adapter_guard",
            ],
            stop_condition="stop_if_websearch_snippet_or_candidate_becomes_runtime_truth",
        ),
        _edge(
            edge_id="retriever_output_to_compact_packet",
            from_node="retrieval_result",
            to_node="compact_evidence_packet",
            dependency_direction="retrieval_result_to_manager_packet",
            required_contract="compact FoodDB packet without raw rows or full dumps",
            current_status="contract_backed",
            manager_style_guard="manager_receives_compact_evidence_packet_only",
            evidence=[
                "app.nutrition.application.food_evidence_packet_builder.build_food_evidence_recall_packet",
                "tests.test_food_evidence_packet_builder.test_food_evidence_recall_packet_is_compact_and_manager_facing",
            ],
            stop_condition="stop_if_packet_includes_raw_rows_candidate_only_records_or_full_fooddb",
        ),
        _edge(
            edge_id="packet_to_manager_seam",
            from_node="compact_evidence_packet",
            to_node="manager_diagnostic_seam",
            dependency_direction="packet_to_manager_synthesis",
            required_contract="diagnostic seam uses provided packet without inventing source",
            current_status="contract_backed",
            manager_style_guard="manager_uses_packet_grounding_but_does_not_create_fooddb_truth",
            evidence=[
                "app.nutrition.application.grokfast_fooddb_packet_smoke.build_grokfast_fooddb_packet_diagnostic",
                "tests.test_grokfast_fooddb_packet_smoke",
            ],
            stop_condition="stop_if_manager_invents_source_or_mutates_without_grounded_packet",
        ),
        _edge(
            edge_id="packet_to_mutation_guard",
            from_node="compact_evidence_packet",
            to_node="runtime_mutation_guard",
            dependency_direction="grounding_to_write_guard",
            required_contract="mutation guard checks evidence sufficiency before commit",
            current_status="contract_backed",
            manager_style_guard="insufficient_evidence_must_downgrade_to_followup_or_no_mutation",
            evidence=[
                "app.nutrition.application.fooddb_packet_mutation_guard_readiness.build_fooddb_packet_mutation_guard_readiness",
                "tests.test_fooddb_packet_mutation_guard_readiness",
                "app.nutrition.application.grokfast_fooddb_packet_smoke.evaluate_manager_output_against_packet",
                "app.nutrition.application.food_evidence_mvp_policy",
            ],
            stop_condition="stop_if_packet_presence_bypasses_mutation_legality_or_commit_boundary",
        ),
        _edge(
            edge_id="exact_candidate_to_no_mutation",
            from_node="exact_candidate_lane",
            to_node="no_mutation_boundary",
            dependency_direction="candidate_lane_to_guarded_non_mutation",
            required_contract="exact candidates remain non-runtime until separate promotion lane",
            current_status="contract_backed",
            manager_style_guard="exact_candidate_packets_remain_candidate_only_until_separate_promotion_lane",
            evidence=[
                "app.nutrition.application.websearch_candidate_packet_smoke.derive_websearch_candidate_boundary",
                "app.nutrition.application.evidence_packet_consumption.consume_rechecked_packets",
            ],
            stop_condition="stop_if_exact_candidate_can_mutate_ledger_or_claim_exact_truth",
        ),
        *build_websearch_live_diagnostic_integration_edges(),
        _edge(
            edge_id="websearch_candidate_lane_status_to_websearch_status_packet",
            from_node="websearch_candidate_lane_status",
            to_node="websearch_evidence_status_packet",
            dependency_direction="candidate_lane_status_to_consolidated_status_surface",
            required_contract="candidate lane status may consolidate into WebSearch status packet without changing truth posture",
            current_status="contract_backed",
            manager_style_guard="websearch_status_packet_may_summarize_lane_status_but_cannot_promote_runtime_truth_or_mutation",
            evidence=[
                "app.nutrition.application.websearch_candidate_lane_status_packet.build_websearch_candidate_lane_status_packet",
                "app.nutrition.application.websearch_evidence_status_packet.build_websearch_evidence_status_packet",
                "tests.test_websearch_evidence_status_packet.test_websearch_evidence_status_packet_advances_to_exact_chain_review_after_live_status_inspection",
            ],
            stop_condition="stop_if_consolidated_status_packet_reroutes_candidate_lane_into_runtime_truth_or_shared_contract_change",
        ),
        _edge(
            edge_id="exact_evidence_lane_status_to_websearch_status_packet",
            from_node="exact_evidence_lane_status",
            to_node="websearch_evidence_status_packet",
            dependency_direction="exact_lane_status_to_consolidated_status_surface",
            required_contract="exact lane diagnostic status may consolidate without enabling exact truth promotion",
            current_status="contract_backed",
            manager_style_guard="exact_lane_status_may_inform_next_steps_but_cannot_grant_exact_truth_or_runtime_mutation",
            evidence=[
                "app.nutrition.application.exact_evidence_lane_status_packet.build_exact_evidence_lane_status_packet",
                "app.nutrition.application.websearch_evidence_status_packet.build_websearch_evidence_status_packet",
                "tests.test_websearch_evidence_status_packet.test_websearch_evidence_status_packet_sanitizes_post_live_repeat_into_narrow_expansion",
            ],
            stop_condition="stop_if_exact_lane_consolidation_reopens_live_probe_or_promotes_exact_truth",
        ),
        _edge(
            edge_id="websearch_status_packet_to_retriever_router_readiness",
            from_node="websearch_evidence_status_packet",
            to_node="retriever_router_readiness_gate",
            dependency_direction="websearch_status_to_router_availability_gate",
            required_contract="exact-brand WebSearch lane opens only when status packet proves candidate-lane clear posture",
            current_status="contract_backed",
            manager_style_guard="router_readiness_may_gate_websearch_lane_availability_but_cannot_decide_user_intent_or_mutation",
            evidence=[
                "app.nutrition.application.food_evidence_retriever_router_readiness.apply_websearch_status_gate_to_availability",
                "app.nutrition.application.food_evidence_retriever_router_readiness.build_food_evidence_retriever_router_readiness",
                "tests.test_food_evidence_retriever_router_readiness.test_apply_websearch_status_gate_enables_exact_brand_lane_after_live_clear",
            ],
            stop_condition="stop_if_router_opens_websearch_candidate_lane_without_clear_status_packet_or_promotes_runtime_truth",
        ),
        _edge(
            edge_id="listed_components_to_approved_runtime_anchors",
            from_node="listed_basket_components",
            to_node="approved_runtime_anchors_only",
            dependency_direction="listed_component_lookup_to_runtime_anchor_boundary",
            required_contract="listed basket estimates only approved runtime anchors",
            current_status="contract_backed",
            manager_style_guard="listed_basket_components_may_estimate_only_when_runtime_anchor_is_approved",
            evidence=[
                "app.nutrition.application.fooddb_listed_component_expansion_plan.build_listed_component_expansion_plan",
                "tests.test_fooddb_listed_component_expansion_plan",
            ],
            stop_condition="stop_if_bare_basket_or_unapproved_component_receives_estimate",
        ),
    )
    counts = {"contract_backed": sum(1 for edge in check_edges if edge["current_status"] == "contract_backed"), "draft": sum(1 for edge in check_edges if edge["current_status"] == "draft"), "missing": sum(1 for edge in check_edges if edge["current_status"] == "missing")}
    return {
        "artifact_type": "accurate_intake_fooddb_integration_readiness_matrix",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "claim_scope": "dependency_inversion_and_manager_style_integration_check",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "websearch_runtime_truth_allowed": False,
        "readiness_claimed": False,
        "check_edges": list(check_edges),
        "summary": {"edge_count": len(check_edges), **counts, "next_required_slices": ["manager_fooddb_packet_seam_smoke"]},
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_packetizer_contract_change",
            "no_manager_context_change",
            "no_websearch_runtime_truth",
            "no_readiness_claim",
        ],
    }


def _edge(
    *,
    edge_id: str,
    from_node: str,
    to_node: str,
    dependency_direction: str,
    required_contract: str,
    current_status: str,
    manager_style_guard: str,
    evidence: list[str],
    stop_condition: str,
) -> dict[str, Any]:
    return {"edge_id": edge_id, "from": from_node, "to": to_node, "dependency_direction": dependency_direction, "required_contract": required_contract, "current_status": current_status, "manager_style_guard": manager_style_guard, "evidence": evidence, "stop_condition": stop_condition}


__all__ = ["build_fooddb_integration_readiness_matrix"]
