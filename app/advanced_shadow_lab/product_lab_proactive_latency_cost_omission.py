from __future__ import annotations

from typing import Any, Mapping


def build_product_lab_proactive_latency_cost_omission_report(
    *,
    turn_artifacts: list[Mapping[str, Any]],
    live_diagnostic_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    omissions = _omission_traces(turn_artifacts)
    provider = _provider_cost_posture(live_diagnostic_artifact)
    blockers = [
        *_turn_blockers(turn_artifacts),
        *_provider_blockers(provider),
    ]
    return {
        "artifact_type": "advanced_product_lab_proactive_latency_cost_omission_report",
        "artifact_schema_version": "1.0",
        "status": "pass" if not blockers else "blocked",
        "provider_cost_posture": provider,
        "omission_trace_count": len(omissions),
        "omitted_trigger_types": [
            str(trace.get("trigger_type") or "") for trace in omissions
        ],
        "degraded_omission_behavior": "omit_candidates_without_retry_expansion",
        "retry_expansion_attempted": False,
        "latency_budget_policy": "do_not_retry_expand_context_after_omission",
        "mainline_activation_enabled": False,
        "scheduler_delivery_allowed": False,
        "notification_delivery_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "blockers": blockers,
    }


def _provider_cost_posture(artifact: Mapping[str, Any]) -> dict[str, Any]:
    trace = _mapping(artifact.get("provider_trace_summary"))
    return {
        "provider_profile_id": str(artifact.get("provider_profile_id") or ""),
        "live_provider_used": artifact.get("live_provider_used") is True,
        "usage_present": trace.get("usage_present") is True,
        "cost_amount_claimed": False,
    }


def _omission_traces(turn_artifacts: list[Mapping[str, Any]]) -> list[Mapping[str, Any]]:
    return [
        _mapping(trace)
        for turn in turn_artifacts
        for trace in _mapping(
            turn.get("product_lab_proactive_artifact")
        ).get("omission_traces", [])
        if isinstance(trace, Mapping)
    ]


def _turn_blockers(turn_artifacts: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for index, turn in enumerate(turn_artifacts):
        if turn.get("status") != "pass":
            blockers.append(f"turn[{index}].status_{turn.get('status') or 'missing'}")
        if turn.get("canonical_product_mutation_allowed") is True:
            blockers.append(f"turn[{index}].canonical_product_mutation_allowed")
    return blockers


def _provider_blockers(provider: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if provider.get("live_provider_used") is not True:
        blockers.append("provider.live_provider_not_used")
    if provider.get("usage_present") is not True:
        blockers.append("provider.usage_missing")
    if provider.get("cost_amount_claimed") is True:
        blockers.append("provider.cost_amount_claimed_without_billing_truth")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_product_lab_proactive_latency_cost_omission_report"]
