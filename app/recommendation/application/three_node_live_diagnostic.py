from __future__ import annotations

import asyncio
from typing import Any, Mapping

from app.recommendation.application.three_node_diagnostic_fake_provider import (
    FakeRecommendationThreeNodeDiagnosticProvider,
)
from app.recommendation.application.three_node_diagnostic_policy import (
    field_by_node,
    mapping,
    node_blockers,
    offer_output,
    output_blockers,
    payload_from_preflight,
    preflight_blockers,
    recommendation_response,
    trace_summary,
)
from app.recommendation.application.three_node_live_preflight import (
    FALSE_ACTIVATION_FLAGS,
    build_recommendation_three_node_live_preflight,
)
from app.recommendation.application.three_node_shadow_policy import candidate_guard
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_live_diagnostic"
)
ARTIFACT_TYPE = "recommendation_three_node_live_diagnostic"
NON_CLAIMS = [
    "not_runtime_activation_evidence",
    "not_product_readiness_evidence",
    "not_user_facing_activation",
    "not_recommendation_serving",
    "not_canonical_mutation_authority",
    "not_kimi_activation",
]


def run_recommendation_three_node_live_diagnostic(
    *,
    preflight: Mapping[str, Any] | None = None,
    provider: Any | None = None,
    provider_mode: str = "fake_provider_contract_test",
    live_invoked: bool = False,
    live_requested: bool | None = None,
    pre_run_blockers: list[str] | None = None,
    provider_gate: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    preflight_artifact = dict(preflight or build_recommendation_three_node_live_preflight())
    blocked_preflight = preflight_blockers(preflight_artifact)
    active_provider = provider or FakeRecommendationThreeNodeDiagnosticProvider()
    node_outputs: list[dict[str, Any]] = []
    blockers = [*blocked_preflight, *(pre_run_blockers or [])]

    if not blockers:
        node_outputs = [
            _run_node(active_provider, node_input, provider_mode, live_invoked)
            for node_input in preflight_artifact.get("provider_inputs") or []
        ]
        blockers.extend(node_blockers(node_outputs))

    guard = candidate_guard(payload_from_preflight(preflight_artifact))
    output = offer_output(node_outputs) if not blockers else {}
    response = recommendation_response(output, guard) if not blockers else None
    if response is None and not blockers:
        blockers.append("offer_synthesis.output.recommendation_response_missing")

    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "diagnostic_only": True,
        "fixed_case_matrix_used": True,
        "semantic_quality_claimed": False,
        "provider_mode": provider_mode,
        "provider_profile_id": str(preflight_artifact.get("provider_profile_id") or ""),
        "live_requested": bool(live_invoked if live_requested is None else live_requested),
        "live_invoked": bool(live_invoked),
        "live_provider_invoked": bool(live_invoked and node_outputs),
        "live_llm_invoked": bool(live_invoked and node_outputs),
        "provider_gate": dict(provider_gate or {}),
        "node_outputs": node_outputs,
        "node_status_by_physical_node": field_by_node(node_outputs, "status"),
        "node_provider_used_by_physical_node": {
            str(row.get("physical_node") or ""): row.get("live_provider_used") is True
            for row in node_outputs
        },
        "candidate_guard": guard,
        "deterministic_guard_replayed": not blocked_preflight,
        "recommendation_response": response,
        "blockers": blockers,
        "activation_flags": dict(FALSE_ACTIVATION_FLAGS),
        "recommendation_served": False,
        "intake_committed": False,
        "non_claims": list(NON_CLAIMS),
    }


def _run_node(provider: Any, node_input: Mapping[str, Any], provider_mode: str, live_invoked: bool) -> dict[str, Any]:
    node = str(node_input.get("physical_node") or "")
    stage = f"recommendation_three_node_{node}"
    try:
        output, trace = asyncio.run(
            provider.complete_with_trace(
                system_prompt="Return the requested recommendation diagnostic JSON only.",
                user_payload=dict(node_input),
                stage=stage,
                max_tokens=700,
            )
        )
    except Exception as exc:
        return _provider_error_node(node, stage, provider_mode, live_invoked, exc)
    blockers = output_blockers(node, mapping(output))
    return {
        "physical_node": node,
        "status": "blocked" if blockers else "pass",
        "provider_mode": provider_mode,
        "live_provider_used": bool(live_invoked),
        "provider_trace_summary": trace_summary(trace),
        "output": mapping(output),
        "blockers": blockers,
    }


def _provider_error_node(
    node: str,
    stage: str,
    provider_mode: str,
    live_invoked: bool,
    exc: Exception,
) -> dict[str, Any]:
    trace = getattr(exc, "trace", None)
    summary = trace_summary(trace if isinstance(trace, Mapping) else {"stage": stage})
    summary["error_type"] = type(exc).__name__
    return {
        "physical_node": node,
        "status": "blocked",
        "provider_mode": provider_mode,
        "live_provider_used": bool(live_invoked),
        "provider_trace_summary": summary,
        "output": {},
        "blockers": [f"{node}.provider_runtime_error:{type(exc).__name__}"],
    }


__all__ = [
    "FakeRecommendationThreeNodeDiagnosticProvider",
    "SIDECAR_ACTIVATION_CONTRACT",
    "run_recommendation_three_node_live_diagnostic",
]
