from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_store_paths import require_scope
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_signal_projection"
)

APPROVED_SIGNAL_PATHS = (
    ("manager_final_decision", "memory_candidate_signal"),
    ("manager_final_decision", "memory_lab_candidate_signal"),
    ("memory_lab_projection", "candidate_signal"),
)
ALLOWED_SIGNAL_KEYS = {
    "candidate_type",
    "manager_decision_field",
    "source_refs",
    "review_status",
    "promotion_allowed_now",
    "human_review_required",
    "reason_codes",
    "summary",
    "reinforcement_count",
    "confidence",
    "created_at",
    "last_seen_at",
    "default_max_days",
    "confirmed",
    "conflicts_with",
    "store_name",
    "item_names",
    "source_kind",
}
STRUCTURED_REJECTION_REASONS = {
    "canonical_correction_not_memory",
    "unsafe_instruction_attempt",
}


def project_memory_signal_for_ingress_event(event: Mapping[str, Any]) -> dict[str, Any]:
    scope_error = _scope_error(event)
    if scope_error:
        return _with_projected_signal(
            event,
            _rejection_signal(
                rejection_reason=scope_error,
                manager_decision_field="scope_validation_failed",
                source_refs=_fallback_source_refs(event),
                projection_source="scope_keys",
            ),
        )

    source_trace = _mapping(event.get("sanitized_source_trace"))
    if isinstance(source_trace.get("memory_lab_candidate_signal"), Mapping):
        return dict(event)

    signal, path = _approved_structured_signal(source_trace)
    if signal:
        return _with_projected_signal(event, _candidate_signal(signal, path))

    rejection_reason = _structured_rejection_reason(source_trace)
    return _with_projected_signal(
        event,
        _rejection_signal(
            rejection_reason=rejection_reason or "no_explicit_memory_signal",
            manager_decision_field=_manager_decision_field(rejection_reason),
            source_refs=_fallback_source_refs(event),
            projection_source="structured_rejection"
            if rejection_reason
            else "no_approved_structured_signal",
        ),
    )


def _approved_structured_signal(
    source_trace: Mapping[str, Any],
) -> tuple[Mapping[str, Any] | None, str]:
    for path in APPROVED_SIGNAL_PATHS:
        signal = _mapping(_dig(source_trace, *path))
        if signal:
            return signal, ".".join(path)
    return None, ""


def _candidate_signal(signal: Mapping[str, Any], projection_source: str) -> dict[str, Any]:
    projected = {
        key: signal[key]
        for key in ALLOWED_SIGNAL_KEYS
        if key in signal
    }
    projected["projection_source"] = projection_source
    projected.setdefault("promotion_allowed_now", False)
    projected.setdefault("human_review_required", True)
    return projected


def _rejection_signal(
    *,
    rejection_reason: str,
    manager_decision_field: str,
    source_refs: list[str],
    projection_source: str,
) -> dict[str, Any]:
    return {
        "candidate_type": "none",
        "manager_decision_field": manager_decision_field,
        "rejection_reason": rejection_reason,
        "source_refs": source_refs,
        "reason_codes": [rejection_reason],
        "projection_source": projection_source,
        "promotion_allowed_now": False,
        "human_review_required": True,
    }


def _with_projected_signal(
    event: Mapping[str, Any],
    signal: Mapping[str, Any],
) -> dict[str, Any]:
    projected = dict(event)
    source_trace = dict(_mapping(projected.get("sanitized_source_trace")))
    source_trace["memory_lab_candidate_signal"] = dict(signal)
    projected["sanitized_source_trace"] = source_trace
    return projected


def _structured_rejection_reason(source_trace: Mapping[str, Any]) -> str | None:
    decision = _mapping(source_trace.get("manager_final_decision"))
    reason = str(decision.get("memory_candidate_rejection_reason") or "")
    if reason in STRUCTURED_REJECTION_REASONS:
        return reason
    return None


def _manager_decision_field(rejection_reason: str | None) -> str:
    if rejection_reason == "unsafe_instruction_attempt":
        return "unsafe_memory_instruction_rejected"
    if rejection_reason == "canonical_correction_not_memory":
        return "canonical_correction"
    return "memory_signal_projection_rejected"


def _scope_error(event: Mapping[str, Any]) -> str | None:
    try:
        require_scope(_mapping(event.get("scope_keys")))
    except ValueError as exc:
        return str(exc)
    return None


def _fallback_source_refs(event: Mapping[str, Any]) -> list[str]:
    refs = event.get("source_trace_ids")
    if isinstance(refs, list):
        return [str(ref) for ref in refs if ref]
    request_id = str(event.get("request_id") or "")
    return [f"trace:{request_id}"] if request_id else []


def _dig(value: Mapping[str, Any], *path: str) -> Any:
    current: Any = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "APPROVED_SIGNAL_PATHS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "project_memory_signal_for_ingress_event",
]
