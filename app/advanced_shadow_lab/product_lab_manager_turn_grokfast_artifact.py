from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.model_profiles import advanced_lab_model_profile_policy
from app.advanced_shadow_lab.product_lab_manager_turn_grokfast_policy import (
    manager_turn_tool_order,
)


def build_manager_turn_grokfast_artifact(
    *,
    artifact_type: str,
    status: str,
    runtime_artifact: Mapping[str, Any],
    provider_mode: str,
    provider_profile_id: str,
    live_invoked: bool,
    provider_invoked: bool,
    provider: Any,
    provider_trace: Mapping[str, Any],
    provider_error: Mapping[str, Any],
    provider_result: Mapping[str, Any],
    output_guard: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": artifact_type,
        "artifact_schema_version": "1.0",
        "status": status,
        **dict(FALSE_FLAGS),
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "diagnostic_evidence_class": _evidence_class(live_invoked, provider_invoked),
        "live_invoked": bool(live_invoked),
        "provider_invoked": bool(provider_invoked),
        "live_provider_used": bool(live_invoked and provider_invoked),
        "live_grokfast_diagnostic_pass": (
            live_invoked and provider_invoked and status == "pass"
        ),
        "source_manager_tool_order": manager_turn_tool_order(runtime_artifact),
        "model_profile_policy": advanced_lab_model_profile_policy(),
        "provider_readiness": _mapping(provider.readiness()) if hasattr(provider, "readiness") else {},
        "provider_trace_summary": _trace_summary(provider_trace),
        "provider_error": dict(provider_error),
        "model_output_summary": _model_output_summary(provider_result),
        "output_guard": dict(output_guard),
        "blockers": blockers,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
    }


def _model_output_summary(output: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "claim_scope": str(output.get("claim_scope") or ""),
        "selected_capabilities": [str(item) for item in output.get("selected_capabilities") or []],
        "tool_call_order": [str(item) for item in output.get("tool_call_order") or []],
        "manager_turn_summary_present": bool(str(output.get("manager_turn_summary") or "")),
        "risk_notes_present": bool(str(output.get("risk_notes") or "")),
    }


def _trace_summary(trace: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "stage": str(trace.get("stage") or ""),
        "provider": str(trace.get("provider") or ""),
        "usage_present": isinstance(trace.get("usage"), Mapping),
    }


def _evidence_class(live_invoked: bool, provider_invoked: bool) -> str:
    if live_invoked and provider_invoked:
        return "live_grokfast"
    if provider_invoked:
        return "fake_contract"
    return "blocked_not_invoked"


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = ["build_manager_turn_grokfast_artifact"]
