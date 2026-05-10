from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
    resolve_advanced_lab_model_profile,
    resolve_live_diagnostic_profile,
)
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
    run_recommendation_three_node_shadow,
)
from app.recommendation.application.three_node_shadow_policy import empty_candidate_guard
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_live_preflight"
)
ARTIFACT_TYPE = "recommendation_three_node_live_preflight"
PHYSICAL_NODE_ORDER = [
    "recommendation_planning",
    "candidate_retrieval_guard_scoring",
    "offer_synthesis",
]
FALSE_ACTIVATION_FLAGS = {
    "runtime_effect_allowed": False,
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "durable_product_memory_written": False,
    "manager_context_packet_changed": False,
    "user_facing_behavior_changed": False,
    "live_provider_used": False,
    "live_provider_invoked": False,
    "live_llm_invoked": False,
    "recommendation_served": False,
    "intake_committed": False,
    "product_readiness_claimed": False,
}
NON_CLAIMS = [
    "not_live_provider_activation",
    "not_kimi_activation",
    "not_runtime_activation_evidence",
    "not_recommendation_serving",
    "not_user_facing_activation",
    "not_canonical_mutation_authority",
]


def build_recommendation_three_node_live_preflight(
    *,
    payload: Mapping[str, Any] | None = None,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> dict[str, Any]:
    profile, profile_blockers = _profile(provider_profile_id)
    target = resolve_advanced_lab_model_profile(ADVANCED_LAB_TARGET_REASONING_PROFILE_ID)
    source_payload = dict(payload or build_fixture_recommendation_three_node_input())
    three_node = run_recommendation_three_node_shadow(source_payload)
    artifact_blockers = _three_node_blockers(three_node)
    blockers = [*profile_blockers, *artifact_blockers]
    candidate_guard = dict(three_node.get("candidate_guard") or empty_candidate_guard())

    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "recommendation.application.three_node_live_preflight",
        "consumer": "future_recommendation_three_node_manual_live_diagnostic",
        "retirement_trigger": "approved_recommendation_runtime_activation_plan",
        "canonical_recommendation_graph": "three_node",
        "physical_node_order": list(PHYSICAL_NODE_ORDER),
        "provider_dependency_inversion_required": True,
        "provider_mode": "preflight_no_provider_call",
        "provider_profile_id": provider_profile_id,
        "profile_role": str(profile.get("role") or ""),
        "profile_model_id": str(profile.get("model_id") or ""),
        "target_reasoning_profile_id": ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        "target_reasoning_model_id": str(target.get("model_id") or ""),
        "target_reasoning_live_calls_allowed": False,
        "provider_call_ready": False,
        "live_provider_invoked": False,
        "live_llm_invoked": False,
        "live_provider_used": False,
        "candidate_guard": candidate_guard,
        "provider_inputs": [] if blockers else _provider_inputs(source_payload, candidate_guard, profile),
        "blockers": blockers,
        "activation_flags": dict(FALSE_ACTIVATION_FLAGS),
        "non_claims": list(NON_CLAIMS),
    }


def _profile(provider_profile_id: str) -> tuple[dict[str, Any], list[str]]:
    try:
        profile, blockers = resolve_live_diagnostic_profile(provider_profile_id)
    except ValueError as exc:
        return {}, [f"profile.{exc}"]
    return dict(profile), [f"profile.{blocker}" for blocker in blockers]


def _three_node_blockers(artifact: Mapping[str, Any]) -> list[str]:
    if artifact.get("status") == "pass":
        return []
    return [
        "three_node_artifact.status_not_pass",
        *[str(blocker) for blocker in artifact.get("blockers") or []],
    ]


def _provider_inputs(
    payload: Mapping[str, Any],
    candidate_guard: Mapping[str, Any],
    profile: Mapping[str, Any],
) -> list[dict[str, Any]]:
    allowed_ids = {str(item) for item in candidate_guard.get("allowed_candidate_ids") or []}
    return [
        _node_input(
            profile=profile,
            physical_node="recommendation_planning",
            logical_outputs=["recommendation_context_result", "candidate_spec"],
            response_schema=_schema(
                "recommendation_three_node_planning_v1",
                ["recommendation_context_result", "candidate_spec", "non_serve_flags"],
            ),
            payload={
                "current_budget_view": _mapping(payload.get("current_budget_view")),
                "negative_preference_summary": _mapping(payload.get("negative_preference_summary")),
                "open_rescue_context": _mapping(payload.get("open_rescue_context")),
            },
        ),
        _node_input(
            profile=profile,
            physical_node="offer_synthesis",
            logical_outputs=["ranking_result", "recommendation_response_result"],
            response_schema=_schema(
                "recommendation_three_node_offer_synthesis_v1",
                ["ranking_result", "recommendation_response_result", "non_serve_flags"],
            ),
            payload={
                "candidate_guard": dict(candidate_guard),
                "allowed_candidate_pool": [
                    _candidate_for_offer(item)
                    for item in payload.get("candidate_source_fixture") or []
                    if isinstance(item, Mapping) and str(item.get("candidate_id")) in allowed_ids
                ],
            },
        ),
    ]


def _node_input(
    *,
    profile: Mapping[str, Any],
    physical_node: str,
    logical_outputs: list[str],
    response_schema: dict[str, Any],
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provider_input_mode": "recommendation_three_node_live_preflight_no_provider_call",
        "provider_profile_id": str(profile.get("provider_profile_id") or ""),
        "profile_model_id": str(profile.get("model_id") or ""),
        "physical_node": physical_node,
        "logical_outputs_required": logical_outputs,
        "semantic_owner": f"future_live_{physical_node}_provider_when_manually_invoked",
        "deterministic_role": "validate_schema_claims_and_hard_guards_not_select_semantics",
        "payload": payload,
        "response_schema": response_schema,
        "live_provider_invoked": False,
        "live_llm_invoked": False,
    }


def _schema(name: str, required: list[str]) -> dict[str, Any]:
    return {"name": name, "strict": True, "type": "object", "required": required}


def _candidate_for_offer(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": str(candidate.get("candidate_id") or ""),
        "title": str(candidate.get("title") or ""),
        "source_type": str(candidate.get("source_type") or ""),
        "estimated_kcal_range": _mapping(candidate.get("estimated_kcal_range")),
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
    }


def _mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_three_node_live_preflight",
]
