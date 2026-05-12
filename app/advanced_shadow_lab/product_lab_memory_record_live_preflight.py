from __future__ import annotations

from typing import Any

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_live_diagnostic_profile,
)


PREFLIGHT_ARTIFACT_TYPE = "advanced_product_lab_memory_record_live_edd_preflight"
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_self_use_v1_activation",
    "not_production_scheduler_delivery",
    "not_canonical_mutation",
    "not_durable_product_memory",
    "not_kimi_activation",
]


def build_memory_record_live_edd_preflight(
    *,
    provider_mode: str,
    allow_live_provider: bool,
    env_live_gate_enabled: bool,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> dict[str, Any]:
    normalized_mode = str(provider_mode or "")
    blockers: list[str] = []
    profile: dict[str, object] = {}
    if normalized_mode not in {"fake", "live"}:
        blockers.append(f"provider_mode_unsupported:{normalized_mode or 'missing'}")
    if normalized_mode == "live":
        profile, profile_blockers = _profile_and_blockers(provider_profile_id)
        blockers.extend(profile_blockers)
        if not allow_live_provider or not env_live_gate_enabled:
            blockers.append("live_gate_not_enabled")
    elif normalized_mode == "fake":
        profile, _ = _profile_and_blockers(provider_profile_id)

    live_ready = normalized_mode == "live" and not blockers
    fake_pass = normalized_mode == "fake" and not blockers
    status = "pass" if live_ready or fake_pass else "blocked"
    return {
        "artifact_type": PREFLIGHT_ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_memory_record_live_preflight.py",
        "consumer": "advanced_product_lab_memory_live_edd_gate",
        "provider_mode": normalized_mode,
        "provider_profile_id": str(provider_profile_id),
        "profile": profile,
        "allow_live_provider_flag": bool(allow_live_provider),
        "env_live_gate_enabled": bool(env_live_gate_enabled),
        "fake_contract_preflight_pass": fake_pass,
        "live_provider_invocation_allowed": live_ready,
        "live_milestone_preflight_ready": live_ready,
        "reviewed_preflight_status": _preflight_review_status(
            status=status,
            provider_mode=normalized_mode,
            live_ready=live_ready,
            fake_pass=fake_pass,
        ),
        "blockers": blockers,
        "lab_enabled": True,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "kimi_live_calls_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _profile_and_blockers(provider_profile_id: str) -> tuple[dict[str, object], list[str]]:
    try:
        return resolve_live_diagnostic_profile(provider_profile_id)
    except ValueError as exc:
        return {}, [str(exc)]


def _preflight_review_status(
    *,
    status: str,
    provider_mode: str,
    live_ready: bool,
    fake_pass: bool,
) -> str:
    if live_ready:
        return "live_grokfast_preflight_ready"
    if fake_pass:
        return "fake_contract_preflight_passed_non_live"
    if status == "blocked":
        return "blocked_not_invoked_preflight"
    return f"noncanonical_preflight:{provider_mode or 'missing'}"
