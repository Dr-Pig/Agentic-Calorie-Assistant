from __future__ import annotations

from typing import Any

from .websearch_live_diagnostic_activation_edges import (
    build_websearch_live_diagnostic_activation_edges,
)


def build_websearch_live_diagnostic_integration_edges() -> tuple[dict[str, Any], ...]:
    return (
        _edge(
            edge_id="websearch_candidate_to_selected_extract_request",
            from_node="websearch_candidate_pipeline",
            to_node="selected_extract_request_packet",
            dependency_direction="candidate_lane_to_bounded_extract_request",
            required_contract="selected extract request is bounded and candidate-only",
            current_status="contract_backed",
            manager_style_guard="websearch_candidate_may_request_bounded_extract_but_cannot_become_truth",
            evidence=[
                "app.nutrition.application.websearch_selected_extract_packet_smoke.build_websearch_selected_extract_packet_smoke",
                "tests.test_websearch_selected_extract_packet_smoke",
            ],
            stop_condition="stop_if_selected_extract_request_includes_raw_content_or_runtime_truth",
        ),
        _edge(
            edge_id="selected_extract_request_to_extract_result_candidate",
            from_node="selected_extract_request_packet",
            to_node="extract_result_review_candidate",
            dependency_direction="bounded_extract_request_to_review_candidate",
            required_contract="extract results stay review candidates with provenance and no raw content",
            current_status="contract_backed",
            manager_style_guard="bounded_extract_result_is_evidence_candidate_not_exact_card_truth",
            evidence=[
                "app.nutrition.application.websearch_extract_result_candidate_smoke.build_websearch_extract_result_candidate_smoke",
                "tests.test_websearch_extract_result_candidate_smoke",
            ],
            stop_condition="stop_if_extract_result_candidate_allows_promotion_mutation_or_raw_content",
        ),
        _edge(
            edge_id="extract_result_candidate_to_exact_review_packet",
            from_node="extract_result_review_candidate",
            to_node="exact_card_review_packet",
            dependency_direction="extract_candidate_to_review_packet",
            required_contract="exact-card review packet preserves checklist without approval authority",
            current_status="contract_backed",
            manager_style_guard="exact_review_packet_is_review_only_not_manager_truth",
            evidence=[
                "app.nutrition.application.websearch_exact_candidate_review_packet.build_websearch_exact_candidate_review_packet",
                "tests.test_websearch_exact_candidate_review_packet",
            ],
            stop_condition="stop_if_exact_review_packet_can_approve_promote_or_mutate",
        ),
        _edge(
            edge_id="exact_review_packet_to_live_extract_preflight",
            from_node="exact_card_review_packet",
            to_node="websearch_live_extract_preflight",
            dependency_direction="review_packet_to_diagnostic_preflight",
            required_contract="live extract preflight requires explicit allow-live and keeps runtime truth closed",
            current_status="contract_backed",
            manager_style_guard="live_extract_preflight_authorizes_diagnostic_only_not_runtime_truth",
            evidence=[
                "app.nutrition.application.websearch_live_extract_preflight.build_websearch_live_extract_preflight",
                "app.nutrition.application.websearch_live_extract_preflight.is_websearch_live_extract_preflight_clear",
                "tests.test_websearch_live_extract_preflight",
            ],
            stop_condition="stop_if_live_extract_preflight_claims_runtime_truth_or_omits_explicit_live_flag",
        ),
        _edge(
            edge_id="websearch_live_case_matrix_to_live_extract_preflight",
            from_node="websearch_grokfast_live_diagnostic_case_matrix",
            to_node="websearch_live_extract_preflight",
            dependency_direction="case_matrix_to_diagnostic_preflight",
            required_contract="fixed WebSearch live diagnostic case matrix required before live preflight clears",
            current_status="contract_backed",
            manager_style_guard="live_preflight_requires_fixed_anti_overfit_case_matrix_not_ad_hoc_happy_path",
            evidence=[
                "app.nutrition.application.websearch_grokfast_live_diagnostic_case_matrix.build_websearch_grokfast_live_diagnostic_case_matrix_artifact",
                "app.nutrition.application.websearch_live_extract_preflight.build_websearch_live_extract_preflight",
                "tests.test_websearch_grokfast_live_diagnostic_case_matrix",
                "tests.test_websearch_live_extract_preflight.test_live_extract_preflight_blocks_missing_or_ad_hoc_case_matrix",
                "tests.test_websearch_live_extract_preflight.test_live_extract_preflight_blocks_case_matrix_overfit_or_live_claims",
                "tests.test_websearch_live_extract_preflight.test_live_extract_preflight_blocks_case_level_matrix_overclaims",
            ],
            stop_condition="stop_if_live_preflight_accepts_ad_hoc_case_matrix_or_case_level_runtime_overclaim",
        ),
        *build_websearch_live_diagnostic_activation_edges(),
    )


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
    return {
        "edge_id": edge_id,
        "from": from_node,
        "to": to_node,
        "dependency_direction": dependency_direction,
        "required_contract": required_contract,
        "current_status": current_status,
        "manager_style_guard": manager_style_guard,
        "evidence": evidence,
        "stop_condition": stop_condition,
    }


__all__ = ["build_websearch_live_diagnostic_integration_edges"]
