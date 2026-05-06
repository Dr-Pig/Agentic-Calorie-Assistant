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
    contract_transport = _contract_transport_summary(diagnostic_artifact)
    preflight_evidence = _preflight_evidence_summary(diagnostic_artifact)
    preflight_healthy = _preflight_evidence_healthy(preflight_evidence)
    provider_contract_blocked = _provider_contract_blocked(
        diagnostic_artifact=diagnostic_artifact,
        failure_counts=failure_counts,
        contract_transport_healthy=contract_transport["healthy"],
    )
    candidate_boundary_blocked = any(
        family in failure_counts for family in _CANDIDATE_BOUNDARY_FAILURES
    )
    if live_websearch_used:
        seam_status = "unexpected_live_websearch_used"
        next_recommended_slice = "inspect_unexpected_websearch_live_tool_loop"
    elif not live_provider_used:
        seam_status = "fixture_only_live_not_checked"
        next_recommended_slice = "run_explicit_grokfast_websearch_packet_live_diagnostic"
    elif diagnostic_status == "pass":
        if preflight_healthy:
            seam_status = "live_diagnostic_pass"
            next_recommended_slice = "websearch_candidate_pipeline_narrow_expansion"
        else:
            seam_status = "preflight_evidence_missing"
            next_recommended_slice = "rerun_with_clear_websearch_live_extract_preflight"
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
        "provider_runtime_residual_blocked": (
            "provider_response_error" in failure_counts and not provider_contract_blocked
        ),
        "candidate_boundary_blocked": candidate_boundary_blocked,
        "preflight_evidence_required": live_provider_used,
        "preflight_evidence_healthy": preflight_healthy,
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
        "contract_transport": contract_transport,
        "preflight_evidence": preflight_evidence,
        "sanitization": {
            "raw_manager_output_included": False,
            "raw_provider_trace_included": False,
            "raw_response_excerpt_included": False,
            "candidate_payload_included": False,
        },
        "non_claims": list(WEBSEARCH_LIVE_DIAGNOSTIC_REPORT_NON_CLAIMS),
    }


def _preflight_evidence_summary(diagnostic_artifact: dict[str, Any]) -> dict[str, Any]:
    preflight = diagnostic_artifact.get("preflight_ref")
    if not isinstance(preflight, dict):
        return {
            "present": False,
            "preflight_ref_source": "missing",
            "artifact_type": "missing_preflight_ref",
            "status": "missing",
            "ready_for_live_extract_diagnostic": False,
            "ready_for_runtime_truth": False,
            "review_packet_authorized": False,
            "review_packet_count": 0,
            "case_matrix_fixed_required_cases": False,
            "case_matrix_case_count": 0,
            "case_matrix_negative_case_count": 0,
            "case_matrix_modifier_guard_cases": 0,
            "case_matrix_live_provider_invoked": True,
            "case_matrix_websearch_invoked": True,
        }
    return {
        "present": True,
        "preflight_ref_source": _safe_preflight_ref_source(preflight.get("preflight_ref_source")),
        "artifact_type": _safe_preflight_artifact_type(preflight.get("artifact_type")),
        "status": "pass" if preflight.get("status") == "pass" else "blocked",
        "ready_for_live_extract_diagnostic": preflight.get("ready_for_live_extract_diagnostic") is True,
        "ready_for_runtime_truth": preflight.get("ready_for_runtime_truth") is True,
        "review_packet_authorized": preflight.get("review_packet_authorized") is True,
        "review_packet_count": _safe_non_negative_int(preflight.get("review_packet_count")),
        "case_matrix_fixed_required_cases": preflight.get("case_matrix_fixed_required_cases") is True,
        "case_matrix_case_count": _safe_non_negative_int(preflight.get("case_matrix_case_count")),
        "case_matrix_negative_case_count": _safe_non_negative_int(
            preflight.get("case_matrix_negative_case_count")
        ),
        "case_matrix_modifier_guard_cases": _safe_non_negative_int(
            preflight.get("case_matrix_modifier_guard_cases")
        ),
        "case_matrix_live_provider_invoked": preflight.get("case_matrix_live_provider_invoked") is not False,
        "case_matrix_websearch_invoked": preflight.get("case_matrix_websearch_invoked") is not False,
    }


def _preflight_evidence_healthy(preflight: dict[str, Any]) -> bool:
    return (
        preflight.get("present") is True
        and preflight.get("preflight_ref_source")
        == "run_accurate_intake_grokfast_websearch_packet_smoke"
        and preflight.get("artifact_type") == "accurate_intake_websearch_live_extract_preflight_v1"
        and preflight.get("status") == "pass"
        and preflight.get("ready_for_live_extract_diagnostic") is True
        and preflight.get("ready_for_runtime_truth") is False
        and preflight.get("review_packet_authorized") is True
        and preflight.get("review_packet_count") >= 1
        and preflight.get("case_matrix_fixed_required_cases") is True
        and preflight.get("case_matrix_case_count") == 6
        and preflight.get("case_matrix_negative_case_count") == 4
        and preflight.get("case_matrix_modifier_guard_cases") == 1
        and preflight.get("case_matrix_live_provider_invoked") is False
        and preflight.get("case_matrix_websearch_invoked") is False
    )


