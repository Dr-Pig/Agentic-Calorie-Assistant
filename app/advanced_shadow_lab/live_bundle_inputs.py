from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from app.advanced_shadow_lab.live_bundle_fixture_inputs import (
    build_live_bundle_chain_payload,
    build_live_bundle_memory_review,
)
from app.advanced_shadow_lab.live_bundle_profile_gate import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_bundle_profile_gate,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract
from app.shared.infra.json_artifacts import write_json_artifact


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.live_bundle_inputs"
)
MEMORY_REVIEW_FILENAME = "memory_dogfood_replay_review.json"
CHAIN_PAYLOAD_FILENAME = "chain_payload.json"
PREFLIGHT_FILENAME = "live_bundle_input_preflight.json"
ALLOW_ENV = "ADVANCED_SHADOW_LAB_ALLOW_LIVE_LLM_DIAGNOSTIC"
ENV_KEYS = (
    "AI_BUILDER_TOKEN",
    "AI_BUILDER_BASE_URL",
    "BUILDERSPACE_MANAGER_MODEL",
    "AI_BUILDER_TIMEOUT_SECONDS",
    "AI_BUILDER_TRANSPORT_RETRY_COUNT",
    ALLOW_ENV,
)
FALSE_FLAGS = {
    "live_provider_invoked": False,
    "live_provider_used": False,
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "recommendation_served": False,
    "rescue_committed": False,
    "proposal_committed": False,
    "durable_product_memory_written": False,
    "durable_memory_written": False,
    "mutation_changed": False,
    "user_facing_behavior_changed": False,
    "product_readiness_claimed": False,
    "provider_specific_product_semantics_allowed": False,
}
NON_CLAIMS = [
    "not_runtime_activation_evidence",
    "not_product_readiness_evidence",
    "not_user_facing_activation",
    "not_scheduler_delivery",
    "not_canonical_mutation_authority",
    "not_kimi_activation",
]


def build_live_bundle_preflight(
    *,
    provider_mode: str = "fake",
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    allow_live_provider: bool = False,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    env_map = os.environ if env is None else env
    profile, blocked = resolve_live_bundle_profile_gate(
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
    )
    blockers: list[str] = []
    if blocked is not None:
        blockers.extend(str(item) for item in blocked.get("blockers") or [])
    if provider_mode == "live" and blocked is None:
        if not allow_live_provider or env_map.get(ALLOW_ENV) != "1":
            blockers.append("live_gate_not_enabled")
        elif not _present(env_map, "AI_BUILDER_TOKEN"):
            blockers.append("ai_builder_token_missing")
    return {
        "artifact_type": "advanced_shadow_live_bundle_input_preflight",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/advanced_shadow_lab/live_bundle_inputs.py",
        "consumer": "advanced_shadow_lab_manual_live_diagnostic",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "provider_mode": provider_mode,
        "provider_profile_id": provider_profile_id,
        "profile_role": str(_mapping(profile).get("role") or ""),
        "profile_model_id": str(_mapping(profile).get("model_id") or ""),
        "allow_live_provider_flag": bool(allow_live_provider),
        "environment_presence": {key: _present(env_map, key) for key in ENV_KEYS},
        "input_artifacts": {
            "memory_review": "runtime_lab_memory_dogfood_replay_review",
            "chain_payload": "advanced_shadow_live_bundle_chain_payload",
        },
        "blockers": blockers,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def write_live_bundle_inputs(
    output_dir: Path,
    *,
    provider_mode: str = "fake",
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    allow_live_provider: bool = False,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)
    memory_review = build_live_bundle_memory_review()
    chain_payload = build_live_bundle_chain_payload()
    preflight = build_live_bundle_preflight(
        provider_mode=provider_mode,
        provider_profile_id=provider_profile_id,
        allow_live_provider=allow_live_provider,
        env=env,
    )
    paths = {
        "memory_review_path": output_dir / MEMORY_REVIEW_FILENAME,
        "chain_payload_path": output_dir / CHAIN_PAYLOAD_FILENAME,
        "preflight_path": output_dir / PREFLIGHT_FILENAME,
    }
    write_json_artifact(paths["memory_review_path"], memory_review)
    write_json_artifact(paths["chain_payload_path"], chain_payload)
    write_json_artifact(paths["preflight_path"], preflight)
    return {
        **paths,
        "memory_review": memory_review,
        "chain_payload": chain_payload,
        "preflight": preflight,
    }


def _present(env: Mapping[str, str], key: str) -> bool:
    return bool(str(env.get(key) or "").strip())


def _mapping(value: object) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_live_bundle_chain_payload",
    "build_live_bundle_memory_review",
    "build_live_bundle_preflight",
    "write_live_bundle_inputs",
]
