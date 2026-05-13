from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.self_use_trace_ingress_best_practice import (
    best_practice_evidence,
)
from app.rescue.application.self_use_trace_ingress_contracts import (
    REQUIRED_SCOPE_KEYS,
    SIDECAR_ACTIVATION_CONTRACT,
    RescueIngressScopeError,
)
from app.rescue.application.self_use_trace_ingress_mappers import (
    active_body_plan_view,
    current_budget_view,
    dig,
    event_id,
    mapping,
    recent_committed_meals_view,
    request_id,
    sanitize,
    scope_keys,
    source_refs,
)


def build_rescue_ingress_event_from_self_use_trace(
    trace: Mapping[str, Any],
    *,
    scope_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    sanitized_trace, redacted_fields = sanitize(dict(trace))
    resolved_scope = scope_keys(sanitized_trace, scope_overrides or {})
    missing = tuple(key for key in REQUIRED_SCOPE_KEYS if not resolved_scope.get(key))
    if missing:
        raise RescueIngressScopeError(missing)

    resolved_request_id = request_id(sanitized_trace)
    context_snapshot = mapping(sanitized_trace.get("context_snapshot"))
    budget = current_budget_view(sanitized_trace)
    meals = recent_committed_meals_view(sanitized_trace)
    body_plan = active_body_plan_view(sanitized_trace)
    return {
        "artifact_type": "rescue_ingress_event",
        "event_id": event_id(resolved_scope, resolved_request_id),
        "request_id": resolved_request_id,
        "scope_keys": resolved_scope,
        "source_bundle": str(dig(sanitized_trace, "trace_meta", "bundle") or "unknown"),
        "source_trace_ids": [resolved_request_id],
        "canonical_source_refs": source_refs(
            request_id=resolved_request_id,
            context_snapshot=context_snapshot,
            current_budget=budget,
            recent_meals=meals,
            active_body_plan=body_plan,
        ),
        "raw_user_input_redacted": dig(sanitized_trace, "request", "text"),
        "manager_context_contract": {
            "context_policy_version": str(
                dig(context_snapshot, "metadata", "context_policy_version") or ""
            ),
            "manager_context_packet_changed": False,
        },
        "current_budget_view": budget,
        "recent_committed_meals_view": meals,
        "active_body_plan_view": body_plan,
        "open_proposals_view": {"open_rescue_proposal_count": 0},
        "secret_redaction": {
            "raw_secret_values_stored": False,
            "redacted_fields": sorted(set(redacted_fields)),
        },
        "runtime_connected": True,
        "lab_isolated": True,
        "rescue_triggered": False,
        "runtime_effect_allowed": False,
        "self_use_v1_affected": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed": False,
        "sanitized_source_trace": sanitized_trace,
    }


def build_rescue_trace_ingress_diagnostic_artifact(
    traces: list[Mapping[str, Any]],
    *,
    scope_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    rejected_traces: list[dict[str, Any]] = []
    for index, trace in enumerate(traces):
        try:
            events.append(
                build_rescue_ingress_event_from_self_use_trace(
                    trace,
                    scope_overrides=scope_overrides,
                )
            )
        except RescueIngressScopeError as exc:
            rejected_traces.append(
                {"index": index, "request_id": request_id(trace), "reason": str(exc)}
            )
    return {
        "artifact_type": "rescue_trace_ingress_diagnostic",
        "status": "pass" if events and not rejected_traces else "blocked",
        "event_count": len(events),
        "rejected_trace_count": len(rejected_traces),
        "events": events,
        "rejected_traces": rejected_traces,
        "runtime_connected": True,
        "lab_isolated": True,
        "rescue_triggered": False,
        "runtime_effect_allowed": False,
        "self_use_v1_affected": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed": False,
        "best_practice_evidence": best_practice_evidence(),
    }


__all__ = [
    "REQUIRED_SCOPE_KEYS",
    "RescueIngressScopeError",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_ingress_event_from_self_use_trace",
    "build_rescue_trace_ingress_diagnostic_artifact",
]
