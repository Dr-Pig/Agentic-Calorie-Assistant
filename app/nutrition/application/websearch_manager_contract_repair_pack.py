from __future__ import annotations

from datetime import UTC, datetime
from typing import Any


WEBSEARCH_MANAGER_CONTRACT_REPAIR_PACK_NON_CLAIMS = [
    "no_live_provider_call",
    "no_live_websearch_call",
    "no_prompt_or_schema_change",
    "no_manager_contract_change",
    "no_runtime_truth_promotion",
    "no_exact_card_truth_promotion",
    "no_runtime_mutation",
    "no_packetizer_format_change",
    "no_manager_context_change",
    "no_readiness_claim",
]

_ALIAS_HINTS = {
    "intent": ["intent_type"],
    "evidence_posture": ["evidence_source"],
}

_CONTRACT_STRUCTURAL_FIELDS = {
    "answer_contract",
    "confidence",
    "evidence_honesty_posture",
    "evidence_posture",
    "evidence_source",
    "exactness",
    "final_action",
    "followup_posture",
    "intent",
    "intent_type",
    "manager_action",
    "repair_ack",
    "semantic_decision",
    "target_attachment",
    "tool_calls",
    "uncertainty_posture",
    "workflow_effect",
}
_ALLOWED_MISSING_FIELDS = {
    "confidence",
    "evidence_posture",
    "exactness",
    "intent",
    "manager_action",
    "repair_ack",
    "target_attachment",
    "workflow_effect",
}
_ALLOWED_FAILURE_FAMILIES = {
    "candidate_attachment_requires_boundary_review",
    "manager_intent_alias_gap",
    "manager_output_contract_violation",
}
_ALLOWED_SHAPE_PATTERNS = {
    "candidate_only_target_attachment_present",
    "intent_type_present_intent_missing",
    "no_commit_final_action",
    "pending_mutation_intent_candidate",
    "semantic_estimation_pending",
}
_ALLOWED_VALIDATION_ERROR_FAMILIES = {
    "manager_output_contract_violation",
}
_ALLOWED_PROBE_NEXT_SLICES = {
    "grokfast_websearch_packet_live_diagnostic",
    "inspect_websearch_manager_contract_failures",
    "narrow_prompt_schema_intent_alias_probe",
    "websearch_candidate_pipeline_narrow_expansion",
}
_ALLOWED_CASE_STATUSES = {
    "fail",
    "pass",
    "unknown",
}
_ALLOWED_PROBE_CASE_IDS = {
    "grokfast_websearch_exact_candidate_intent_type_only",
    "grokfast_websearch_size_followup_intent_type_only",
}


