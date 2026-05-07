from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_EXPECTED_REPORT = "accurate_intake_websearch_live_diagnostic_report"
_EXPECTED_HANDOFF = "accurate_intake_websearch_manager_contract_handoff_v1"
_EXPECTED_STATUS_INSPECTION = "accurate_intake_websearch_status_packet_inspection_v1"
_REPORT_OVERRIDE_SLICES = {
    "run_explicit_grokfast_websearch_packet_live_diagnostic": "live_activation_ordering",
    "rerun_with_clear_websearch_live_extract_preflight": "upstream_evidence_chain",
}
_HANDOFF_OVERRIDE_SLICES = {
    "narrow_grokfast_websearch_manager_contract_probe": "manager_contract_owner",
    "narrow_prompt_schema_intent_alias_probe": "manager_contract_owner",
    "tighten_websearch_manager_contract_prompt_or_transport": "manager_contract_owner",
    "repair_artifact_alignment_required": "artifact_alignment",
    "narrow_websearch_packet_boundary_or_prompt_probe": "packet_boundary_owner",
}
_CANDIDATE_BOUNDARY_FAMILIES = frozenset(
    {
        "invented_websearch_evidence_reference",
        "websearch_ambiguous_candidate_missing_followup",
        "websearch_candidate_created_item_results",
        "websearch_candidate_mutated_runtime",
        "websearch_candidate_not_used",
        "websearch_truth_shortcut",
        "websearch_truth_surface_leak",
        "websearch_weak_candidate_not_rejected",
    }
)

def build_websearch_live_failure_taxonomy_inspection(
    *,
    live_diagnostic_report: dict[str, Any],
    manager_contract_handoff_artifact: dict[str, Any] | None = None,
    status_packet_inspection_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    blockers = _report_blockers(live_diagnostic_report)
    blockers.extend(
        _artifact_blockers(
            manager_contract_handoff_artifact,
            expected_type=_EXPECTED_HANDOFF,
            mutation_key="runtime_mutation_attempted",
            prefix="manager_contract_handoff",
        )
    )
    blockers.extend(
        _artifact_blockers(
            status_packet_inspection_artifact,
            expected_type=_EXPECTED_STATUS_INSPECTION,
            mutation_key="mutation_changed",
            prefix="status_packet_inspection",
        )
    )
    failure_counts = _failure_counts(live_diagnostic_report)
    dominant_lane, next_safe_slice = _next_safe_slice(
        live_diagnostic_report=live_diagnostic_report,
        failure_counts=failure_counts,
        manager_contract_handoff_artifact=manager_contract_handoff_artifact,
        status_packet_inspection_artifact=status_packet_inspection_artifact,
    )
    return {
        "artifact_type": "accurate_intake_websearch_live_failure_taxonomy_inspection_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "deterministic_websearch_live_failure_taxonomy_inspection_only",
        "claim_scope": "websearch_live_failure_lane_selection_without_runtime_truth",
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "seam_status": str(live_diagnostic_report.get("seam_status") or "unknown"),
            "report_next_recommended_slice": str(
                live_diagnostic_report.get("next_recommended_slice") or ""
            ),
            "handoff_status": _handoff_status(manager_contract_handoff_artifact),
            "handoff_selected_next_step": _handoff_selected_next_step(
                manager_contract_handoff_artifact
            ),
            "status_packet_next_safe_slice": _status_packet_next_safe_slice(
                status_packet_inspection_artifact
            ),
            "candidate_boundary_failure_count": _sum_counts(
                failure_counts, _CANDIDATE_BOUNDARY_FAMILIES
            ),
            "unclassified_failure_count": _sum_counts(
                failure_counts, set(failure_counts) - _CANDIDATE_BOUNDARY_FAMILIES
            ),
            "dominant_failure_lane": dominant_lane,
            "next_safe_slice": next_safe_slice,
        },
        "source_refs": {
            "live_diagnostic_report_type": live_diagnostic_report.get("artifact_type"),
            "manager_contract_handoff_type": None
            if manager_contract_handoff_artifact is None
            else manager_contract_handoff_artifact.get("artifact_type"),
            "status_packet_inspection_type": None
            if status_packet_inspection_artifact is None
            else status_packet_inspection_artifact.get("artifact_type"),
        },
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }

