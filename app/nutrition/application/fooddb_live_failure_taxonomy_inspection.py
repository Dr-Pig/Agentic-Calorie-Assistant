from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

_EXPECTED_REPORT = "accurate_intake_fooddb_live_diagnostic_report"
_EXPECTED_HANDOFF = "accurate_intake_fooddb_manager_contract_handoff_v1"
_EXPECTED_HANDOFF_INSPECTION = (
    "accurate_intake_fooddb_manager_contract_handoff_inspection_v1"
)
_HANDOFF_OVERRIDE_SLICES = {
    "grokfast_websearch_packet_live_diagnostic": "websearch_ready",
    "narrow_fooddb_packet_boundary_or_prompt_probe": "packet_boundary_owner",
    "repair_artifact_alignment_required": "artifact_alignment",
    "tighten_fooddb_manager_contract_prompt_or_transport": "manager_contract_owner",
}
_REPORT_OVERRIDE_SLICES = {
    "rerun_with_clear_fooddb_live_runner_evidence": "upstream_evidence_chain",
    "run_explicit_grokfast_fooddb_packet_live_diagnostic": "live_activation_ordering",
}
_PROVIDER_CONTRACT_FAMILIES = frozenset(
    {
        "malformed_json",
        "manager_contract_required_fields_missing",
        "manager_contract_schema_validation_failed",
        "manager_output_contract_violation",
        "non_json_model_output",
        "payload_shape_error",
        "provider_response_error",
    }
)
_PACKET_BOUNDARY_FAMILIES = frozenset(
    {
        "bare_basket_called_tools",
        "bare_basket_estimated_without_components",
        "bare_basket_missing_followup",
        "bare_basket_mutation_intent",
        "fooddb_packet_not_used",
        "generic_meal_overclaimed_exact",
        "invented_evidence_reference",
        "invented_text_evidence_reference",
        "manager_did_not_finalize_after_packet",
        "modifier_adjusted_kcal_without_packet_adjustment",
        "packet_pass2_reopened_tool_calls",
        "unsupported_modifier_adjusted_kcal_range",
    }
)
def build_fooddb_live_failure_taxonomy_inspection(
    *,
    live_diagnostic_report: dict[str, Any],
    manager_contract_handoff_artifact: dict[str, Any] | None = None,
    manager_contract_handoff_inspection_artifact: dict[str, Any] | None = None,
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
            manager_contract_handoff_inspection_artifact,
            expected_type=_EXPECTED_HANDOFF_INSPECTION,
            mutation_key="mutation_changed",
            prefix="manager_contract_handoff_inspection",
        )
    )

    failure_counts = _failure_counts(live_diagnostic_report)
    summary = _summary(
        live_diagnostic_report=live_diagnostic_report,
        failure_counts=failure_counts,
        handoff_inspection=manager_contract_handoff_inspection_artifact,
    )
    return {
        "artifact_type": "accurate_intake_fooddb_live_failure_taxonomy_inspection_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "deterministic_fooddb_live_failure_taxonomy_inspection_only",
        "claim_scope": "fooddb_live_failure_lane_selection_without_runtime_truth",
        "status": "pass" if not blockers else "blocked",
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "shared_contract_changed": False,
        "manager_context_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": summary,
        "source_refs": {
            "live_diagnostic_report_type": live_diagnostic_report.get("artifact_type"),
            "manager_contract_handoff_type": None
            if manager_contract_handoff_artifact is None
            else manager_contract_handoff_artifact.get("artifact_type"),
            "manager_contract_handoff_inspection_type": None
            if manager_contract_handoff_inspection_artifact is None
            else manager_contract_handoff_inspection_artifact.get("artifact_type"),
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
        return ["unsupported_fooddb_live_diagnostic_report"]
    blockers: list[str] = []
    if report.get("runtime_truth_changed") is not False:
        blockers.append("fooddb_live_diagnostic_report_changed_runtime_truth")
    if report.get("runtime_mutation_attempted") is not False:
        blockers.append("fooddb_live_diagnostic_report_changed_runtime_mutation")
    if report.get("readiness_claimed") is not False:
        blockers.append("fooddb_live_diagnostic_report_claimed_readiness")
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
def _summary(
    *,
    live_diagnostic_report: dict[str, Any],
    failure_counts: dict[str, int],
    handoff_inspection: dict[str, Any] | None,
) -> dict[str, Any]:
    dominant_lane, next_safe_slice = _next_safe_slice(
        live_diagnostic_report=live_diagnostic_report,
        failure_counts=failure_counts,
        handoff_inspection=handoff_inspection,
    )
    return {
        "seam_status": str(live_diagnostic_report.get("seam_status") or "unknown"),
        "source_live_provider_used": live_diagnostic_report.get("source_live_provider_used") is True,
        "report_next_recommended_slice": str(
            live_diagnostic_report.get("next_recommended_slice") or ""
        ),
        "handoff_inspection_next_safe_slice": _handoff_next_safe_slice(handoff_inspection),
        "provider_contract_failure_count": _sum_counts(failure_counts, _PROVIDER_CONTRACT_FAMILIES),
        "packet_boundary_failure_count": _sum_counts(failure_counts, _PACKET_BOUNDARY_FAMILIES),
        "unclassified_failure_count": _sum_counts(
            failure_counts, set(failure_counts) - _PROVIDER_CONTRACT_FAMILIES - _PACKET_BOUNDARY_FAMILIES
        ),
        "dominant_failure_lane": dominant_lane,
        "next_safe_slice": next_safe_slice,
    }
def _next_safe_slice(
    *,
    live_diagnostic_report: dict[str, Any],
    failure_counts: dict[str, int],
    handoff_inspection: dict[str, Any] | None,
) -> tuple[str, str]:
    handoff_next = _handoff_next_safe_slice(handoff_inspection)
    if handoff_next in _HANDOFF_OVERRIDE_SLICES:
        return _HANDOFF_OVERRIDE_SLICES[handoff_next], handoff_next

    report_next = str(live_diagnostic_report.get("next_recommended_slice") or "").strip()
    if report_next in _REPORT_OVERRIDE_SLICES:
        return _REPORT_OVERRIDE_SLICES[report_next], report_next

    seam_status = str(live_diagnostic_report.get("seam_status") or "").strip()
    if seam_status == "live_diagnostic_pass":
        return "websearch_ready", "grokfast_websearch_packet_live_diagnostic"
    if seam_status == "provider_contract_blocked" or _sum_counts(
        failure_counts, _PROVIDER_CONTRACT_FAMILIES
    ):
        return "manager_contract_owner", "narrow_grokfast_fooddb_manager_contract_probe"
    if seam_status == "packet_boundary_blocked" or _sum_counts(
        failure_counts, _PACKET_BOUNDARY_FAMILIES
    ):
        return "packet_boundary_owner", "narrow_fooddb_packet_boundary_or_prompt_probe"
    return "contract_handoff_followup", "inspect_contract_handoff_status"
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
def _handoff_next_safe_slice(artifact: dict[str, Any] | None) -> str:
    if not isinstance(artifact, dict):
        return ""
    summary = artifact.get("summary")
    if not isinstance(summary, dict):
        return ""
    return str(summary.get("next_safe_slice") or "").strip()
__all__ = ["build_fooddb_live_failure_taxonomy_inspection"]
