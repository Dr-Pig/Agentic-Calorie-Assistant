from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


def build_fooddb_manager_contract_handoff(
    *,
    live_diagnostic_report: dict[str, Any],
    contract_probe_artifact: dict[str, Any],
    repair_pack_artifact: dict[str, Any],
) -> dict[str, Any]:
    if str(live_diagnostic_report.get("artifact_type") or "") != "accurate_intake_fooddb_live_diagnostic_report":
        raise ValueError("unsupported_fooddb_manager_contract_handoff_live_report")
    if str(contract_probe_artifact.get("artifact_type") or "") != "accurate_intake_fooddb_manager_contract_probe":
        raise ValueError("unsupported_fooddb_manager_contract_handoff_contract_probe")
    if str(repair_pack_artifact.get("artifact_type") or "") != "accurate_intake_fooddb_manager_contract_repair_pack":
        raise ValueError("unsupported_fooddb_manager_contract_handoff_repair_pack")

    seam_status = str(live_diagnostic_report.get("seam_status") or "")
    contract_failure_detected = contract_probe_artifact.get("contract_failure_detected") is True
    repair_next = str(repair_pack_artifact.get("next_recommended_slice") or "")
    repair_summary = dict(repair_pack_artifact.get("summary") or {})
    probe_summary = dict(contract_probe_artifact.get("summary") or {})
    probe_case_count = int(probe_summary.get("case_count", 0) or 0)
    repair_case_count = int(repair_summary.get("case_count", 0) or 0)

    alignment_blockers: list[str] = []
    if seam_status == "provider_contract_blocked" and not contract_failure_detected:
        alignment_blockers.append("live_report_probe_contract_status_mismatch")
    if seam_status == "live_diagnostic_pass" and contract_failure_detected:
        alignment_blockers.append("live_pass_with_contract_failure_detected")
    if repair_next == "repair_artifact_alignment_required":
        alignment_blockers.append("repair_pack_alignment_required")
    if contract_failure_detected and repair_case_count == 0:
        alignment_blockers.append("repair_pack_empty_for_contract_failure")
    if contract_failure_detected and probe_case_count != repair_case_count:
        alignment_blockers.append("probe_repair_case_count_mismatch")

    if alignment_blockers:
        status = "blocked_contract_handoff_alignment"
        selected_next_step = "repair_artifact_alignment_required"
        handoff_ready = False
    elif seam_status == "provider_contract_blocked" and contract_failure_detected:
        status = "ready_for_manager_contract_owner"
        selected_next_step = repair_next or "tighten_fooddb_manager_contract_prompt_or_transport"
        handoff_ready = True
    elif seam_status == "packet_boundary_blocked":
        status = "return_to_fooddb_packet_boundary"
        selected_next_step = "narrow_fooddb_packet_boundary_or_prompt_probe"
        handoff_ready = False
    elif seam_status == "live_diagnostic_pass":
        status = "fooddb_contract_unblocked"
        selected_next_step = "grokfast_websearch_packet_live_diagnostic"
        handoff_ready = False
    else:
        status = "insufficient_contract_handoff_evidence"
        selected_next_step = "inspect_fooddb_live_failure_taxonomy"
        handoff_ready = False

    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_handoff_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_handoff_only",
        "claim_scope": "fooddb_live_contract_handoff_to_manager_owner",
        "status": status,
        "selected_next_step": selected_next_step,
        "handoff_ready": handoff_ready,
        "downstream_owner": "manager_runtime_contract",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "shared_contract_changed": False,
        "readiness_claimed": False,
        "summary": {
            "live_seam_status": seam_status,
            "contract_failure_detected": contract_failure_detected,
            "probe_case_count": probe_case_count,
            "repair_case_count": repair_case_count,
            "aggregate_missing_required_fields": dict(
                probe_summary.get("aggregate_missing_required_fields") or {}
            ),
            "alias_hint_counts": dict(repair_summary.get("alias_hint_counts") or {}),
            "probe_match_status_counts": dict(repair_summary.get("probe_match_status_counts") or {}),
            "trace_status_counts": dict(repair_summary.get("trace_status_counts") or {}),
            "alignment_blocker_count": len(alignment_blockers),
        },
        "alignment_blockers": alignment_blockers,
        "artifact_chain": {
            "live_diagnostic_report": {
                "seam_status": seam_status,
                "source_live_provider_used": live_diagnostic_report.get("source_live_provider_used"),
                "next_recommended_slice": live_diagnostic_report.get("next_recommended_slice"),
            },
            "contract_probe": {
                "contract_failure_detected": contract_failure_detected,
                "next_recommended_slice": contract_probe_artifact.get("next_recommended_slice"),
            },
            "repair_pack": {
                "next_recommended_slice": repair_next,
            },
        },
        "non_claims": [
            "no_live_provider_call",
            "no_runtime_truth_promotion",
            "no_mutation_legality_change",
            "no_packetizer_format_change",
            "no_manager_context_change",
            "no_shared_contract_change",
            "no_readiness_claim",
        ],
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_manager_contract_handoff"]
