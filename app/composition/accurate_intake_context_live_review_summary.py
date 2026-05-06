from __future__ import annotations

from typing import Any


def _object_dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list_value(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []


def _int_value(value: Any) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0


def _case_ids_from_canary(canary: dict[str, Any]) -> list[str]:
    output_ids = [
        str(_object_dict(output).get("case_id") or "")
        for output in _list_value(canary.get("provider_outputs"))
        if str(_object_dict(output).get("case_id") or "")
    ]
    if output_ids:
        return output_ids
    return [
        str(_object_dict(trace).get("case_id") or "")
        for trace in _list_value(canary.get("provider_traces"))
        if str(_object_dict(trace).get("case_id") or "")
    ]


def context_live_diagnostic_stage_summary(
    canary: dict[str, Any],
    *,
    required_case_count: int,
) -> dict[str, Any]:
    summary = _object_dict(canary.get("summary"))
    case_ids = _case_ids_from_canary(canary)
    provider_output_count = _int_value(summary.get("provider_output_count"))
    if not provider_output_count and case_ids:
        provider_output_count = len(case_ids)
    live_invoked = canary.get("live_invoked") is True or canary.get("live_provider_invoked") is True
    blocked_response_count = _int_value(summary.get("blocked_response_count"))

    if not live_invoked or canary.get("status") == "not_invoked":
        live_stage = "not_invoked"
        reason = "not_invoked"
    elif provider_output_count == 1 and len(case_ids) <= 1:
        live_stage = "single-case"
        reason = "single_provider_output"
    elif provider_output_count == required_case_count:
        live_stage = "full-matrix"
        reason = "full_matrix_provider_outputs"
    elif provider_output_count > 1:
        live_stage = "partial-matrix"
        reason = "partial_provider_outputs"
    else:
        live_stage = "unknown"
        reason = "provider_outputs_missing"

    return {
        "live_stage": live_stage,
        "live_stage_reason": reason,
        "live_provider_output_count": provider_output_count,
        "live_blocked_response_count": blocked_response_count,
        "single_case_live_probe_completed": (
            live_stage == "single-case" and blocked_response_count == 0
        ),
        "full_matrix_live_probe_completed": (
            live_stage == "full-matrix" and blocked_response_count == 0
        ),
        "diagnostic_only_not_readiness": True,
    }


def artifact_statuses(inputs: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {
        group_id: {
            "artifact_type": payload.get("artifact_type") or "not_available",
            "status": str(payload.get("status") or ""),
            "source_artifact_path": payload.get("_source_artifact_path") or "not_available",
        }
        for group_id, payload in inputs.items()
    }


__all__ = [
    "artifact_statuses",
    "context_live_diagnostic_stage_summary",
]
