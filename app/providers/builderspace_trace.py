from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def new_transport_attempt(attempt_index: int, base_url: str, model: str, stage: str) -> dict[str, Any]:
    return {
        "attempt_index": attempt_index,
        "started_at_utc": _utc_now_iso(),
        "base_url": base_url,
        "endpoint": f"{base_url}/chat/completions",
        "model": model,
        "stage": stage,
    }


def build_success_trace(
    *,
    stage: str,
    provider: str,
    model: str,
    request_payload: dict[str, Any],
    response_text: str | None,
    parsed: dict[str, Any],
    data: dict[str, Any],
    transport_attempts: list[dict[str, Any]],
    parse_attempts: list[dict[str, Any]],
    transport_meta: dict[str, Any],
    decision_transport_meta: dict[str, Any],
    finish_reason: str | None,
    response_status: int | None,
    raw_content: str | None,
    parse_meta: dict[str, Any],
    effective_response_format_type: str | None,
) -> dict[str, Any]:
    return {
        "stage": stage,
        "provider": provider,
        "model": model,
        "request_payload": request_payload,
        "raw_content": raw_content,
        "raw_response_excerpt": (response_text or "")[:1200] if response_text is not None else None,
        "parsed_object": parsed,
        "status": data.get("status"),
        "incomplete_details": data.get("incomplete_details"),
        "usage": data.get("usage"),
        "transport_attempts": transport_attempts,
        "parse_attempts": parse_attempts + list(parse_meta.get("parse_attempts") or []),
        "finish_reason": finish_reason,
        "response_status": response_status,
        "parse_contract_status": parse_meta.get("parse_contract_status"),
        "parse_recovery_used": parse_meta.get("parse_recovery_used"),
        "parse_recovery_strategy": parse_meta.get("parse_recovery_strategy"),
        "parse_recovery_ambiguous": parse_meta.get("parse_recovery_ambiguous"),
        "raw_content_excerpt": parse_meta.get("raw_content_excerpt"),
        "request_failure_family": None,
        "structured_output_transport_attempted": transport_meta["structured_output_transport_attempted"],
        "structured_output_transport_mode": transport_meta["structured_output_transport_mode"],
        "structured_output_transport_accepted": transport_meta["structured_output_transport_accepted"],
        "structured_output_transport_fallback": transport_meta["structured_output_transport_fallback"],
        "fallback_reason": transport_meta["fallback_reason"],
        "structured_output_transport_constraint_snapshot": transport_meta["structured_output_transport_constraint_snapshot"],
        "schema_name": decision_transport_meta.get("schema_name") or transport_meta.get("schema_name"),
        "schema_version": decision_transport_meta.get("schema_version") or transport_meta.get("schema_version"),
        "forbidden_as_success": transport_meta.get("forbidden_as_success", []),
        "repair_attempted": bool(transport_meta.get("repair_attempted")),
        "repair_result": transport_meta.get("repair_result") or "not_needed",
        "repair_attempt_count": int(transport_meta.get("repair_attempt_count") or 0),
        "effective_response_format_type": effective_response_format_type,
        "decision_transport_attempted": decision_transport_meta["decision_transport_attempted"],
        "decision_transport_mode": decision_transport_meta["decision_transport_mode"],
        "decision_transport_accepted": decision_transport_meta["decision_transport_accepted"],
        "decision_transport_fallback": decision_transport_meta["decision_transport_fallback"],
        "decision_transport_fallback_reason": decision_transport_meta["decision_transport_fallback_reason"],
        "decision_transport_contract_breach": decision_transport_meta["decision_transport_contract_breach"],
        "decision_transport_constraint_snapshot": decision_transport_meta["decision_transport_constraint_snapshot"],
        "decision_transport_schema_name": decision_transport_meta.get("schema_name"),
        "decision_transport_schema_version": decision_transport_meta.get("schema_version"),
    }


