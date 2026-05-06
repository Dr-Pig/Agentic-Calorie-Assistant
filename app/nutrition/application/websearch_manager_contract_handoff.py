from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .websearch_live_report_handoff_gate import websearch_live_report_handoff_blockers


WEBSEARCH_MANAGER_CONTRACT_HANDOFF_NON_CLAIMS = [
    "no_live_provider_call",
    "no_live_websearch_call",
    "no_prompt_or_schema_change",
    "no_manager_contract_change",
    "no_runtime_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_runtime_mutation",
    "no_packetizer_format_change",
    "no_manager_context_change",
    "no_shared_contract_change",
    "no_readiness_claim",
]
_ALLOWED_SEAM_STATUSES = {
    "candidate_boundary_blocked",
    "diagnostic_fail_unclassified",
    "fixture_only_live_not_checked",
    "live_diagnostic_pass",
    "provider_contract_blocked",
}
_ALLOWED_NEXT_SLICES = {
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_sanitized_failure_taxonomy",
    "inspect_websearch_live_failure_taxonomy",
    "narrow_grokfast_websearch_manager_contract_probe",
    "narrow_prompt_schema_intent_alias_probe",
    "narrow_websearch_packet_boundary_or_prompt_probe",
    "repair_artifact_alignment_required",
    "run_explicit_grokfast_websearch_packet_live_diagnostic",
    "tighten_websearch_manager_contract_prompt_or_transport",
    "websearch_candidate_pipeline_narrow_expansion",
}
_ALLOWED_SUMMARY_COUNT_KEYS = {
    "confidence",
    "evidence_posture",
    "exactness",
    "intent",
    "intent_type_present_intent_missing",
    "manager_action",
    "repair_ack",
    "target_attachment",
    "workflow_effect",
}


def build_websearch_manager_contract_handoff(
    *,
    live_diagnostic_report: dict[str, Any],
    contract_probe_artifact: dict[str, Any],
    repair_pack_artifact: dict[str, Any],
    preflight_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    if (
        str(live_diagnostic_report.get("artifact_type") or "")
        != "accurate_intake_websearch_live_diagnostic_report"
    ):
        raise ValueError("unsupported_websearch_manager_contract_handoff_live_report")
    if (
        str(contract_probe_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_manager_contract_probe"
    ):
        raise ValueError("unsupported_websearch_manager_contract_handoff_contract_probe")
    if (
        str(repair_pack_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_manager_contract_repair_pack"
    ):
        raise ValueError("unsupported_websearch_manager_contract_handoff_repair_pack")

    seam_status = _safe_enum(
        live_diagnostic_report.get("seam_status"),
        allowed_values=_ALLOWED_SEAM_STATUSES,
        fallback="unknown",
    )
    probe_summary = dict(contract_probe_artifact.get("summary") or {})
    repair_summary = dict(repair_pack_artifact.get("summary") or {})
    probe_case_count = int(probe_summary.get("case_count", 0) or 0)
    probe_fail_count = int(probe_summary.get("fail_count", 0) or 0)
    repair_case_count = int(repair_summary.get("case_count", 0) or 0)
    contract_failure_detected = (
        contract_probe_artifact.get("contract_failure_detected") is True
        or str(contract_probe_artifact.get("status") or "") == "diagnostic_fail"
        or probe_fail_count > 0
    )
    repair_next = _safe_enum(
        repair_pack_artifact.get("next_recommended_slice"),
        allowed_values=_ALLOWED_NEXT_SLICES,
        fallback="",
    )

    alignment_blockers: list[str] = []
    alignment_blockers.extend(
        websearch_live_report_handoff_blockers(
            live_diagnostic_report=live_diagnostic_report,
            preflight_artifact=preflight_artifact,
            seam_status=seam_status,
            contract_failure_detected=contract_failure_detected,
        )
    )
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
        selected_next_step = (
            repair_next or "tighten_websearch_manager_contract_prompt_or_transport"
        )
        handoff_ready = True
    elif seam_status == "candidate_boundary_blocked":
        status = "return_to_websearch_packet_boundary"
        selected_next_step = "narrow_websearch_packet_boundary_or_prompt_probe"
        handoff_ready = False
    elif seam_status == "live_diagnostic_pass":
        status = "websearch_contract_unblocked"
        selected_next_step = "websearch_candidate_pipeline_narrow_expansion"
        handoff_ready = False
    else:
        status = "insufficient_contract_handoff_evidence"
        selected_next_step = "inspect_websearch_live_failure_taxonomy"
        handoff_ready = False

    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_handoff_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_handoff_only",
        "claim_scope": "websearch_live_contract_handoff_to_manager_owner",
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
            "probe_fail_count": probe_fail_count,
            "repair_case_count": repair_case_count,
            "aggregate_missing_required_fields": _safe_count_map(
                probe_summary.get("aggregate_missing_required_fields")
            ),
            "alias_hint_counts": _safe_count_map(repair_summary.get("alias_hint_counts")),
            "shape_pattern_counts": _safe_count_map(repair_summary.get("shape_pattern_counts")),
            "alignment_blocker_count": len(alignment_blockers),
        },
        "alignment_blockers": alignment_blockers,
        "artifact_chain": {
            "live_diagnostic_report": {
                "seam_status": seam_status,
                "source_live_provider_used": live_diagnostic_report.get("source_live_provider_used") is True,
                "source_live_websearch_used": live_diagnostic_report.get("source_live_websearch_used") is True,
                "next_recommended_slice": _safe_enum(
                    live_diagnostic_report.get("next_recommended_slice"),
                    allowed_values=_ALLOWED_NEXT_SLICES,
                    fallback=None,
                ),
            },
            "contract_probe": {
                "contract_failure_detected": contract_failure_detected,
                "next_recommended_slice": _safe_enum(
                    probe_summary.get("next_recommended_slice"),
                    allowed_values=_ALLOWED_NEXT_SLICES,
                    fallback=None,
                ),
            },
            "repair_pack": {
                "next_recommended_slice": repair_next,
            },
        },
        "non_claims": list(WEBSEARCH_MANAGER_CONTRACT_HANDOFF_NON_CLAIMS),
    }


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


def _safe_count_map(value: Any) -> dict[str, int]:
    if not isinstance(value, dict):
        return {}
    result: dict[str, int] = {}
    for key, count in value.items():
        key_text = str(key or "").strip()
        if key_text not in _ALLOWED_SUMMARY_COUNT_KEYS:
            continue
        if isinstance(count, int):
            result[key_text] = count
    return dict(sorted(result.items()))


def _safe_enum(value: Any, *, allowed_values: set[str], fallback: str | None) -> str | None:
    text = str(value or "").strip()
    if text in allowed_values:
        return text
    return fallback


__all__ = [
    "WEBSEARCH_MANAGER_CONTRACT_HANDOFF_NON_CLAIMS",
    "build_websearch_manager_contract_handoff",
]
