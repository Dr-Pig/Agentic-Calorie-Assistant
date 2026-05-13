from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_advanced_lab_model_profile,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.response_presentation_contracts"
)
STAGE = "rescue_phase1_response_presentation"
PRIMARY_ACTIONS = [
    {"action_id": "accept_rescue_plan", "label": "接受這個方案"},
    {"action_id": "dismiss_rescue_plan", "label": "先不要"},
]
SECONDARY_INTENTS = [
    "shorten_rescue_plan",
    "extend_rescue_plan",
    "explain_rescue_plan",
]
REQUIRED_OUTPUT_FIELDS = [
    "reply_text",
    "primary_actions",
    "negotiation_affordance",
    "ui_hints",
    "claim_scope",
    "action_request",
    "delivery_request",
    "mutation_request",
    "reason_codes",
]
CARD_MATH_FIELDS = (
    "overshoot_kcal",
    "recommended_days",
    "daily_kcal_adjustment",
    "cap_mode",
    "effective_from",
)
FALSE_OUTPUT_FLAGS = {
    "runtime_effect_allowed": False,
    "canonical_mutation_changed": False,
    "mainline_activation_enabled": False,
    "production_scheduler_delivery_allowed": False,
    "proposal_committed": False,
    "ledger_entry_created": False,
    "durable_product_memory_written_in_mainline": False,
    "manager_context_packet_changed_in_mainline": False,
}


def build_rescue_response_presentation_payload(
    *,
    proposal_id: str,
    proposal_shaping_payload: Mapping[str, Any],
    proposal_shaping_validation: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
    effective_from_policy: Mapping[str, Any],
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> dict[str, Any]:
    profile = resolve_advanced_lab_model_profile(provider_profile_id)
    shaped_proposal = mapping(proposal_shaping_validation.get("shaped_proposal"))
    card_math = _card_math(
        proposal_shaping_payload=proposal_shaping_payload,
        option_generation_result=option_generation_result,
        effective_from_policy=effective_from_policy,
    )
    blockers = _input_blockers(
        proposal_shaping_payload,
        proposal_shaping_validation,
        option_generation_result,
        effective_from_policy,
        shaped_proposal,
        card_math,
    )
    return {
        "artifact_type": "rescue_response_presentation_payload",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "rescue_response_card",
        "stage": STAGE,
        "decision_mode": "llm_response_writer_with_deterministic_action_guard",
        "proposal_id": proposal_id,
        "provider_profile_id": provider_profile_id,
        "provider_contract": _provider_contract(profile),
        "primary_actions_contract": list(PRIMARY_ACTIONS),
        "secondary_affordance_contract": list(SECONDARY_INTENTS),
        "card_math": card_math,
        "provider_request": {}
        if blockers
        else _provider_request(shaped_proposal=shaped_proposal, card_math=card_math),
        "blockers": blockers,
        "lab_user_facing_surface_allowed": not blockers,
        "live_llm_invoked": False,
        "provider_called": False,
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _card_math(
    *,
    proposal_shaping_payload: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
    effective_from_policy: Mapping[str, Any],
) -> dict[str, Any]:
    selected = mapping(option_generation_result.get("selected_option"))
    user_payload = mapping(mapping(proposal_shaping_payload.get("provider_request")).get("user_payload"))
    budget_context = mapping(user_payload.get("budget_context"))
    return {
        "overshoot_kcal": budget_context.get("overshoot_kcal"),
        "recommended_days": selected.get("recommended_days"),
        "daily_kcal_adjustment": selected.get("daily_kcal_adjustment"),
        "cap_mode": selected.get("cap_mode"),
        "effective_from": effective_from_policy.get("effective_from_posture"),
    }


def _provider_request(
    *,
    shaped_proposal: Mapping[str, Any],
    card_math: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "system_prompt": (
            "Return exactly one top-level JSON object for rescue response presentation. "
            "Use primary_actions exactly and set negotiation_affordance.not_primary_actions=true "
            "with the exact allowed_secondary_intents. Do not add shorten, extend, explain, "
            "schedule, delivery, save, commit, or mutation actions."
        ),
        "user_payload": {
            "target_surface": "rescue_response_presentation",
            "shaped_proposal": dict(shaped_proposal),
            "response_card_math": dict(card_math),
            "primary_actions_contract": list(PRIMARY_ACTIONS),
            "secondary_affordance_contract": list(SECONDARY_INTENTS),
            "output_contract": {
                "required_top_level_fields": list(REQUIRED_OUTPUT_FIELDS),
                "claim_scope_value": "lab_response_presentation_only",
                "primary_actions_must_equal": list(PRIMARY_ACTIONS),
                "secondary_intents_not_primary": list(SECONDARY_INTENTS),
            },
            "constraints": {
                "primary_actions_must_match_contract": True,
                "single_rescue_proposal_card_only": True,
                "backup_options_forbidden": True,
                "mainline_activation_enabled": False,
                "mutation_or_commit_allowed": False,
                "delivery_or_scheduler_allowed": False,
            },
        },
    }


def _input_blockers(
    shaping_payload: Mapping[str, Any],
    shaping_validation: Mapping[str, Any],
    option_result: Mapping[str, Any],
    effective_policy: Mapping[str, Any],
    shaped_proposal: Mapping[str, Any],
    card_math: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if shaping_payload.get("artifact_type") != "rescue_proposal_shaping_payload":
        blockers.append("proposal_shaping_payload.unsupported_artifact_type")
    if shaping_payload.get("status") != "pass":
        blockers.append("proposal_shaping_payload.status_not_pass")
    if shaping_validation.get("status") != "pass" or not shaped_proposal:
        blockers.append("proposal_shaping_validation.status_not_pass")
    if option_result.get("artifact_type") != "rescue_option_generation_result":
        blockers.append("option_generation_result.unsupported_artifact_type")
    if option_result.get("status") == "blocked":
        blockers.append("option_generation_result.status_blocked")
    if effective_policy.get("status") != "pass":
        blockers.append("effective_from_policy.status_not_pass")
    for field in CARD_MATH_FIELDS:
        if card_math.get(field) in (None, ""):
            blockers.append(f"card_math.{field}_missing")
    for flag in FALSE_OUTPUT_FLAGS:
        for name, packet in (
            ("proposal_shaping_payload", shaping_payload),
            ("proposal_shaping_validation", shaping_validation),
            ("option_generation_result", option_result),
            ("effective_from_policy", effective_policy),
        ):
            if packet.get(flag) is True:
                blockers.append(f"{name}.{flag}")
    return blockers


def _provider_contract(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_family": str(profile.get("provider_family") or ""),
        "diagnostic_live_model": "grok-4-fast",
        "target_reasoning_model": "kimi-k2.5",
        "provider_dependency_inversion_required": True,
        "provider_specific_product_semantics_allowed": False,
        "kimi_live_calls_allowed": False,
    }


def mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "FALSE_OUTPUT_FLAGS",
    "PRIMARY_ACTIONS",
    "SECONDARY_INTENTS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "STAGE",
    "build_rescue_response_presentation_payload",
    "mapping",
]
