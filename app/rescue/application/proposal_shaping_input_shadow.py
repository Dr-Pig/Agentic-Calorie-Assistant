from __future__ import annotations

from typing import Any, Mapping

from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.proposal_shaping_input_shadow"
)
OPTION_ARTIFACT = "rescue_option_generation_shadow_packet"
FALSE_INPUT_FLAGS = (
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
    "ledger_entry_created",
    "runtime_effect_allowed",
)
FORBIDDEN_OUTPUT_FIELDS = (
    "proposal_card",
    "proposal_headline",
    "proposal_summary",
    "coaching_frame",
    "quick_action_posture",
    "candidate_copy",
    "send_or_skip",
    "primary_actions",
)
CONTEXT_AUTHORITY_FLAGS = (
    "runtime_effect_allowed",
    "runtime_truth_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
    "proposal_committed",
    "rescue_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "ledger_entry_created",
    "proactive_sent",
    "recommendation_served",
)
CONTEXT_ALLOWED_FIELDS = {
    "budget_context": {"current_date", "overshoot_kcal", "remaining_budget_kcal"},
    "body_plan_context": {"safety_floor_kcal", "target_days_count", "sex"},
    "rescue_history_context": {
        "recent_rescue_count",
        "summary",
        "rescue_viability_posture",
    },
    "suppression_context": {"trigger_type", "summary"},
}


def build_rescue_proposal_shaping_input_shadow_packet(
    *,
    option_generation_shadow_packet: Mapping[str, Any],
    budget_context: Mapping[str, Any] | None = None,
    body_plan_context: Mapping[str, Any] | None = None,
    rescue_history_context: Mapping[str, Any] | None = None,
    suppression_context: list[Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    context_blockers = _context_blockers(
        budget_context=budget_context,
        body_plan_context=body_plan_context,
        rescue_history_context=rescue_history_context,
        suppression_context=suppression_context,
    )
    blockers = [
        *_input_blockers(option_generation_shadow_packet),
        *context_blockers,
    ]
    return {
        "artifact_type": "rescue_proposal_shaping_input_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "future_rescue_proposal_shaping_llm_contract",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "option_generation_shadow_packet_used": not blockers,
        "llm_role": "future_proposal_framing_only",
        "deterministic_role": "validate_input_and_forbid_runtime_effects",
        "shaping_input_envelope": {}
        if blockers
        else {
            "deterministic_option": _deterministic_option(option_generation_shadow_packet),
            "review_context": {
                "budget_context": _sanitized_mapping("budget_context", budget_context),
                "body_plan_context": _sanitized_mapping("body_plan_context", body_plan_context),
                "rescue_history_context": _sanitized_mapping("rescue_history_context", rescue_history_context),
                "suppression_context": [
                    _sanitized_mapping("suppression_context", item)
                    for item in (suppression_context or [])
                ],
            },
        },
        "forbidden_output_fields": list(FORBIDDEN_OUTPUT_FIELDS),
        "blockers": blockers,
        "proposal_card": None,
        "proposal_headline": None,
        "proposal_summary": None,
        "coaching_frame": None,
        "quick_action_posture": None,
        "candidate_copy": None,
        "send_or_skip": None,
        "primary_actions": [],
        "runtime_effect_allowed": False,
        "live_llm_invoked": False,
        "provider_called": False,
        "recommendation_posture_updated": False,
        "ledger_entry_created": False,
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def _input_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != OPTION_ARTIFACT:
        blockers.append("option_generation_shadow_packet.unsupported_artifact_type")
    if packet.get("status") == "blocked":
        blockers.append("option_generation_shadow_packet.status_blocked")
    for flag in FALSE_INPUT_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"option_generation_shadow_packet.{flag}")
    for field in FORBIDDEN_OUTPUT_FIELDS:
        value = packet.get(field)
        if value not in (None, [], {}):
            blockers.append(f"option_generation_shadow_packet.{field}")
    return blockers


def _context_blockers(
    *,
    budget_context: Mapping[str, Any] | None,
    body_plan_context: Mapping[str, Any] | None,
    rescue_history_context: Mapping[str, Any] | None,
    suppression_context: list[Mapping[str, Any]] | None,
) -> list[str]:
    blockers = [
        *_authority_blockers("budget_context", budget_context),
        *_authority_blockers("body_plan_context", body_plan_context),
        *_authority_blockers("rescue_history_context", rescue_history_context),
    ]
    for index, item in enumerate(suppression_context or []):
        blockers.extend(_authority_blockers(f"suppression_context[{index}]", item))
    return blockers


def _authority_blockers(name: str, value: Mapping[str, Any] | None) -> list[str]:
    if value is None:
        return []
    return [
        f"{name}.{flag}"
        for flag in CONTEXT_AUTHORITY_FLAGS
        if value.get(flag) is True
    ]


def _sanitized_mapping(
    context_name: str,
    value: Mapping[str, Any] | None,
) -> dict[str, Any]:
    if value is None:
        return {}
    allowed = CONTEXT_ALLOWED_FIELDS[context_name]
    return {key: value[key] for key in allowed if key in value}


def _deterministic_option(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recommended_days": packet.get("recommended_days"),
        "daily_kcal_adjustment": packet.get("daily_kcal_adjustment"),
        "cap_mode": packet.get("cap_mode"),
        "special_posture": packet.get("special_posture"),
        "recovery_viability": packet.get("recovery_viability"),
        "guardrail_notes": list(packet.get("guardrail_notes") or []),
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_proposal_shaping_input_shadow_packet",
]
