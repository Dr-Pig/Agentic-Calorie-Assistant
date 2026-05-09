from __future__ import annotations

from pathlib import Path
from typing import Any, Mapping

from app.memory.application.runtime_lab_trace_ingress_contracts import (
    MemoryIngressScopeError,
    REQUIRED_SCOPE_KEYS,
    SIDECAR_ACTIVATION_CONTRACT,
)
from app.memory.application.runtime_lab_trace_ingress_redaction import sanitize_trace
from app.memory.application.runtime_lab_trace_ingress_sources import (
    canonical_source_refs,
    dig,
    event_id,
    manager_decision_summary,
    request_id,
    resolve_scope_keys,
    source_trace_ids,
    tool_call_names,
)


def build_memory_ingress_event_from_manager_trace(
    trace: Mapping[str, Any],
    *,
    scope_overrides: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    sanitized_trace, redacted_fields = sanitize_trace(dict(trace))
    scope_keys = resolve_scope_keys(sanitized_trace, scope_overrides or {})
    missing = tuple(key for key in REQUIRED_SCOPE_KEYS if not scope_keys.get(key))
    if missing:
        raise MemoryIngressScopeError(missing)

    resolved_request_id = request_id(sanitized_trace)
    return {
        "artifact_type": "memory_ingress_event",
        "event_id": event_id(scope_keys, resolved_request_id),
        "request_id": resolved_request_id,
        "scope_keys": scope_keys,
        "source_bundle": str(dig(sanitized_trace, "trace_meta", "bundle") or "unknown"),
        "source_trace_ids": source_trace_ids(sanitized_trace, resolved_request_id),
        "canonical_source_refs": canonical_source_refs(
            sanitized_trace,
            resolved_request_id,
        ),
        "raw_user_input_redacted": dig(sanitized_trace, "request", "text"),
        "manager_decision_summary": manager_decision_summary(sanitized_trace),
        "tool_call_names": tool_call_names(sanitized_trace),
        "secret_redaction": {
            "raw_secret_values_stored": False,
            "redacted_fields": sorted(set(redacted_fields)),
        },
        "runtime_connected": True,
        "lab_isolated": True,
        "runtime_effect_allowed": False,
        "memory_store_written": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "shadow_memory_context_pack_used": False,
        "sanitized_source_trace": sanitized_trace,
    }


def build_memory_trace_ingress_diagnostic_artifact(
    traces: list[Mapping[str, Any]],
    *,
    scope_overrides: Mapping[str, str] | None = None,
    live_invoked: bool = False,
) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    rejected_traces: list[dict[str, Any]] = []
    for index, trace in enumerate(traces):
        try:
            events.append(
                build_memory_ingress_event_from_manager_trace(
                    trace,
                    scope_overrides=scope_overrides,
                )
            )
        except MemoryIngressScopeError as exc:
            rejected_traces.append(
                {
                    "index": index,
                    "request_id": request_id(trace),
                    "reason": str(exc),
                }
            )

    return {
        "artifact_type": "runtime_lab_memory_trace_ingress_diagnostic",
        "status": "pass" if events and not rejected_traces else "blocked",
        "activation_stage": "live_diagnostic" if live_invoked else "fixture_diagnostic",
        "runtime_connected": True,
        "lab_isolated": True,
        "live_invoked": live_invoked,
        "event_count": len(events),
        "rejected_trace_count": len(rejected_traces),
        "events": events,
        "rejected_traces": rejected_traces,
        "runtime_effect_allowed": False,
        "memory_store_written": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "manager_context_packet_changed": False,
        "shadow_memory_context_pack_used": False,
        "manager_context_injected": False,
    }


def write_memory_trace_ingress_diagnostic_artifact(
    path: Path,
    traces: list[Mapping[str, Any]],
    *,
    scope_overrides: Mapping[str, str] | None = None,
    live_invoked: bool = False,
) -> dict[str, Any]:
    from app.shared.infra.json_artifacts import write_json_artifact

    artifact = build_memory_trace_ingress_diagnostic_artifact(
        traces,
        scope_overrides=scope_overrides,
        live_invoked=live_invoked,
    )
    write_json_artifact(path, artifact)
    return artifact


__all__ = [
    "MemoryIngressScopeError",
    "REQUIRED_SCOPE_KEYS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_memory_ingress_event_from_manager_trace",
    "build_memory_trace_ingress_diagnostic_artifact",
    "write_memory_trace_ingress_diagnostic_artifact",
]
