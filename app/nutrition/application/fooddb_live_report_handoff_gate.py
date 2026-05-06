from __future__ import annotations

from typing import Any


def fooddb_live_report_handoff_blockers(
    *,
    live_diagnostic_report: dict[str, Any],
    seam_status: str | None,
    contract_failure_detected: bool,
) -> list[str]:
    blockers: list[str] = []
    if seam_status == "provider_contract_blocked" and not contract_failure_detected:
        blockers.append("live_report_probe_contract_status_mismatch")
    if seam_status == "live_diagnostic_pass" and contract_failure_detected:
        blockers.append("live_pass_with_contract_failure_detected")
    if seam_status != "live_diagnostic_pass":
        return blockers
    if live_diagnostic_report.get("upstream_evidence_required") is not True:
        blockers.append("live_report_upstream_evidence_not_required")
    if live_diagnostic_report.get("upstream_evidence_healthy") is not True:
        blockers.append("live_report_upstream_evidence_not_healthy")
    if (
        live_diagnostic_report.get("source_artifact_type")
        != "accurate_intake_grokfast_fooddb_packet_smoke"
    ):
        blockers.append("live_report_source_artifact_type_mismatch")
    if live_diagnostic_report.get("source_status") != "pass":
        blockers.append("live_report_source_status_not_pass")
    if live_diagnostic_report.get("source_live_provider_used") is not True:
        blockers.append("live_report_missing_live_provider_diagnostic")
    if live_diagnostic_report.get("can_expand_to_websearch_live_diagnostic") is not True:
        blockers.append("live_report_websearch_expansion_not_authorized")
    for key, blocker in (
        ("runtime_truth_changed", "live_report_changed_runtime_truth"),
        ("runtime_mutation_attempted", "live_report_attempted_runtime_mutation"),
        ("readiness_claimed", "live_report_claimed_readiness"),
    ):
        if live_diagnostic_report.get(key) is not False:
            blockers.append(blocker)
    return blockers


__all__ = ["fooddb_live_report_handoff_blockers"]
