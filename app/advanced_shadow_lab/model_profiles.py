from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Literal

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.model_profiles"
)

ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID = (
    "builderspace-grok-4-fast-advanced-shadow-lab-live-diagnostic"
)
ADVANCED_LAB_TARGET_REASONING_PROFILE_ID = (
    "builderspace-kimi-k2-5-advanced-shadow-lab-dormant-reference"
)

AdvancedLabModelRole = Literal[
    "diagnostic_live_llm",
    "target_reasoning_model",
]


@dataclass(frozen=True)
class AdvancedLabModelProfile:
    provider_profile_id: str
    role: AdvancedLabModelRole
    provider_family: str
    model_id: str
    role_label: str
    selection_status: str
    live_diagnostic_allowed: bool
    kimi_live_calls_allowed: bool
    production_selected: bool = False
    provider_specific_product_semantics_allowed: bool = False
    product_semantics_owner: str = "advanced_runtime_lab_contracts"

    def as_dict(self) -> dict[str, object]:
        return asdict(self)


_PROFILES = (
    AdvancedLabModelProfile(
        provider_profile_id=ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        role="diagnostic_live_llm",
        provider_family="builderspace",
        model_id="grok-4-fast",
        role_label="advanced_shadow_lab_live_diagnostic",
        selection_status="approved_for_manual_lab_live_diagnostic_after_gate",
        live_diagnostic_allowed=True,
        kimi_live_calls_allowed=False,
    ),
    AdvancedLabModelProfile(
        provider_profile_id=ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        role="target_reasoning_model",
        provider_family="builderspace",
        model_id="kimi-k2.5",
        role_label="advanced_shadow_lab_target_reasoning_dormant",
        selection_status="dormant_reference_only",
        live_diagnostic_allowed=False,
        kimi_live_calls_allowed=False,
    ),
)


def advanced_lab_model_profiles() -> dict[str, dict[str, object]]:
    return {profile.provider_profile_id: profile.as_dict() for profile in _PROFILES}


def advanced_lab_model_profile_policy() -> dict[str, object]:
    return {
        "artifact_type": "advanced_shadow_lab_model_profile_policy",
        "profile_selection_stage": "offline_sidecar_contract",
        "default_live_diagnostic_profile_id": ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
        "target_reasoning_profile_id": ADVANCED_LAB_TARGET_REASONING_PROFILE_ID,
        "provider_dependency_inversion_required": True,
        "provider_family": "builderspace",
        "diagnostic_live_model": "grok-4-fast",
        "target_reasoning_model": "kimi-k2.5",
        "live_provider_calls_allowed_by_default": False,
        "kimi_live_calls_allowed": False,
        "production_selected": False,
        "provider_specific_product_semantics_allowed": False,
        "profiles": advanced_lab_model_profiles(),
        "non_claims": [
            "not_live_provider_activation",
            "not_kimi_activation",
            "not_production_model_selection",
            "not_provider_semantic_ownership",
        ],
    }


def resolve_advanced_lab_model_profile(
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> dict[str, object]:
    profiles = advanced_lab_model_profiles()
    if provider_profile_id not in profiles:
        raise ValueError(f"unsupported_advanced_lab_provider_profile:{provider_profile_id}")
    return profiles[provider_profile_id]


def live_diagnostic_profile_blockers(profile: dict[str, object]) -> list[str]:
    blockers: list[str] = []
    if profile.get("provider_family") != "builderspace":
        blockers.append("provider_family_not_builderspace")
    if profile.get("live_diagnostic_allowed") is not True:
        blockers.append("profile_not_live_diagnostic_allowed")
    if profile.get("model_id") == "kimi-k2.5":
        blockers.append("kimi_live_calls_forbidden")
    if profile.get("kimi_live_calls_allowed") is True:
        blockers.append("kimi_live_call_flag_must_remain_false")
    if profile.get("provider_specific_product_semantics_allowed") is True:
        blockers.append("provider_specific_product_semantics_forbidden")
    if profile.get("production_selected") is True:
        blockers.append("production_model_selection_forbidden")
    return blockers


def resolve_live_diagnostic_profile(
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> tuple[dict[str, object], list[str]]:
    profile = resolve_advanced_lab_model_profile(provider_profile_id)
    return profile, live_diagnostic_profile_blockers(profile)


__all__ = [
    "ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID",
    "ADVANCED_LAB_TARGET_REASONING_PROFILE_ID",
    "SIDECAR_ACTIVATION_CONTRACT",
    "advanced_lab_model_profile_policy",
    "advanced_lab_model_profiles",
    "live_diagnostic_profile_blockers",
    "resolve_advanced_lab_model_profile",
    "resolve_live_diagnostic_profile",
]
