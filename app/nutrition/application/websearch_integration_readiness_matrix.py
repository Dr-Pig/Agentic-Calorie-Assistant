from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_websearch_integration_readiness_matrix() -> dict[str, Any]:
    edges = (
        _edge(
            "websearch_candidate_lane_status_to_websearch_status_packet",
            "websearch_candidate_lane_status",
            "websearch_evidence_status_packet",
            "candidate_lane_status_to_consolidated_status_surface",
            "candidate lane status may consolidate without promoting runtime truth",
            "status packet summarizes candidate lane only; it does not choose truth or mutation",
            [
                "app.nutrition.application.websearch_candidate_lane_status_packet.build_websearch_candidate_lane_status_packet",
                "app.nutrition.application.websearch_evidence_status_packet.build_websearch_evidence_status_packet",
                "tests.test_websearch_evidence_status_packet.test_websearch_evidence_status_packet_advances_to_exact_chain_review_after_live_status_inspection",
            ],
            "stop_if_status_packet_rewrites_candidate_lane_into_runtime_truth_or_shared_contract_change",
        ),
        _edge(
            "exact_evidence_lane_status_to_websearch_status_packet",
            "exact_evidence_lane_status",
            "websearch_evidence_status_packet",
            "exact_lane_status_to_consolidated_status_surface",
            "exact lane diagnostic status may consolidate without exact truth promotion",
            "status packet may point to exact-chain followthrough but cannot grant exact truth or mutation",
            [
                "app.nutrition.application.exact_evidence_lane_status_packet.build_exact_evidence_lane_status_packet",
                "app.nutrition.application.websearch_evidence_status_packet.build_websearch_evidence_status_packet",
                "tests.test_websearch_evidence_status_packet.test_websearch_evidence_status_packet_sanitizes_post_live_repeat_into_narrow_expansion",
            ],
            "stop_if_exact_lane_consolidation_reopens_live_probe_or_promotes_exact_truth",
        ),
        _edge(
            "websearch_contract_handoff_to_websearch_status_packet",
            "websearch_manager_contract_handoff",
            "websearch_evidence_status_packet",
            "contract_handoff_to_consolidated_status_surface",
            "manager contract handoff may inform consolidated status without changing manager semantics",
            "handoff proof may classify contract posture but cannot patch manager semantics",
            [
                "app.nutrition.application.websearch_manager_contract_handoff.build_websearch_manager_contract_handoff",
                "app.nutrition.application.websearch_evidence_status_packet.build_websearch_evidence_status_packet",
                "tests.test_websearch_manager_contract_handoff",
            ],
            "stop_if_handoff_selected_step_becomes_runtime_truth_or_mutation_authority",
        ),
        _edge(
            "websearch_status_packet_to_retriever_router_readiness",
            "websearch_evidence_status_packet",
            "retriever_router_readiness_gate",
            "websearch_status_to_router_availability_gate",
            "router may open exact-brand WebSearch lane only when status packet proves clear candidate-lane posture",
            "router readiness can enable or disable the lane; it cannot_grant_runtime_truth_or_mutation",
            [
                "app.nutrition.application.food_evidence_retriever_router_readiness.apply_websearch_status_gate_to_availability",
                "app.nutrition.application.food_evidence_retriever_router_readiness.build_food_evidence_retriever_router_readiness",
                "tests.test_food_evidence_retriever_router_readiness.test_apply_websearch_status_gate_enables_exact_brand_lane_after_live_clear",
            ],
            "stop_if_router_opens_websearch_lane_without_clear_status_or_cannot_grant_runtime_truth_or_mutation",
        ),
        _edge(
            "websearch_exact_candidate_chain_status_to_live_runner_readiness_packet",
            "websearch_exact_candidate_chain_status",
            "websearch_live_runner_readiness_packet",
            "chain_status_to_explicit_live_runner_gate",
            "live runner readiness requires clear exact candidate chain proof",
            "live runner readiness validates chain proof before explicit provider diagnostic only",
            [
                "app.nutrition.application.websearch_exact_candidate_chain_status.build_websearch_exact_candidate_chain_status",
                "app.nutrition.application.websearch_live_runner_readiness_packet.build_websearch_live_runner_readiness_packet",
                "tests.test_websearch_live_runner_readiness_packet.test_websearch_live_runner_readiness_blocks_chain_not_clear",
            ],
            "stop_if_live_runner_readiness_accepts_chain_drift_or_review_packet_mismatch",
        ),
        _edge(
            "websearch_live_extract_preflight_to_live_runner_readiness_packet",
            "websearch_live_extract_preflight",
            "websearch_live_runner_readiness_packet",
            "diagnostic_preflight_to_explicit_live_runner_gate",
            "live runner readiness requires clear preflight before explicit provider diagnostic",
            "preflight may authorize later live diagnostics but cannot grant runtime truth",
            [
                "app.nutrition.application.websearch_live_extract_preflight.build_websearch_live_extract_preflight",
                "app.nutrition.application.websearch_live_runner_readiness_packet.build_websearch_live_runner_readiness_packet",
                "tests.test_websearch_live_runner_readiness_packet",
            ],
            "stop_if_live_runner_readiness_skips_preflight_clearance_or_claims_runtime_truth",
        ),
        _edge(
            "websearch_live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic",
            "websearch_live_runner_readiness_packet",
            "grokfast_websearch_packet_live_diagnostic_runner",
            "explicit_live_runner_gate_to_provider_diagnostic",
            "explicit allow-live plus clear readiness packet required before provider call",
            "live runner readiness opens a diagnostic canary only; it does not grant runtime truth or mutation",
            [
                "app.nutrition.application.websearch_live_runner_readiness_packet.build_websearch_live_runner_readiness_packet",
                "scripts.run_accurate_intake_websearch_live_diagnostic_bundle.main",
                "tests.test_websearch_live_runner_readiness_packet",
                "tests.test_grokfast_websearch_packet_smoke.test_grokfast_websearch_packet_smoke_live_requires_runner_readiness_packet",
            ],
            "stop_if_grokfast_live_diagnostic_runs_without_readiness_packet_or_without_explicit_allow_live",
        ),
    )
    return {
        "artifact_type": "accurate_intake_websearch_integration_readiness_matrix",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "claim_scope": "websearch_status_and_live_readiness_integration_check",
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "readiness_claimed": False,
        "check_edges": list(edges),
        "summary": {
            "edge_count": len(edges),
            "contract_backed": len(edges),
            "next_required_slices": ["inspect_websearch_status_packet"],
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _edge(
    edge_id: str,
    from_node: str,
    to_node: str,
    dependency_direction: str,
    required_contract: str,
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
        "current_status": "contract_backed",
        "manager_style_guard": manager_style_guard,
        "evidence": evidence,
        "stop_condition": stop_condition,
    }


__all__ = ["build_websearch_integration_readiness_matrix"]
