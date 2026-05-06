from __future__ import annotations

from typing import Any


def websearch_live_report_handoff_blockers(
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
    if live_diagnostic_report.get("preflight_evidence_healthy") is not True:
        blockers.append("live_report_preflight_evidence_not_healthy")
    if (
        live_diagnostic_report.get("source_artifact_type")
        != "accurate_intake_grokfast_websearch_packet_smoke"
    ):
        blockers.append("live_report_source_artifact_type_mismatch")
    if live_diagnostic_report.get("source_status") != "pass":
        blockers.append("live_report_source_status_not_pass")
    if live_diagnostic_report.get("preflight_evidence_required") is not True:
        blockers.append("live_report_preflight_evidence_not_required")
    if live_diagnostic_report.get("can_expand_websearch_candidate_pipeline") is not True:
        blockers.append("live_report_candidate_expansion_not_authorized")
    if live_diagnostic_report.get("source_live_provider_used") is not True:
        blockers.append("live_report_missing_live_provider_diagnostic")
    preflight_evidence = live_diagnostic_report.get("preflight_evidence")
    if not isinstance(preflight_evidence, dict):
        blockers.append("live_report_preflight_evidence_missing")
    else:
        if preflight_evidence.get("preflight_artifact_digest_verified") is not True:
            blockers.append("live_report_preflight_digest_not_verified")
        if preflight_evidence.get("preflight_artifact_integrity_clear") is not True:
            blockers.append("live_report_preflight_integrity_not_clear")
        if preflight_evidence.get("ready_for_runtime_truth") is not False:
            blockers.append("live_report_preflight_allowed_runtime_truth")
    for key, blocker in (
        ("source_live_websearch_used", "live_report_used_live_websearch"),
        ("runtime_truth_changed", "live_report_changed_runtime_truth"),
        ("runtime_mutation_attempted", "live_report_attempted_runtime_mutation"),
        ("readiness_claimed", "live_report_claimed_readiness"),
    ):
        if live_diagnostic_report.get(key) is not False:
            blockers.append(blocker)
    return blockers


__all__ = ["websearch_live_report_handoff_blockers"]
