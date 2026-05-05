from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from app.nutrition.application.grokfast_fooddb_packet_smoke import build_live_manager_payload


ResponseSchemaForConstraints = Callable[[dict[str, Any]], dict[str, Any] | None]


GROKFAST_FOODDB_CONTRACT_PROBE_NON_CLAIMS = [
    "no_live_provider_call",
    "no_runtime_mutation",
    "no_fooddb_truth_promotion",
    "no_websearch_runtime_truth",
    "no_readiness_claim",
]


def build_grokfast_fooddb_contract_probe(
    *,
    packet_artifact: dict[str, Any],
    response_schema_for_constraints: ResponseSchemaForConstraints,
    diagnostic_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    cases = [
        _case_probe(
            packet_case=packet_case,
            response_schema_for_constraints=response_schema_for_constraints,
            diagnostic_case=_diagnostic_case(diagnostic_artifact, packet_case),
        )
        for packet_case in packet_artifact.get("cases") or []
        if isinstance(packet_case, dict)
    ]
    issue_counts = _issue_counts(cases)
    status = "contract_drift_detected" if issue_counts else "pass"
    return {
        "artifact_type": "accurate_intake_grokfast_fooddb_contract_probe",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_only",
        "claim_scope": "grokfast_fooddb_packet_schema_contract_drift_probe",
        "status": status,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "source_packet_artifact_type": packet_artifact.get("artifact_type"),
        "source_diagnostic_artifact_type": (diagnostic_artifact or {}).get("artifact_type"),
        "source_live_provider_used": (diagnostic_artifact or {}).get("live_provider_used") is True,
        "summary": {
            "case_count": len(cases),
            "drift_case_count": sum(1 for case in cases if case.get("issues")),
            "issue_counts": issue_counts,
        },
        "cases": cases,
        "next_recommended_slice": (
            "narrow_grokfast_fooddb_profile_schema"
            if issue_counts
            else "rerun_grokfast_fooddb_packet_live_diagnostic"
        ),
        "non_claims": list(GROKFAST_FOODDB_CONTRACT_PROBE_NON_CLAIMS),
    }


def _case_probe(
    *,
    packet_case: dict[str, Any],
    response_schema_for_constraints: ResponseSchemaForConstraints,
    diagnostic_case: dict[str, Any] | None,
) -> dict[str, Any]:
    live_payload = build_live_manager_payload(packet_case=packet_case)
    strict_contract = live_payload.get("expected_output_contract") or {}
    constraints = live_payload.get("constraints") if isinstance(live_payload.get("constraints"), dict) else {}
    schema = response_schema_for_constraints(constraints) or {}
    schema_properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    schema_required = set(schema.get("required") or [])
    strict_case_contract = strict_contract.get("case_level_contract")
    if not isinstance(strict_case_contract, dict):
        strict_case_contract = {}

    schema_allows_top_level_evidence_used = "evidence_used" in schema_properties
    strict_allows_top_level_evidence_used = (
        strict_contract.get("top_level_evidence_used_allowed") is True
    )
    strict_requires_top_level_item_results = (
        strict_case_contract.get("top_level_item_results_required") is True
    )
    schema_requires_top_level_item_results = "item_results" in schema_required
    provider_output = (diagnostic_case or {}).get("manager_output")
    if not isinstance(provider_output, dict):
        provider_output = {}
    provider_emitted_top_level_evidence_used = "evidence_used" in provider_output
    provider_put_item_results_in_answer_contract = isinstance(
        (provider_output.get("answer_contract") or {}),
        dict,
    ) and "item_results" in (provider_output.get("answer_contract") or {})

    issues: list[str] = []
    if schema_allows_top_level_evidence_used and not strict_allows_top_level_evidence_used:
        issues.append("schema_allows_forbidden_top_level_evidence_used")
    if strict_requires_top_level_item_results and not schema_requires_top_level_item_results:
        issues.append("schema_does_not_require_strict_top_level_item_results")
    if provider_emitted_top_level_evidence_used and not strict_allows_top_level_evidence_used:
        issues.append("provider_emitted_forbidden_top_level_evidence_used")
    if provider_put_item_results_in_answer_contract:
        issues.append("provider_put_item_results_in_answer_contract")

    return {
        "case_id": packet_case.get("case_id"),
        "case_family": constraints.get("phase_b1_case_family"),
        "strict_contract": {
            "top_level_evidence_used_allowed": strict_allows_top_level_evidence_used,
            "top_level_item_results_required": strict_requires_top_level_item_results,
            "answer_contract_item_results_allowed": strict_contract.get(
                "answer_contract_item_results_allowed"
            )
            is True,
            "answer_contract_evidence_used_allowed": strict_contract.get(
                "answer_contract_evidence_used_allowed"
            )
            is True,
        },
        "provider_schema": {
            "top_level_evidence_used_allowed": schema_allows_top_level_evidence_used,
            "top_level_item_results_required": schema_requires_top_level_item_results,
        },
        "observed_live_output": {
            "available": bool(provider_output),
            "top_level_evidence_used_present": provider_emitted_top_level_evidence_used,
            "answer_contract_item_results_present": provider_put_item_results_in_answer_contract,
        },
        "issues": sorted(set(issues)),
    }


def _diagnostic_case(
    diagnostic_artifact: dict[str, Any] | None,
    packet_case: dict[str, Any],
) -> dict[str, Any] | None:
    if not isinstance(diagnostic_artifact, dict):
        return None
    case_id = str(packet_case.get("case_id") or "")
    for case in diagnostic_artifact.get("cases") or []:
        if isinstance(case, dict) and str(case.get("case_id") or "") == case_id:
            return case
    return None


def _issue_counts(cases: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for case in cases:
        for issue in case.get("issues") or []:
            issue_text = str(issue or "").strip()
            if issue_text:
                counts[issue_text] = counts.get(issue_text, 0) + 1
    return dict(sorted(counts.items()))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "GROKFAST_FOODDB_CONTRACT_PROBE_NON_CLAIMS",
    "ResponseSchemaForConstraints",
    "build_grokfast_fooddb_contract_probe",
]
