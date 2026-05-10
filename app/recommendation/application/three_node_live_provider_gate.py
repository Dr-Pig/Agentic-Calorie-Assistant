from __future__ import annotations

import os
from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.three_node_live_provider_gate"
)
LIVE_DIAGNOSTIC_ENV = "RECOMMENDATION_THREE_NODE_LIVE_DIAGNOSTIC"
LIVE_DIAGNOSTIC_ENV_VALUE = "grokfast"
LIVE_DIAGNOSTIC_MODEL_ID = "grok-4-fast"


def build_recommendation_three_node_live_provider_gate(
    *,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    source_env = os.environ if env is None else env
    env_value = str(source_env.get(LIVE_DIAGNOSTIC_ENV) or "").strip().lower()
    live_requested = env_value == LIVE_DIAGNOSTIC_ENV_VALUE
    profile, profile_blockers = _profile(provider_profile_id)
    blockers = _gate_blockers(
        live_requested=live_requested,
        profile=profile,
        profile_blockers=profile_blockers,
    )
    gate = _gate_result(
        profile=profile,
        provider_profile_id=provider_profile_id,
        live_requested=live_requested,
        blockers=blockers,
    )
    return gate


def _profile(provider_profile_id: str) -> tuple[dict[str, Any], list[str]]:
    try:
        profile, blockers = resolve_live_diagnostic_profile(provider_profile_id)
    except ValueError as exc:
        return {}, [str(exc)]
    return dict(profile), list(blockers)


def _gate_blockers(
    *,
    live_requested: bool,
    profile: Mapping[str, Any],
    profile_blockers: list[str],
) -> list[str]:
    blockers: list[str] = []
    if not live_requested:
        blockers.append(f"live_env_not_enabled:{LIVE_DIAGNOSTIC_ENV}")
    blockers.extend(f"profile.{blocker}" for blocker in profile_blockers)
    if profile.get("model_id") != LIVE_DIAGNOSTIC_MODEL_ID:
        blockers.append("profile.model_not_grok_4_fast")
    return blockers


def _gate_result(
    *,
    profile: Mapping[str, Any],
    provider_profile_id: str,
    live_requested: bool,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "artifact_type": "recommendation_three_node_live_provider_gate",
        "status": "blocked" if blockers else "pass",
        "provider_profile_id": provider_profile_id,
        "provider_family": str(profile.get("provider_family") or ""),
        "model_id": str(profile.get("model_id") or ""),
        "role_label": str(profile.get("role_label") or ""),
        "live_env_var": LIVE_DIAGNOSTIC_ENV,
        "accepted_live_env_value": LIVE_DIAGNOSTIC_ENV_VALUE,
        "live_requested": live_requested,
        "live_provider_invoked": False,
        "kimi_live_calls_allowed": profile.get("kimi_live_calls_allowed") is True,
        "blockers": list(blockers),
        "non_claims": [
            "not_runtime_activation_evidence",
            "not_product_readiness_evidence",
            "not_kimi_activation",
            "not_recommendation_serving",
        ],
    }


__all__ = [
    "LIVE_DIAGNOSTIC_ENV",
    "LIVE_DIAGNOSTIC_ENV_VALUE",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_recommendation_three_node_live_provider_gate",
]
