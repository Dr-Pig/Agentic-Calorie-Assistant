from __future__ import annotations

from datetime import UTC, datetime
import ast
from typing import Any


def build_fooddb_manager_contract_probe(*, diagnostic_artifact: dict[str, Any]) -> dict[str, Any]:
    source_artifact_type = str(diagnostic_artifact.get("artifact_type") or "")
    if source_artifact_type != "accurate_intake_grokfast_fooddb_packet_smoke":
        raise ValueError(f"unsupported_fooddb_manager_contract_probe_source:{source_artifact_type}")

    cases = []
    aggregate_missing_fields: dict[str, int] = {}
    decision_transport_modes: dict[str, int] = {}
    schema_names: dict[str, int] = {}
    schema_versions: dict[str, int] = {}
    contract_breach_count = 0
    accepted_count = 0
    fallback_reason_counts: dict[str, int] = {}

    for case in diagnostic_artifact.get("cases") or []:
        if not isinstance(case, dict):
            continue
        provider_trace = case.get("provider_trace")
        trace = provider_trace.get("trace") if isinstance(provider_trace, dict) else None
        if not isinstance(trace, dict):
            continue

        missing_fields = _extract_missing_fields_from_trace(trace)
        for field in missing_fields:
            aggregate_missing_fields[field] = aggregate_missing_fields.get(field, 0) + 1

        mode = str(trace.get("decision_transport_mode") or "").strip()
        if mode:
            decision_transport_modes[mode] = decision_transport_modes.get(mode, 0) + 1

        schema_name = str(trace.get("decision_transport_schema_name") or "").strip()
        if schema_name:
            schema_names[schema_name] = schema_names.get(schema_name, 0) + 1

        schema_version = str(trace.get("decision_transport_schema_version") or "").strip()
        if schema_version:
            schema_versions[schema_version] = schema_versions.get(schema_version, 0) + 1

        if trace.get("decision_transport_contract_breach") is True:
            contract_breach_count += 1
        if trace.get("decision_transport_accepted") is True:
            accepted_count += 1

        fallback_reason = str(
            trace.get("decision_transport_fallback_reason")
            or trace.get("fallback_reason")
            or ""
        ).strip()
        if fallback_reason:
            fallback_reason_counts[fallback_reason] = fallback_reason_counts.get(fallback_reason, 0) + 1

        cases.append(
            {
                "case_id": case.get("case_id"),
                "status": case.get("status"),
                "failure_families": list(case.get("failure_families") or []),
                "missing_required_fields": missing_fields,
                "decision_transport_mode": mode or None,
                "decision_transport_schema_name": schema_name or None,
                "decision_transport_schema_version": schema_version or None,
                "decision_transport_contract_breach": trace.get("decision_transport_contract_breach") is True,
                "decision_transport_accepted": trace.get("decision_transport_accepted") is True,
                "fallback_reason": fallback_reason or None,
                "failing_component": str(trace.get("failing_component") or "").strip() or None,
                "effective_response_format_type": str(trace.get("effective_response_format_type") or "").strip() or None,
                "observed_type": str(trace.get("observed_type") or "").strip() or None,
            }
        )

    source_live_provider_used = diagnostic_artifact.get("live_provider_used") is True
    contract_failure_detected = contract_breach_count > 0 or bool(aggregate_missing_fields)
    if not source_live_provider_used:
        next_recommended_slice = "run_explicit_grokfast_fooddb_packet_live_diagnostic"
    elif contract_failure_detected:
        next_recommended_slice = "tighten_fooddb_manager_contract_prompt_or_transport"
    else:
        next_recommended_slice = "narrow_fooddb_packet_boundary_or_prompt_probe"

    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_probe",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_report_only",
        "claim_scope": "fooddb_manager_live_contract_probe",
        "source_artifact_type": source_artifact_type,
        "source_status": diagnostic_artifact.get("status"),
        "source_live_provider_used": source_live_provider_used,
        "contract_failure_detected": contract_failure_detected,
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "production_selected": False,
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": len(cases),
            "contract_breach_count": contract_breach_count,
            "decision_transport_accepted_count": accepted_count,
            "aggregate_missing_required_fields": dict(sorted(aggregate_missing_fields.items())),
            "decision_transport_modes": dict(sorted(decision_transport_modes.items())),
            "schema_names": dict(sorted(schema_names.items())),
            "schema_versions": dict(sorted(schema_versions.items())),
            "fallback_reason_counts": dict(sorted(fallback_reason_counts.items())),
        },
        "cases": cases,
        "non_claims": [
            "no_live_provider_call",
            "no_runtime_truth_promotion",
            "no_mutation_legality_change",
            "no_packetizer_format_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        result = []
        for item in value:
            text = str(item or "").strip()
            if text:
                result.append(text)
        return result
    if isinstance(value, dict):
        result = []
        for key, item in value.items():
            if not item:
                continue
            text = str(key or "").strip()
            if text:
                result.append(text)
        return result
    return []


def _extract_missing_fields_from_trace(trace: dict[str, Any]) -> list[str]:
    direct = _string_list(trace.get("missing_required_fields") or trace.get("incomplete_details"))
    if direct:
        return direct

    fields: list[str] = []
    for attempt in trace.get("parse_attempts") or []:
        if not isinstance(attempt, dict):
            continue
        error_text = str(attempt.get("error") or "").strip()
        fields.extend(_parse_missing_fields_from_error(error_text))
    if fields:
        seen = []
        for field in fields:
            if field not in seen:
                seen.append(field)
        return seen
    return []


def _parse_missing_fields_from_error(error_text: str) -> list[str]:
    marker = "missing required fields"
    if marker not in error_text:
        return []
    start = error_text.rfind("[")
    end = error_text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    literal = error_text[start : end + 1]
    try:
        parsed = ast.literal_eval(literal)
    except (SyntaxError, ValueError):
        return []
    return _string_list(parsed)


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_manager_contract_probe"]