def build_websearch_manager_contract_repair_pack(
    *,
    contract_probe_artifact: dict[str, Any],
) -> dict[str, Any]:
    if (
        str(contract_probe_artifact.get("artifact_type") or "")
        != "accurate_intake_websearch_manager_contract_probe"
    ):
        raise ValueError("unsupported_websearch_contract_repair_probe_source")

    repair_cases = []
    alias_hint_counts: dict[str, int] = {}
    missing_field_counts: dict[str, int] = {}
    shape_pattern_counts: dict[str, int] = {}
    status_counts: dict[str, int] = {}

    for index, case in enumerate(contract_probe_artifact.get("cases") or [], start=1):
        if not isinstance(case, dict):
            continue
        case_id = _safe_case_id(case.get("case_id"), fallback=f"case_{index:03d}")
        missing_fields = _string_list(
            case.get("missing_required_fields"),
            allowed_values=_ALLOWED_MISSING_FIELDS,
        )
        observed_fields = _sanitize_present_fields(case.get("observed_keys") or [])
        shape_patterns = _string_list(
            case.get("shape_patterns"),
            allowed_values=_ALLOWED_SHAPE_PATTERNS,
        )
        alias_hints = _detect_alias_hints(
            missing_fields=missing_fields,
            present_fields=observed_fields,
        )
        for field in missing_fields:
            missing_field_counts[field] = missing_field_counts.get(field, 0) + 1
        for pattern in shape_patterns:
            shape_pattern_counts[pattern] = shape_pattern_counts.get(pattern, 0) + 1
        for hint in alias_hints:
            alias_hint_counts[hint["expected_field"]] = (
                alias_hint_counts.get(hint["expected_field"], 0) + 1
            )
        status = _safe_status(case.get("status"))
        status_counts[status] = status_counts.get(status, 0) + 1

        repair_cases.append(
            {
                "case_id": case_id,
                "status": status,
                "failure_families": _string_list(
                    case.get("failure_families"),
                    allowed_values=_ALLOWED_FAILURE_FAMILIES,
                ),
                "missing_required_fields": missing_fields,
                "present_top_level_fields": observed_fields,
                "shape_patterns": shape_patterns,
                "alias_hints": alias_hints,
                "validation_error_family": _safe_optional_string(
                    case.get("validation_error_family"),
                    allowed_values=_ALLOWED_VALIDATION_ERROR_FAMILIES,
                ),
                "recommended_owner": _recommended_owner(
                    missing_fields=missing_fields,
                    shape_patterns=shape_patterns,
                ),
            }
        )

    summary = dict(contract_probe_artifact.get("summary") or {})
    fail_count = int(summary.get("fail_count", status_counts.get("fail", 0)) or 0)
    probe_next_recommended_slice = _safe_optional_string(
        summary.get("next_recommended_slice"),
        allowed_values=_ALLOWED_PROBE_NEXT_SLICES,
    )
    next_recommended_slice = (
        "tighten_websearch_manager_contract_prompt_or_transport"
        if fail_count > 0
        else (probe_next_recommended_slice or "grokfast_websearch_packet_live_diagnostic")
    )

    return {
        "artifact_type": "accurate_intake_websearch_manager_contract_repair_pack",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "diagnostic_repair_pack_only",
        "claim_scope": "websearch_manager_contract_prompt_transport_repair_inputs",
        "runtime_truth_changed": False,
        "runtime_mutation_attempted": False,
        "manager_contract_changed": False,
        "prompt_changed": False,
        "schema_changed": False,
        "readiness_claimed": False,
        "next_recommended_slice": next_recommended_slice,
        "summary": {
            "case_count": len(repair_cases),
            "status_counts": dict(sorted(status_counts.items())),
            "aggregate_missing_required_fields": dict(sorted(missing_field_counts.items())),
            "shape_pattern_counts": dict(sorted(shape_pattern_counts.items())),
            "alias_hint_counts": dict(sorted(alias_hint_counts.items())),
            "probe_next_recommended_slice": probe_next_recommended_slice,
        },
        "cases": repair_cases,
        "non_claims": list(WEBSEARCH_MANAGER_CONTRACT_REPAIR_PACK_NON_CLAIMS),
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


def _recommended_owner(*, missing_fields: list[str], shape_patterns: list[str]) -> str:
    if "intent" in missing_fields or "intent_type_present_intent_missing" in shape_patterns:
        return "manager_runtime_contract"
    if "candidate_only_target_attachment_present" in shape_patterns:
        return "manager_runtime_contract"
    return "websearch_evidence_packet_owner"


def _sanitize_present_fields(fields: Any) -> list[str]:
    result = []
    for field in fields or []:
        text = str(field or "").strip()
        if text and text in _CONTRACT_STRUCTURAL_FIELDS:
            result.append(text)
    return sorted(set(result))


def _safe_case_id(value: Any, *, fallback: str) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_PROBE_CASE_IDS:
        return text
    return fallback


def _safe_optional_string(value: Any, *, allowed_values: set[str]) -> str | None:
    text = str(value or "").strip()
    if text in allowed_values:
        return text
    return None


def _safe_status(value: Any) -> str:
    text = str(value or "").strip()
    if text in _ALLOWED_CASE_STATUSES:
        return text
    return "unknown"


def _string_list(value: Any, *, allowed_values: set[str]) -> list[str]:
    if not isinstance(value, list):
        return []
    result = []
    for item in value:
        text = str(item or "").strip()
        if text and text in allowed_values:
            result.append(text)
    return result


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "WEBSEARCH_MANAGER_CONTRACT_REPAIR_PACK_NON_CLAIMS",
    "build_websearch_manager_contract_repair_pack",
]
