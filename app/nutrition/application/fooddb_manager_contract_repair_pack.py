from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any


_ALIAS_HINTS = {
    "intent": ["intent_type"],
    "confidence": [],
    "exactness": [],
    "repair_ack": [],
    "target_attachment": [],
    "workflow_effect": [],
    "evidence_posture": ["evidence_source"],
}

_CONTRACT_STRUCTURAL_FIELDS = {
    "manager_action",
    "tool_calls",
    "intent",
    "intent_type",
    "target_attachment",
    "final_action",
    "workflow_effect",
    "semantic_decision",
    "answer_contract",
    "exactness",
    "confidence",
    "evidence_posture",
    "evidence_source",
    "repair_ack",
    "uncertainty_posture",
    "evidence_honesty_posture",
    "followup_posture",
}


def build_fooddb_manager_contract_repair_pack(
    *,
    diagnostic_artifact: dict[str, Any],
    contract_probe_artifact: dict[str, Any],
) -> dict[str, Any]:
    if str(diagnostic_artifact.get("artifact_type") or "") != "accurate_intake_grokfast_fooddb_packet_smoke":
        raise ValueError("unsupported_fooddb_contract_repair_diagnostic_source")
    if str(contract_probe_artifact.get("artifact_type") or "") != "accurate_intake_fooddb_manager_contract_probe":
        raise ValueError("unsupported_fooddb_contract_repair_probe_source")

    case_probe_by_id = {
        str(case.get("case_id") or ""): case
        for case in contract_probe_artifact.get("cases") or []
        if isinstance(case, dict)
    }
    repair_cases = []
    alias_hint_counts: dict[str, int] = {}
    present_field_counts: dict[str, int] = {}
    probe_match_status_counts: dict[str, int] = {}
    trace_status_counts: dict[str, int] = {}

    for case in diagnostic_artifact.get("cases") or []:
        if not isinstance(case, dict):
            continue
        case_id = str(case.get("case_id") or "").strip()
        provider_trace = case.get("provider_trace")
        trace = _provider_trace_payload(provider_trace)
        trace_status = "trace_present" if isinstance(trace, dict) else "missing_provider_trace"
        trace_status_counts[trace_status] = trace_status_counts.get(trace_status, 0) + 1

        parsed_object = _parsed_object_dict(trace)
        present_fields = _sanitize_present_fields(parsed_object.keys())
        for field in present_fields:
            present_field_counts[field] = present_field_counts.get(field, 0) + 1

        probe_case = case_probe_by_id.get(case_id, {})
        probe_match_status = "matched_probe_case" if probe_case else "missing_probe_case"
        probe_match_status_counts[probe_match_status] = probe_match_status_counts.get(probe_match_status, 0) + 1
        missing_fields = list(probe_case.get("missing_required_fields") or [])
        alias_hints = _detect_alias_hints(missing_fields=missing_fields, present_fields=present_fields)
        for hint in alias_hints:
            alias_hint_counts[hint["expected_field"]] = alias_hint_counts.get(hint["expected_field"], 0) + 1

        repair_cases.append(
            {
                "case_id": case_id,
                "failure_families": list(case.get("failure_families") or []),
                "missing_required_fields": missing_fields,
                "present_top_level_fields": present_fields,
                "alias_hints": alias_hints,
                "probe_match_status": probe_match_status,
                "trace_status": trace_status,
                "failing_component": probe_case.get("failing_component"),
                "effective_response_format_type": probe_case.get("effective_response_format_type"),
                "decision_transport_mode": probe_case.get("decision_transport_mode"),
            }
        )

    needs_alignment = (
        probe_match_status_counts.get("missing_probe_case", 0) > 0
        or trace_status_counts.get("missing_provider_trace", 0) > 0
    )
    next_recommended_slice = (
        "repair_artifact_alignment_required"
        if needs_alignment
        else "tighten_fooddb_manager_contract_prompt_or_transport"
    )

    return {
        "artifact_type": "accurate_intake_fooddb_manager_contract_repair_pack",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_repair_pack_only",
        "claim_scope": "fooddb_manager_contract_prompt_transport_repair_inputs",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "readiness_claimed": False,
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": len(repair_cases),
            "aggregate_missing_required_fields": dict(
                contract_probe_artifact.get("summary", {}).get("aggregate_missing_required_fields") or {}
            ),
            "present_field_counts": dict(sorted(present_field_counts.items())),
            "alias_hint_counts": dict(sorted(alias_hint_counts.items())),
            "probe_match_status_counts": dict(sorted(probe_match_status_counts.items())),
            "trace_status_counts": dict(sorted(trace_status_counts.items())),
        },
        "cases": repair_cases,
        "non_claims": [
            "no_live_provider_call",
            "no_runtime_truth_promotion",
            "no_mutation_legality_change",
            "no_packetizer_format_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _detect_alias_hints(*, missing_fields: list[str], present_fields: list[str]) -> list[dict[str, str]]:
    present = set(present_fields)
    hints: list[dict[str, str]] = []
    for missing in missing_fields:
        for candidate in _ALIAS_HINTS.get(missing, []):
            if candidate in present:
                hints.append(
                    {
                        "expected_field": missing,
                        "observed_field": candidate,
                    }
                )
    return hints


def _provider_trace_payload(provider_trace: Any) -> dict[str, Any] | None:
    if not isinstance(provider_trace, dict):
        return None
    if not provider_trace:
        return None
    nested = provider_trace.get("trace")
    if isinstance(nested, dict):
        return nested
    return provider_trace


def _parsed_object_dict(trace: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(trace, dict):
        return {}
    parsed_object = trace.get("parsed_object")
    if isinstance(parsed_object, dict):
        return parsed_object
    if isinstance(parsed_object, str):
        try:
            decoded = json.loads(parsed_object)
        except json.JSONDecodeError:
            return {}
        if isinstance(decoded, dict):
            return decoded
    return {}


def _sanitize_present_fields(fields: Any) -> list[str]:
    result = []
    for field in fields:
        text = str(field or "").strip()
        if not text or text not in _CONTRACT_STRUCTURAL_FIELDS:
            continue
        result.append(text)
    return sorted(set(result))


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = ["build_fooddb_manager_contract_repair_pack"]
