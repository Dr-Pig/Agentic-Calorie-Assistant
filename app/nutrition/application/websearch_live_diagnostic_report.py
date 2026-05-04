from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


WEBSEARCH_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS = [
    "no_live_provider_call",
    "no_live_websearch_call",
    "no_kimi_call",
    "no_runtime_mutation",
    "no_websearch_runtime_truth",
    "no_fooddb_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_readiness_claim",
]

_PROVIDER_CONTRACT_FAILURES = frozenset(
    {
        "manager_output_contract_violation",
        "provider_response_error",
    }
)
_CANDIDATE_BOUNDARY_FAILURES = frozenset(
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


def build_websearch_live_diagnostic_report(
    *,
    diagnostic_artifact: dict[str, Any],
) -> dict[str, Any]:
    source_artifact_type = str(diagnostic_artifact.get("artifact_type") or "")
    if source_artifact_type != "accurate_intake_grokfast_websearch_packet_smoke":
        raise ValueError(f"unsupported_websearch_live_diagnostic_artifact_type:{source_artifact_type}")
    failure_counts = _failure_counts(diagnostic_artifact)
    live_provider_used = diagnostic_artifact.get("live_provider_used") is True
    live_websearch_used = diagnostic_artifact.get("live_websearch_used") is True
    diagnostic_status = str(diagnostic_artifact.get("status") or "")
    provider_contract_blocked = any(
        family in failure_counts for family in _PROVIDER_CONTRACT_FAILURES
    )
    candidate_boundary_blocked = any(
        family in failure_counts for family in _CANDIDATE_BOUNDARY_FAILURES
    )
    if not live_provider_used:
        seam_status = "fixture_only_live_not_checked"
        next_recommended_slice = "run_explicit_grokfast_websearch_packet_live_diagnostic"
    elif diagnostic_status == "pass":
        seam_status = "live_diagnostic_pass"
        next_recommended_slice = "websearch_candidate_pipeline_narrow_expansion"
    elif provider_contract_blocked:
        seam_status = "provider_contract_blocked"
        next_recommended_slice = "narrow_grokfast_websearch_manager_contract_probe"
    elif candidate_boundary_blocked:
        seam_status = "candidate_boundary_blocked"
        next_recommended_slice = "narrow_websearch_packet_boundary_or_prompt_probe"
    else:
        seam_status = "diagnostic_fail_unclassified"
        next_recommended_slice = "inspect_sanitized_failure_taxonomy"

    can_expand_websearch = seam_status == "live_diagnostic_pass" and not live_websearch_used
    return {
        "artifact_type": "accurate_intake_websearch_live_diagnostic_report",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_report_only",
        "claim_scope": "websearch_manager_packet_live_activation_readiness",
        "source_artifact_type": source_artifact_type,
        "source_status": diagnostic_status,
        "source_live_provider_used": live_provider_used,
        "source_live_websearch_used": live_websearch_used,
        "seam_status": seam_status,
        "can_expand_websearch_candidate_pipeline": can_expand_websearch,
        "should_run_websearch_live_tool_loop": False,
        "provider_contract_blocked": provider_contract_blocked,
        "candidate_boundary_blocked": candidate_boundary_blocked,
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
            "candidate_payload_included": False,
        },
        "non_claims": list(WEBSEARCH_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS),
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
            for family in _provider_trace_failure_families(provider_trace):
                counts[family] = counts.get(family, 0) + 1
    return dict(sorted(counts.items()))


def _provider_trace_failure_families(provider_trace: dict[str, Any]) -> list[str]:
    families: list[str] = []
    for key in ("failure_family", "error_type"):
        family = str(provider_trace.get(key) or "").strip()
        if family:
            families.append(family)
    trace_summary = provider_trace.get("trace_summary")
    if isinstance(trace_summary, dict):
        for key in ("failure_family", "request_failure_family"):
            family = str(trace_summary.get(key) or "").strip()
            if family:
                families.append(family)
    return families


def _summary_int(diagnostic_artifact: dict[str, Any], key: str) -> int:
    summary = diagnostic_artifact.get("summary")
    if not isinstance(summary, dict):
        return 0
    value = summary.get(key)
    return value if isinstance(value, int) else 0


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS",
    "build_websearch_live_diagnostic_report",
]
