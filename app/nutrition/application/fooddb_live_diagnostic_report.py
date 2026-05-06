from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


FOODDB_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS = [
    "no_live_provider_call",
    "no_live_websearch_call",
    "no_kimi_call",
    "no_runtime_mutation",
    "no_fooddb_truth_promotion",
    "no_websearch_runtime_truth",
    "no_readiness_claim",
]

_PROVIDER_CONTRACT_FAILURES = frozenset(
    {
        "manager_output_contract_violation",
        "provider_response_error",
    }
)

_PACKET_BOUNDARY_FAILURES = frozenset(
    {
        "invented_evidence_reference",
        "fooddb_packet_not_used",
        "manager_did_not_finalize_after_packet",
        "bare_basket_estimated_without_components",
        "bare_basket_called_tools",
        "bare_basket_missing_followup",
        "bare_basket_mutation_intent",
        "generic_meal_overclaimed_exact",
        "modifier_adjusted_kcal_without_packet_adjustment",
        "unsupported_modifier_adjusted_kcal_range",
    }
)


def build_fooddb_live_diagnostic_report(*, diagnostic_artifact: dict[str, Any]) -> dict[str, Any]:
    source_artifact_type = str(diagnostic_artifact.get("artifact_type") or "")
    if source_artifact_type != "accurate_intake_grokfast_fooddb_packet_smoke":
        raise ValueError(f"unsupported_fooddb_live_diagnostic_artifact_type:{source_artifact_type}")

    failure_counts = _failure_counts(diagnostic_artifact)
    live_provider_used = diagnostic_artifact.get("live_provider_used") is True
    diagnostic_status = str(diagnostic_artifact.get("status") or "")
    provider_contract_blocked = any(failure in failure_counts for failure in _PROVIDER_CONTRACT_FAILURES)
    packet_boundary_blocked = any(failure in failure_counts for failure in _PACKET_BOUNDARY_FAILURES)

    if not live_provider_used:
        seam_status = "fixture_only_live_not_checked"
        next_recommended_slice = "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    elif diagnostic_status == "pass":
        seam_status = "live_diagnostic_pass"
        next_recommended_slice = "grokfast_websearch_packet_live_diagnostic"
    elif provider_contract_blocked:
        seam_status = "provider_contract_blocked"
        next_recommended_slice = "narrow_grokfast_fooddb_manager_contract_probe"
    elif packet_boundary_blocked:
        seam_status = "packet_boundary_blocked"
        next_recommended_slice = "narrow_fooddb_packet_boundary_or_prompt_probe"
    else:
        seam_status = "diagnostic_fail_unclassified"
        next_recommended_slice = "inspect_fooddb_live_failure_taxonomy"

    return {
        "artifact_type": "accurate_intake_fooddb_live_diagnostic_report",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_report_only",
        "claim_scope": "fooddb_manager_packet_live_activation_readiness",
        "source_artifact_type": source_artifact_type,
        "source_status": diagnostic_status,
        "source_live_provider_used": live_provider_used,
        "seam_status": seam_status,
        "can_expand_to_websearch_live_diagnostic": seam_status == "live_diagnostic_pass",
        "should_run_websearch_live_tool_loop": False,
        "provider_contract_blocked": provider_contract_blocked,
        "packet_boundary_blocked": packet_boundary_blocked,
        "next_recommended_slice": next_recommended_slice,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "self_use_approved": False,
        "production_selected": False,
        "failure_matrix": {
            "case_count": _summary_int(diagnostic_artifact, "case_count"),
            "pass_count": _summary_int(diagnostic_artifact, "pass_count"),
            "fail_count": _summary_int(diagnostic_artifact, "fail_count"),
            "failure_counts": failure_counts,
        },
        "sanitization": {
            "raw_manager_output_included": False,
            "raw_provider_trace_included": False,
            "raw_response_excerpt_included": False,
            "raw_packet_payload_included": False,
        },
        "non_claims": [
            claim
            for claim in FOODDB_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS
            if claim != "no_live_provider_call" or not live_provider_used
        ],
    }


def _failure_counts(diagnostic_artifact: dict[str, Any]) -> dict[str, int]:
    counts: dict[str, int] = {}
    summary = diagnostic_artifact.get("summary")
    if isinstance(summary, dict):
        for family in summary.get("failure_families") or []:
            family_text = str(family or "").strip()
            if family_text:
                counts[family_text] = counts.get(family_text, 0) + 1
    for case in diagnostic_artifact.get("cases") or []:
        if not isinstance(case, dict):
            continue
        for family in case.get("failure_families") or []:
            family_text = str(family or "").strip()
            if family_text:
                counts[family_text] = counts.get(family_text, 0) + 1
        provider_trace = case.get("provider_trace")
        if isinstance(provider_trace, dict):
            failure_family = str(provider_trace.get("failure_family") or "").strip()
            if failure_family:
                counts[failure_family] = counts.get(failure_family, 0) + 1
            trace = provider_trace.get("trace")
            if isinstance(trace, dict):
                trace_failure = str(trace.get("failure_family") or "").strip()
                if trace_failure:
                    counts[trace_failure] = counts.get(trace_failure, 0) + 1
    return dict(sorted(counts.items()))


def _summary_int(diagnostic_artifact: dict[str, Any], key: str) -> int:
    summary = diagnostic_artifact.get("summary")
    if not isinstance(summary, dict):
        return 0
    value = summary.get(key)
    return value if isinstance(value, int) else 0


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "FOODDB_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS",
    "build_fooddb_live_diagnostic_report",
]
