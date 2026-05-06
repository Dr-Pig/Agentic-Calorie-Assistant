from __future__ import annotations

from typing import Any


def build_websearch_live_diagnostic_activation_edges() -> tuple[dict[str, Any], ...]:
    return (
        _edge(
            edge_id="exact_candidate_chain_status_to_live_runner_readiness_packet",
            from_node="websearch_exact_candidate_chain_status",
            to_node="websearch_live_runner_readiness_packet",
            dependency_direction="chain_status_to_explicit_live_runner_gate",
            required_contract="live runner readiness requires exact candidate chain proof aligned to review packet",
            current_status="contract_backed",
            manager_style_guard="live_runner_readiness_requires_chain_status_proof_before_explicit_live_diagnostic",
            evidence=[
                "app.nutrition.application.websearch_exact_candidate_chain_status.build_websearch_exact_candidate_chain_status",
                "app.nutrition.application.websearch_live_runner_readiness_packet.build_websearch_live_runner_readiness_packet",
                "app.nutrition.application.websearch_live_runner_readiness_checks.live_runner_readiness_input_blockers",
                "tests.test_websearch_live_runner_readiness_packet",
                "tests.test_websearch_live_runner_readiness_packet.test_websearch_live_runner_readiness_blocks_chain_not_clear",
            ],
            stop_condition="stop_if_live_runner_readiness_accepts_chain_drift_or_review_packet_mismatch",
        ),
        _edge(
            edge_id="live_extract_preflight_to_live_runner_readiness_packet",
            from_node="websearch_live_extract_preflight",
            to_node="websearch_live_runner_readiness_packet",
            dependency_direction="diagnostic_preflight_to_explicit_live_runner_gate",
            required_contract="live runner readiness requires clear preflight before explicit provider diagnostic",
            current_status="contract_backed",
            manager_style_guard="live_runner_readiness_requires_clear_preflight_without_granting_runtime_truth",
            evidence=[
                "app.nutrition.application.websearch_live_extract_preflight.build_websearch_live_extract_preflight",
                "app.nutrition.application.websearch_live_runner_readiness_packet.build_websearch_live_runner_readiness_packet",
                "app.nutrition.application.websearch_live_runner_readiness_checks.is_websearch_live_runner_readiness_clear",
                "tests.test_websearch_live_runner_readiness_packet",
            ],
            stop_condition="stop_if_live_runner_readiness_skips_preflight_clearance_or_claims_runtime_truth",
        ),
        _edge(
            edge_id="live_runner_readiness_packet_to_grokfast_websearch_live_diagnostic",
            from_node="websearch_live_runner_readiness_packet",
            to_node="grokfast_websearch_packet_live_diagnostic_runner",
            dependency_direction="explicit_live_runner_gate_to_provider_diagnostic",
            required_contract="explicit allow-live plus clear readiness packet required before provider call",
            current_status="contract_backed",
            manager_style_guard="live_runner_readiness_may_open_explicit_grokfast_diagnostic_but_not_runtime_truth_or_websearch_tool_loop",
            evidence=[
                "app.nutrition.application.websearch_live_runner_readiness_packet.build_websearch_live_runner_readiness_packet",
                "scripts.run_accurate_intake_grokfast_websearch_packet_smoke.main",
                "scripts.run_accurate_intake_websearch_live_diagnostic_bundle.main",
                "tests.test_websearch_live_runner_readiness_packet",
                "tests.test_grokfast_websearch_packet_smoke.test_grokfast_websearch_packet_smoke_live_requires_runner_readiness_packet",
                "tests.test_websearch_live_diagnostic_bundle_runner",
            ],
            stop_condition="stop_if_grokfast_live_diagnostic_runs_without_readiness_packet_or_without_explicit_allow_live",
        ),
        _edge(
            edge_id="live_extract_preflight_to_websearch_live_diagnostic_report",
            from_node="websearch_live_extract_preflight",
            to_node="websearch_live_diagnostic_report",
            dependency_direction="diagnostic_preflight_to_live_report_classification",
            required_contract="live diagnostic report must be gated by preflight and remain diagnostic-only",
            current_status="contract_backed",
            manager_style_guard="live_report_may_classify_seam_status_but_cannot_claim_websearch_truth_or_readiness",
            evidence=[
                "scripts.run_accurate_intake_grokfast_websearch_packet_smoke.main",
                "app.nutrition.application.websearch_live_extract_preflight.is_websearch_live_extract_preflight_clear",
                "app.nutrition.application.grokfast_websearch_packet_smoke.build_grokfast_websearch_packet_diagnostic",
                "app.nutrition.application.websearch_live_diagnostic_report.build_websearch_live_diagnostic_report",
                "tests.test_websearch_live_extract_preflight",
                "tests.test_grokfast_websearch_packet_smoke",
                "tests.test_grokfast_websearch_packet_smoke.test_grokfast_websearch_packet_smoke_live_blocks_preflight_review_packet_mismatch",
                "tests.test_grokfast_websearch_packet_smoke.test_grokfast_websearch_packet_smoke_live_blocks_same_ref_packet_drift",
                "tests.test_websearch_live_diagnostic_report",
            ],
            stop_condition="stop_if_live_report_is_generated_without_preflight_or_claims_runtime_truth",
        ),
        _edge(
            edge_id="websearch_live_report_to_manager_contract_probe",
            from_node="websearch_live_diagnostic_report",
            to_node="websearch_manager_contract_probe",
            dependency_direction="live_report_to_sanitized_contract_probe",
            required_contract="provider contract failures are localized without raw payload leakage",
            current_status="contract_backed",
            manager_style_guard="websearch_live_diagnostic_may_identify_contract_blockers_but_not_repair_manager_semantics",
            evidence=[
                "app.nutrition.application.websearch_live_diagnostic_report.build_websearch_live_diagnostic_report",
                "app.nutrition.application.websearch_manager_contract_probe.build_websearch_manager_contract_probe",
                "tests.test_websearch_live_diagnostic_report",
                "tests.test_websearch_manager_contract_probe",
            ],
            stop_condition="stop_if_websearch_contract_probe_leaks_raw_provider_payload_or_changes_manager_contract",
        ),
        _edge(
            edge_id="websearch_contract_probe_to_repair_pack",
            from_node="websearch_manager_contract_probe",
            to_node="websearch_manager_contract_repair_pack",
            dependency_direction="contract_probe_to_sanitized_repair_inputs",
            required_contract="repair pack emits allowlisted diagnostic fields only",
            current_status="contract_backed",
            manager_style_guard="repair_pack_hands_off_contract_evidence_without_prompt_schema_or_semantic_changes",
            evidence=[
                "app.nutrition.application.websearch_manager_contract_repair_pack.build_websearch_manager_contract_repair_pack",
                "tests.test_websearch_manager_contract_repair_pack",
            ],
            stop_condition="stop_if_repair_pack_echoes_untrusted_case_ids_statuses_or_raw_artifact_strings",
        ),
        _edge(
            edge_id="websearch_repair_pack_to_contract_handoff",
            from_node="websearch_manager_contract_repair_pack",
            to_node="websearch_manager_contract_handoff",
            dependency_direction="repair_pack_to_contract_owner_handoff",
            required_contract="manager contract handoff consumes sanitized repair evidence and alignment checks",
            current_status="contract_backed",
            manager_style_guard="handoff_may_route_contract_blockers_to_manager_owner_but_cannot_patch_manager_semantics",
            evidence=[
                "app.nutrition.application.websearch_manager_contract_handoff.build_websearch_manager_contract_handoff",
                "tests.test_websearch_manager_contract_handoff",
            ],
            stop_condition="stop_if_handoff_skips_repair_pack_alignment_or_reemits_untrusted_summary_values",
        ),
        _edge(
            edge_id="websearch_contract_handoff_to_candidate_lane_status",
            from_node="websearch_manager_contract_handoff",
            to_node="websearch_candidate_lane_status_packet",
            dependency_direction="contract_handoff_to_live_gate",
            required_contract="candidate lane requires explicit contract handoff proof before live diagnostic advancement",
            current_status="contract_backed",
            manager_style_guard="candidate_lane_may_block_or_forward_contract_status_but_cannot_decide_manager_semantics",
            evidence=[
                "app.nutrition.application.websearch_manager_contract_handoff.build_websearch_manager_contract_handoff",
                "app.nutrition.application.websearch_candidate_lane_handoff_gate.compact_websearch_manager_contract_gate",
                "tests.test_websearch_manager_contract_handoff",
                "tests.test_websearch_candidate_lane_status_packet",
            ],
            stop_condition="stop_if_candidate_lane_advances_to_live_without_verified handoff proof_or_leaks_untrusted_next_slice",
        ),
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


__all__ = ["build_websearch_live_diagnostic_activation_edges"]
