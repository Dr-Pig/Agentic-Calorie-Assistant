from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.model_profiles import (
    ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
    resolve_advanced_lab_model_profile,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_contracts"
)
STAGE = "rescue_phase1_proposal_shaping"
FLOW_ARTIFACT = "reactive_rescue_independent_message_flow"
OPTION_ARTIFACT = "rescue_option_generation_result"
COPY_FIELDS = ("proposal_headline", "proposal_summary", "coaching_frame")
DETERMINISTIC_FIELDS = (
    "recommended_days",
    "daily_kcal_adjustment",
    "cap_mode",
    "special_posture",
)
FORBIDDEN_AUTHORITY_FIELDS = (
    "proposal_id",
    "container_id",
    "proposal_card",
    "primary_actions",
    "accept_rescue_plan",
    "dismiss_rescue_plan",
    "commit",
    "scheduler_trigger",
    "route_target",
    "ledger_entry",
)
FALSE_INPUT_FLAGS = (
    "runtime_effect_allowed",
    "canonical_mutation_changed",
    "production_scheduler_delivery_allowed",
    "ledger_entry_created",
    "proposal_committed",
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
REQUIRED_OUTPUT_FIELDS = [
    "proposal_headline",
    "proposal_summary",
    "coaching_frame",
    "quick_action_posture",
    "claim_scope",
    "action_request",
    "delivery_request",
    "mutation_request",
    "reason_codes",
]
FORBIDDEN_NESTED_OUTPUT_KEYS = ["proposal_shaping", "proposal", "result"]


def build_rescue_proposal_shaping_payload(
    *,
    independent_message_flow: Mapping[str, Any],
    option_generation_result: Mapping[str, Any],
    budget_context: Mapping[str, Any] | None = None,
    rescue_history_context: Mapping[str, Any] | None = None,
    provider_profile_id: str = ADVANCED_LAB_DIAGNOSTIC_PROFILE_ID,
) -> dict[str, Any]:
    profile = resolve_advanced_lab_model_profile(provider_profile_id)
    option = _deterministic_option(option_generation_result)
    blockers = _input_blockers(independent_message_flow, option_generation_result, option)
    return {
        "artifact_type": "rescue_proposal_shaping_payload",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "rescue_response_presentation",
        "stage": STAGE,
        "decision_mode": "llm_copy_with_deterministic_guard",
        "provider_profile_id": provider_profile_id,
        "provider_contract": _provider_contract(profile),
        "provider_request": {}
        if blockers
        else _provider_request(
            message_flow=independent_message_flow,
            deterministic_option=option,
            budget_context=budget_context,
            rescue_history_context=rescue_history_context,
        ),
        "deterministic_option": option,
        "forbidden_authority_fields": list(FORBIDDEN_AUTHORITY_FIELDS),
        "blockers": blockers,
        "lab_user_facing_surface_allowed": not blockers,
        "live_llm_invoked": False,
        "provider_called": False,
        **dict(FALSE_OUTPUT_FLAGS),
    }


def _provider_contract(profile: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "provider_family": str(profile.get("provider_family") or ""),
        "diagnostic_live_model": "grok-4-fast",
        "target_reasoning_model": "kimi-k2.5",
        "provider_dependency_inversion_required": True,
        "provider_specific_product_semantics_allowed": False,
        "kimi_live_calls_allowed": False,
    }


def _provider_request(
    *,
    message_flow: Mapping[str, Any],
    deterministic_option: Mapping[str, Any],
    budget_context: Mapping[str, Any] | None,
    rescue_history_context: Mapping[str, Any] | None,
) -> dict[str, Any]:
    message = mapping(message_flow.get("independent_message"))
    return {
        "system_prompt": (
            "Return exactly one top-level JSON object for rescue proposal shaping. "
            "Do not wrap the answer under proposal_shaping, proposal, result, or any "
            "other container key. You may write lab user-facing proposal copy, but "
            "you must not recalculate math, select primary actions, commit, save, "
            "schedule, deliver, or mutate state."
        ),
        "user_payload": {
            "target_surface": "rescue_proposal_shaping",
            "source_message_id": str(message.get("message_id") or ""),
            "deterministic_option": dict(deterministic_option),
            "budget_context": _allowed(budget_context, {"local_date", "overshoot_kcal"}),
            "rescue_history_context": _allowed(rescue_history_context, {"recent_rescue_count", "summary"}),
            "output_contract": {
                "required_top_level_fields": list(REQUIRED_OUTPUT_FIELDS),
                "nested_container_keys_forbidden": list(FORBIDDEN_NESTED_OUTPUT_KEYS),
                "claim_scope_value": "lab_proposal_shaping_only",
                "boolean_false_fields": [
                    "action_request",
                    "delivery_request",
                    "mutation_request",
                ],
            },
            "constraints": {
                "claim_scope_required": "lab_proposal_shaping_only",
                "lab_user_facing_output_allowed": True,
                "mainline_activation_enabled": False,
                "delivery_or_scheduler_allowed": False,
                "mutation_or_commit_allowed": False,
                "primary_actions_owned_by_response_presentation": True,
            },
        },
    }


def _input_blockers(
    flow: Mapping[str, Any],
    option_result: Mapping[str, Any],
    option: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if flow.get("artifact_type") != FLOW_ARTIFACT:
        blockers.append("independent_message_flow.unsupported_artifact_type")
    if flow.get("status") == "blocked" or flow.get("rescue_message_created") is not True:
        blockers.append("independent_message_flow.message_not_created")
    if option_result.get("artifact_type") != OPTION_ARTIFACT:
        blockers.append("option_generation_result.unsupported_artifact_type")
    if option_result.get("status") == "blocked":
        blockers.append("option_generation_result.status_blocked")
    if not option:
        blockers.append("option_generation_result.missing_deterministic_option")
    for flag in FALSE_INPUT_FLAGS:
        if flow.get(flag) is True:
            blockers.append(f"independent_message_flow.{flag}")
        if option_result.get(flag) is True:
            blockers.append(f"option_generation_result.{flag}")
    return blockers


def _deterministic_option(option_result: Mapping[str, Any]) -> dict[str, Any]:
    selected = mapping(option_result.get("selected_option"))
    return {field: selected.get(field) for field in DETERMINISTIC_FIELDS if field in selected}


def _allowed(value: Mapping[str, Any] | None, keys: set[str]) -> dict[str, Any]:
    return {key: value[key] for key in keys if value is not None and key in value}


def mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, Mapping) else {}


__all__ = [
    "COPY_FIELDS",
    "DETERMINISTIC_FIELDS",
    "FALSE_OUTPUT_FLAGS",
    "FORBIDDEN_AUTHORITY_FIELDS",
    "SIDECAR_ACTIVATION_CONTRACT",
    "STAGE",
    "build_rescue_proposal_shaping_payload",
    "mapping",
]