def _safe_preflight_ref_source(value: Any) -> str:
    if str(value or "") == "run_accurate_intake_grokfast_websearch_packet_smoke":
        return "run_accurate_intake_grokfast_websearch_packet_smoke"
    return "unsupported_preflight_ref_source"


def _safe_preflight_artifact_type(value: Any) -> str:
    if str(value or "") == "accurate_intake_websearch_live_extract_preflight_v1":
        return "accurate_intake_websearch_live_extract_preflight_v1"
    return "unsupported_preflight_artifact"


def _safe_non_negative_int(value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        return 0
    return max(0, value)


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


def _provider_contract_blocked(
    *,
    diagnostic_artifact: dict[str, Any],
    failure_counts: dict[str, int],
    contract_transport_healthy: bool,
) -> bool:
    if "manager_output_contract_violation" in failure_counts:
        return True
    if "provider_response_error" not in failure_counts:
        return False
    return not contract_transport_healthy or _provider_trace_reports_contract_failure(diagnostic_artifact)


def _provider_trace_reports_contract_failure(diagnostic_artifact: dict[str, Any]) -> bool:
    for case in diagnostic_artifact.get("cases") or []:
        if not isinstance(case, dict):
            continue
        provider_trace = case.get("provider_trace")
        if not isinstance(provider_trace, dict):
            continue
        for summary in _provider_trace_contract_views(provider_trace):
            failure_family = str(summary.get("failure_family") or "").strip()
            request_failure_family = str(summary.get("request_failure_family") or "").strip()
            failing_component = str(summary.get("failing_component") or "").strip()
            if failure_family == "manager_output_contract_violation":
                return True
            if request_failure_family == "manager_output_contract_violation":
                return True
            if "validate_manager_payload" in failing_component:
                return True
            if summary.get("decision_transport_contract_breach") is True:
                return True
    return False


def _contract_transport_summary(diagnostic_artifact: dict[str, Any]) -> dict[str, Any]:
    observed_modes: set[str] = set()
    observed_structured_modes: set[str] = set()
    schema_names: set[str] = set()
    schema_versions: set[str] = set()
    decision_transport_attempted = False
    structured_output_attempted = False
    contract_breach_observed = False
    healthy_case_count = 0
    structured_output_healthy_case_count = 0
    for case in diagnostic_artifact.get("cases") or []:
        if not isinstance(case, dict):
            continue
        provider_trace = case.get("provider_trace")
        if not isinstance(provider_trace, dict):
            continue
        for summary in _provider_trace_contract_views(provider_trace):
            mode = str(summary.get("decision_transport_mode") or "").strip()
            if mode:
                observed_modes.add(mode)
            structured_mode = str(summary.get("structured_output_transport_mode") or "").strip()
            if structured_mode:
                observed_structured_modes.add(structured_mode)
            schema_name = str(
                summary.get("schema_name")
                or summary.get("decision_transport_schema_name")
                or ""
            ).strip()
            if schema_name:
                schema_names.add(schema_name)
            schema_version = str(
                summary.get("schema_version")
                or summary.get("decision_transport_schema_version")
                or ""
            ).strip()
            if schema_version:
                schema_versions.add(schema_version)
            if summary.get("decision_transport_attempted") is True:
                decision_transport_attempted = True
            if summary.get("structured_output_transport_attempted") is True:
                structured_output_attempted = True
            if summary.get("decision_transport_contract_breach") is True:
                contract_breach_observed = True
            if (
                mode == "synthetic_tool_transport"
                and schema_name == "founder_live_manager_contract"
                and summary.get("decision_transport_contract_breach") is False
            ):
                healthy_case_count += 1
            if (
                structured_mode == "json_schema"
                and schema_name == "phase_b1_pass2_manager_contract"
                and summary.get("structured_output_transport_accepted") is True
                and summary.get("decision_transport_contract_breach") is not True
            ):
                structured_output_healthy_case_count += 1
    return {
        "decision_transport_attempted": decision_transport_attempted,
        "structured_output_transport_attempted": structured_output_attempted,
        "observed_decision_transport_modes": sorted(observed_modes),
        "observed_structured_output_transport_modes": sorted(observed_structured_modes),
        "observed_schema_names": sorted(schema_names),
        "observed_schema_versions": sorted(schema_versions),
        "contract_breach_observed": contract_breach_observed,
        "healthy_case_count": healthy_case_count,
        "structured_output_healthy_case_count": structured_output_healthy_case_count,
        "healthy": (
            healthy_case_count + structured_output_healthy_case_count > 0
            and not contract_breach_observed
        ),
    }


def _provider_trace_contract_views(provider_trace: dict[str, Any]) -> list[dict[str, Any]]:
    views: list[dict[str, Any]] = []
    trace_summary = provider_trace.get("trace_summary")
    if isinstance(trace_summary, dict):
        views.append(trace_summary)
    views.append(provider_trace)
    return views


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