def _report_blockers(report: dict[str, Any]) -> list[str]:
    if str(report.get("artifact_type") or "") != _EXPECTED_REPORT:
        return ["unsupported_websearch_live_diagnostic_report"]
    blockers: list[str] = []
    if report.get("runtime_truth_changed") is not False:
        blockers.append("websearch_live_diagnostic_report_changed_runtime_truth")
    if report.get("runtime_mutation_attempted") is not False:
        blockers.append("websearch_live_diagnostic_report_changed_runtime_mutation")
    if report.get("readiness_claimed") is not False:
        blockers.append("websearch_live_diagnostic_report_claimed_readiness")
    return blockers

def _artifact_blockers(
    artifact: dict[str, Any] | None,
    *,
    expected_type: str,
    mutation_key: str,
    prefix: str,
) -> list[str]:
    if artifact is None:
        return []
    if str(artifact.get("artifact_type") or "") != expected_type:
        return [f"unsupported_{prefix}_artifact"]
    blockers: list[str] = []
    if artifact.get("runtime_truth_changed") is not False:
        blockers.append(f"{prefix}_changed_runtime_truth")
    if artifact.get(mutation_key) is not False:
        blockers.append(f"{prefix}_changed_runtime_mutation")
    if "shared_contract_changed" in artifact and artifact.get("shared_contract_changed") is not False:
        blockers.append(f"{prefix}_changed_shared_contract")
    if "manager_context_changed" in artifact and artifact.get("manager_context_changed") is not False:
        blockers.append(f"{prefix}_changed_manager_context")
    if "readiness_claimed" in artifact and artifact.get("readiness_claimed") is not False:
        blockers.append(f"{prefix}_claimed_readiness")
    return blockers

def _next_safe_slice(
    *,
    live_diagnostic_report: dict[str, Any],
    failure_counts: dict[str, int],
    manager_contract_handoff_artifact: dict[str, Any] | None,
    status_packet_inspection_artifact: dict[str, Any] | None,
) -> tuple[str, str]:
    handoff_next = _handoff_selected_next_step(manager_contract_handoff_artifact)
    if handoff_next in _HANDOFF_OVERRIDE_SLICES:
        return _HANDOFF_OVERRIDE_SLICES[handoff_next], handoff_next
    report_next = str(live_diagnostic_report.get("next_recommended_slice") or "").strip()
    if report_next in _REPORT_OVERRIDE_SLICES:
        return _REPORT_OVERRIDE_SLICES[report_next], report_next
    seam_status = str(live_diagnostic_report.get("seam_status") or "").strip()
    if seam_status == "candidate_boundary_blocked" or _sum_counts(
        failure_counts, _CANDIDATE_BOUNDARY_FAMILIES
    ):
        return "packet_boundary_owner", "narrow_websearch_packet_boundary_or_prompt_probe"
    if (
        seam_status == "live_diagnostic_pass"
        and _handoff_status(manager_contract_handoff_artifact) == "websearch_contract_unblocked"
        and _status_packet_next_safe_slice(status_packet_inspection_artifact)
        == "inspect_websearch_status_packet"
    ):
        return "no_runtime_integration_wall", "inspect_fooddb_websearch_no_runtime_wall"
    if seam_status == "live_diagnostic_pass":
        next_slice = _status_packet_next_safe_slice(status_packet_inspection_artifact)
        return "status_packet_followup", next_slice or "inspect_websearch_status_packet"
    next_slice = _status_packet_next_safe_slice(status_packet_inspection_artifact)
    return "failure_taxonomy_followup", next_slice or "inspect_websearch_live_failure_taxonomy"

def _failure_counts(report: dict[str, Any]) -> dict[str, int]:
    matrix = report.get("failure_matrix")
    counts = matrix.get("failure_counts") if isinstance(matrix, dict) else {}
    if not isinstance(counts, dict):
        return {}
    result: dict[str, int] = {}
    for key, value in counts.items():
        if isinstance(value, int) and value > 0:
            result[str(key)] = value
    return dict(sorted(result.items()))

def _sum_counts(counts: dict[str, int], families: set[str] | frozenset[str]) -> int:
    return sum(count for family, count in counts.items() if family in families)

def _handoff_status(artifact: dict[str, Any] | None) -> str:
    return "" if not isinstance(artifact, dict) else str(artifact.get("status") or "").strip()

def _handoff_selected_next_step(artifact: dict[str, Any] | None) -> str:
    return "" if not isinstance(artifact, dict) else str(artifact.get("selected_next_step") or "").strip()

def _status_packet_next_safe_slice(artifact: dict[str, Any] | None) -> str:
    if not isinstance(artifact, dict):
        return ""
    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        return ""
    return str(summary.get("next_safe_slice") or "").strip()

__all__ = ["build_websearch_live_failure_taxonomy_inspection"]
