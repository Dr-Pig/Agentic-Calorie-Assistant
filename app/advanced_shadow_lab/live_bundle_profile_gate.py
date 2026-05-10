from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.live_bundle_profile_gate"
)

FALSE_FLAGS = {
    "runtime_connected": False,
    "mainline_runtime_connected": False,
    "mainline_route_or_api_mount_allowed": False,
    "production_scheduler_delivery_allowed": False,
    "production_db_migration_allowed": False,
    "canonical_product_mutation_allowed": False,
    "delivery_attempted": False,
    "proactive_sent": False,
    "scheduler_enabled": False,
    "live_delivery_allowed": False,
    "push_or_line_delivery_connected": False,
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
}


def resolve_live_bundle_profile_gate(
    *,
    provider_mode: str,
    provider_profile_id: str,
) -> tuple[dict[str, object] | None, dict[str, Any] | None]:
    if provider_mode != "live":
        return None, None
    try:
        profile, blockers = resolve_live_diagnostic_profile(provider_profile_id)
    except ValueError as exc:
        return None, build_blocked_live_profile_terminal_artifact(
            provider_profile_id=provider_profile_id,
            reason=str(exc),
        )
    if blockers:
        return None, build_blocked_live_profile_terminal_artifact(
            provider_profile_id=provider_profile_id,
            reason=";".join(blockers),
        )
    return profile, None


def build_blocked_live_profile_terminal_artifact(
    *, provider_profile_id: str, reason: str
) -> dict[str, Any]:
    return {
        "artifact_type": "advanced_shadow_comparison_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked",
        "owner": "app/advanced_shadow_lab/live_bundle_profile_gate.py",
        "consumer": "advanced_shadow_lab_manual_live_diagnostic",
        "retirement_trigger": "approved_advanced_runtime_activation_plan",
        "provider_mode": "not_invoked",
        "provider_profile_id": provider_profile_id,
        "live_invoked": False,
        "live_provider_used": False,
        "provider_invoked": False,
        "blockers": [reason],
        "live_diagnostic_signals": {
            "recommendation_copy_live_diagnostic": _not_invoked_signal(),
            "rescue_copy_live_diagnostic": _not_invoked_signal(),
            "proactive_copy_live_diagnostic": _not_invoked_signal(),
        },
        "non_claims": [
            "not_runtime_activation_evidence",
            "not_product_readiness_evidence",
            "not_user_facing_activation",
            "not_scheduler_delivery",
            "not_canonical_mutation_authority",
            "not_kimi_activation",
        ],
        **FALSE_FLAGS,
    }


def _not_invoked_signal() -> dict[str, object]:
    return {
        "live_invoked": False,
        "live_provider_used": False,
        "provider_mode": "not_invoked",
        "output_guard_status": "not_invoked",
    }


__all__ = [
    "ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID",
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_blocked_live_profile_terminal_artifact",
    "resolve_live_bundle_profile_gate",
]