def build_failure_trace(
    *,
    exc: Exception,
    stage: str,
    provider: str,
    model: str,
    request_payload: dict[str, Any],
    transport_attempts: list[dict[str, Any]],
    parse_attempts: list[dict[str, Any]],
    base_url: str,
    timeout_seconds: int,
    response_text: str | None,
    response_status: int | None,
    data: dict[str, Any] | None,
    transport_meta: dict[str, Any],
    decision_transport_meta: dict[str, Any],
    effective_response_format_type: str | None,
) -> dict[str, Any]:
    failure_family = _failure_family(
        exc=exc,
        response_status=response_status,
        transport_meta=transport_meta,
        decision_transport_meta=decision_transport_meta,
        effective_response_format_type=effective_response_format_type,
    )
    return {
        "stage": stage,
        "provider": provider,
        "model": model,
        "request_payload": request_payload,
        "transport_attempts": transport_attempts,
        "parse_attempts": list(parse_attempts) + list(getattr(exc, "parse_attempts", []) or []),
        "base_url": base_url,
        "timeout_seconds": timeout_seconds,
        "request_failure_family": failure_family,
        "failure_family": failure_family,
        "failing_component": getattr(exc, "failing_component", "builderspace_adapter.complete_with_trace"),
        "violation_family": getattr(exc, "violation_family", None),
        "actual_shape": getattr(exc, "actual_shape", None),
        "parsed_object": getattr(exc, "observed_value", None),
        "observed_type": getattr(exc, "observed_type", None),
        "value_excerpt": getattr(exc, "value_excerpt", None),
        "value_truncated": getattr(exc, "value_truncated", None),
        "raw_content_excerpt": getattr(exc, "raw_content_excerpt", None),
        "raw_content_truncated": getattr(exc, "raw_content_truncated", None),
        "raw_response_excerpt": (response_text or "")[:1200] if response_text is not None else None,
        "response_status": response_status,
        "status": data.get("status") if isinstance(data, dict) else None,
        "incomplete_details": data.get("incomplete_details") if isinstance(data, dict) else None,
        "usage": data.get("usage") if isinstance(data, dict) else None,
        "finish_reason": _extract_finish_reason(data),
        "parse_contract_status": getattr(exc, "parse_contract_status", None),
        "parse_recovery_used": getattr(exc, "parse_recovery_used", False),
        "parse_recovery_strategy": getattr(exc, "parse_recovery_strategy", None),
        "parse_recovery_ambiguous": getattr(exc, "parse_recovery_ambiguous", False),
        "structured_output_transport_attempted": transport_meta["structured_output_transport_attempted"],
        "structured_output_transport_mode": transport_meta["structured_output_transport_mode"],
        "structured_output_transport_accepted": transport_meta["structured_output_transport_accepted"],
        "structured_output_transport_fallback": transport_meta["structured_output_transport_fallback"],
        "fallback_reason": transport_meta["fallback_reason"],
        "structured_output_transport_constraint_snapshot": transport_meta["structured_output_transport_constraint_snapshot"],
        "schema_name": decision_transport_meta.get("schema_name") or transport_meta.get("schema_name"),
        "schema_version": decision_transport_meta.get("schema_version") or transport_meta.get("schema_version"),
        "forbidden_as_success": transport_meta.get("forbidden_as_success", []),
        "repair_attempted": bool(transport_meta.get("repair_attempted")),
        "repair_result": transport_meta.get("repair_result") or ("failed" if transport_meta.get("repair_attempted") else "not_needed"),
        "repair_attempt_count": int(transport_meta.get("repair_attempt_count") or 0),
        "decision_transport_attempted": decision_transport_meta["decision_transport_attempted"],
        "decision_transport_mode": decision_transport_meta["decision_transport_mode"],
        "decision_transport_accepted": decision_transport_meta["decision_transport_accepted"],
        "decision_transport_fallback": decision_transport_meta["decision_transport_fallback"],
        "decision_transport_fallback_reason": decision_transport_meta["decision_transport_fallback_reason"],
        "decision_transport_contract_breach": decision_transport_meta["decision_transport_contract_breach"],
        "decision_transport_constraint_snapshot": decision_transport_meta["decision_transport_constraint_snapshot"],
        "decision_transport_schema_name": decision_transport_meta.get("schema_name"),
        "decision_transport_schema_version": decision_transport_meta.get("schema_version"),
        "effective_response_format_type": effective_response_format_type,
    }


def _extract_finish_reason(data: dict[str, Any] | None) -> str | None:
    if not isinstance(data, dict):
        return None
    choices = data.get("choices")
    if not isinstance(choices, list) or not choices:
        return None
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return None
    finish_reason = first_choice.get("finish_reason")
    return finish_reason if isinstance(finish_reason, str) else None


def _failure_family(
    *,
    exc: Exception,
    response_status: int | None,
    transport_meta: dict[str, Any],
    decision_transport_meta: dict[str, Any],
    effective_response_format_type: str | None,
) -> str | None:
    explicit = getattr(exc, "failure_family", None)
    if explicit:
        return explicit
    if response_status not in {400, 404, 415, 422}:
        return None
    if decision_transport_meta.get("decision_transport_attempted") and not decision_transport_meta.get(
        "decision_transport_accepted"
    ):
        return "tool_choice_rejected"
    if (
        transport_meta.get("structured_output_transport_attempted")
        and effective_response_format_type == "json_schema"
    ):
        return "schema_transport_rejected"
    return "provider_runtime_error"
