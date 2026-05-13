from __future__ import annotations

from typing import Any, Mapping

_PROVIDER_NODES = {"recommendation_planning", "offer_synthesis"}
_ACTIVATION_FLAGS = [
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "served_to_mainline_user",
    "canonical_product_mutation_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
]


def build_recommendation_latency_cost_omission_trace(
    *,
    recommendation_artifact: Mapping[str, Any],
    stage_latency_ms: Mapping[str, int],
    provider_cost_units: Mapping[str, float] | None = None,
    latency_budget_ms: int,
    retry_expansion_attempted: bool = False,
    context_expansion_attempted: bool = False,
) -> dict[str, Any]:
    latency = _latency_trace(stage_latency_ms, latency_budget_ms)
    cost = _cost_trace(recommendation_artifact, provider_cost_units or {})
    degraded = _degraded_omission_trace(recommendation_artifact, latency)
    retry = _no_retry_expansion_trace(
        latency_budget_exceeded=latency["latency_budget_exceeded"],
        retry_expansion_attempted=retry_expansion_attempted,
        context_expansion_attempted=context_expansion_attempted,
    )
    blockers = [
        *_source_blockers(recommendation_artifact),
        *_degraded_blockers(degraded, recommendation_artifact),
        *_retry_blockers(retry),
        *_activation_blockers(recommendation_artifact),
    ]
    return {
        "artifact_type": "recommendation_latency_cost_omission_trace",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "source_artifact_type": str(recommendation_artifact.get("artifact_type") or ""),
        "latency_trace": latency,
        "cost_trace": cost,
        "degraded_omission_trace": degraded,
        "no_retry_expansion_trace": retry,
        "mainline_activation_enabled": (
            recommendation_artifact.get("mainline_activation_enabled") is True
        ),
        "canonical_product_mutation_allowed": (
            recommendation_artifact.get("canonical_product_mutation_allowed") is True
        ),
        "semantic_quality_claimed": False,
        "blockers": blockers,
    }


def _latency_trace(
    stage_latency_ms: Mapping[str, int],
    latency_budget_ms: int,
) -> dict[str, Any]:
    stage_rows = [
        {"stage": str(stage), "latency_ms": int(latency)}
        for stage, latency in stage_latency_ms.items()
    ]
    total = sum(row["latency_ms"] for row in stage_rows)
    return {
        "latency_budget_ms": int(latency_budget_ms),
        "total_latency_ms": total,
        "latency_budget_exceeded": total > int(latency_budget_ms),
        "stage_latency_rows": stage_rows,
    }


def _cost_trace(
    recommendation_artifact: Mapping[str, Any],
    provider_cost_units: Mapping[str, float],
) -> dict[str, Any]:
    nodes = [str(node) for node in recommendation_artifact.get("physical_node_order") or []]
    provider_nodes = [node for node in nodes if node in _PROVIDER_NODES]
    deterministic_nodes = [node for node in nodes if node not in _PROVIDER_NODES]
    return {
        "provider_node_count": len(provider_nodes),
        "deterministic_node_count": len(deterministic_nodes),
        "provider_cost_units_by_node": dict(provider_cost_units),
        "estimated_provider_cost_units": round(
            sum(float(value) for value in provider_cost_units.values()),
            4,
        ),
    }


def _degraded_omission_trace(
    recommendation_artifact: Mapping[str, Any],
    latency: Mapping[str, Any],
) -> dict[str, Any]:
    required = latency.get("latency_budget_exceeded") is True
    context_omitted = (
        required and recommendation_artifact.get("recommendation_served_to_lab") is not True
    )
    return {
        "required": required,
        "recommendation_context_omitted": context_omitted,
        "omission_reason": "latency_budget_exceeded" if required else "",
        "source_omission_traces": _source_omissions(recommendation_artifact),
    }


def _no_retry_expansion_trace(
    *,
    latency_budget_exceeded: bool,
    retry_expansion_attempted: bool,
    context_expansion_attempted: bool,
) -> dict[str, bool]:
    return {
        "retry_expansion_allowed": False,
        "retry_expansion_attempted": bool(retry_expansion_attempted),
        "expanded_context_after_budget_exceeded": (
            bool(latency_budget_exceeded) and bool(context_expansion_attempted)
        ),
    }


def _source_blockers(recommendation_artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if recommendation_artifact.get("artifact_type") != (
        "advanced_product_lab_recommendation_runtime_artifact"
    ):
        blockers.append("source_artifact_type.unsupported")
    if recommendation_artifact.get("status") != "pass":
        blockers.append("source_artifact.status_not_pass")
    return blockers


def _degraded_blockers(
    degraded: Mapping[str, Any],
    recommendation_artifact: Mapping[str, Any],
) -> list[str]:
    if degraded.get("required") is not True:
        return []
    if recommendation_artifact.get("recommendation_served_to_lab") is True:
        return ["degraded_omission.recommendation_served_despite_latency_budget"]
    if degraded.get("recommendation_context_omitted") is not True:
        return ["degraded_omission.context_not_omitted"]
    return []


def _retry_blockers(retry: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if retry.get("retry_expansion_attempted") is True:
        blockers.append("no_retry_expansion.retry_expansion_attempted")
    if retry.get("expanded_context_after_budget_exceeded") is True:
        blockers.append("no_retry_expansion.context_expanded_after_budget_exceeded")
    return blockers


def _activation_blockers(recommendation_artifact: Mapping[str, Any]) -> list[str]:
    return [
        f"activation_flag_true:{name}"
        for name in _ACTIVATION_FLAGS
        if recommendation_artifact.get(name) is True
    ]


def _source_omissions(recommendation_artifact: Mapping[str, Any]) -> list[dict[str, Any]]:
    retrieval = _mapping(recommendation_artifact.get("retrieval_guard_scoring"))
    return [
        dict(item)
        for item in retrieval.get("omission_traces") or []
        if isinstance(item, Mapping)
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["build_recommendation_latency_cost_omission_trace"]
