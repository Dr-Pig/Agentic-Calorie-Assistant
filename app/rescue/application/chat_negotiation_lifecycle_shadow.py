from __future__ import annotations

from typing import Any, Mapping

from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.chat_negotiation_lifecycle_shadow"
)
OPTION_ARTIFACT = "rescue_option_generation_shadow_packet"
SUPPORTED_INTENTS = {
    "present",
    "accept",
    "dismiss",
    "complaint_only",
    "request_shorter",
    "request_gentler",
    "ask_why",
}
FALSE_FLAGS = {
    "runtime_effect_allowed": False,
    "user_facing_behavior_changed": False,
    "proposal_committed": False,
    "rescue_committed": False,
    "ledger_entry_created": False,
    "day_budget_mutated": False,
    "body_plan_mutated": False,
    "meal_thread_mutated": False,
    "durable_memory_written": False,
    "manager_context_packet_changed": False,
    "manager_context_injected": False,
    "proactive_sent": False,
    "recommendation_served": False,
}
OPTION_DRIFT_FLAGS = tuple(FALSE_FLAGS)


def build_rescue_chat_negotiation_lifecycle_shadow(
    *,
    option_generation_shadow_packet: Mapping[str, Any],
    interaction_intent: str = "present",
) -> dict[str, Any]:
    blockers = [
        *_option_blockers(option_generation_shadow_packet),
        *_intent_blockers(interaction_intent),
    ]
    lifecycle = _lifecycle(interaction_intent)
    return {
        "artifact_type": "rescue_chat_negotiation_lifecycle_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "future_same_day_rescue_chat_runtime_activation_review",
        "retirement_trigger": "approved_rescue_chat_negotiation_runtime_activation",
        "lifecycle_state": "blocked" if blockers else lifecycle["state"],
        "proposal_card": None
        if blockers
        else _proposal_card(option_generation_shadow_packet),
        "primary_actions": [] if blockers else _primary_actions(),
        "negotiation_affordances": [] if blockers else _negotiation_affordances(),
        "interaction_intent": interaction_intent,
        "interaction_intent_source": "bounded_lab_fixture_not_raw_text",
        "semantic_interaction_owner": "future_llm_or_human_confirmation",
        "negotiation_intent": lifecycle["negotiation_intent"],
        "next_shadow_step": lifecycle["next_shadow_step"],
        "explicit_accept_required": True,
        "explicit_accept_detected": lifecycle["explicit_accept_detected"],
        "dismiss_requested": lifecycle["dismiss_requested"],
        "commit_effect_requested": False,
        "permanent_rescue_suppression": False,
        "snooze_created": False,
        "blockers": blockers,
        "non_claims": [
            "not_user_facing_response",
            "not_proposal_container_write",
            "not_rescue_commit",
            "not_scheduler_or_notification_delivery",
            "not_raw_text_semantic_router",
        ],
        **dict(FALSE_FLAGS),
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def _option_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != OPTION_ARTIFACT:
        blockers.append("option_generation_shadow_packet.unsupported_artifact_type")
    if packet.get("status") != "pass":
        blockers.append("option_generation_shadow_packet.status_not_pass")
    if packet.get("rescue_needed") is not True:
        blockers.append("option_generation_shadow_packet.rescue_needed_not_true")
    for field in ("recommended_days", "daily_kcal_adjustment", "cap_mode"):
        if packet.get(field) in (None, ""):
            blockers.append(f"option_generation_shadow_packet.{field}_missing")
    for flag in OPTION_DRIFT_FLAGS:
        if packet.get(flag) is True:
            blockers.append(f"option_generation_shadow_packet.{flag}")
    return blockers


def _intent_blockers(interaction_intent: str) -> list[str]:
    return [] if interaction_intent in SUPPORTED_INTENTS else ["interaction_intent.unsupported"]


def _proposal_card(packet: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "card_kind": "same_day_rescue_shadow",
        "default_surface": "chat_primary",
        "recommended_days": packet.get("recommended_days"),
        "daily_kcal_adjustment": packet.get("daily_kcal_adjustment"),
        "cap_mode": packet.get("cap_mode"),
        "special_posture": packet.get("special_posture"),
        "guardrail_notes": list(packet.get("guardrail_notes") or []),
        "stored_action_required_before_commit": True,
        "raw_text_authorized_mutation": False,
    }


def _primary_actions() -> list[dict[str, str]]:
    return [
        {"action_id": "accept_rescue_plan", "effect": "accepted_shadow_only"},
        {"action_id": "dismiss_rescue_plan", "effect": "dismissed_shadow_only"},
    ]


def _negotiation_affordances() -> list[str]:
    return [
        "request_shorter_more_aggressive",
        "request_longer_gentler",
        "ask_why_this_plan",
    ]


def _lifecycle(interaction_intent: str) -> dict[str, Any]:
    if interaction_intent == "accept":
        return _state("accepted_shadow", accept=True, next_step="review_commit_effect_without_applying")
    if interaction_intent == "dismiss":
        return _state("dismissed_shadow", dismiss=True, next_step="hide_current_shadow_instance")
    if interaction_intent == "complaint_only":
        return _state(
            "negotiating",
            negotiation_intent="complaint_or_hardness_feedback",
            next_step="ask_or_offer_adjustment_without_state_mutation",
        )
    if interaction_intent in {"request_shorter", "request_gentler", "ask_why"}:
        return _state(
            "negotiating",
            negotiation_intent=interaction_intent,
            next_step="generate_alternative_or_explanation_shadow",
        )
    return _state("presented", next_step="wait_for_explicit_accept_dismiss_or_negotiation")


def _state(
    state: str,
    *,
    negotiation_intent: str = "not_applicable",
    next_step: str,
    accept: bool = False,
    dismiss: bool = False,
) -> dict[str, Any]:
    return {
        "state": state,
        "negotiation_intent": negotiation_intent,
        "next_shadow_step": next_step,
        "explicit_accept_detected": accept,
        "dismiss_requested": dismiss,
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_chat_negotiation_lifecycle_shadow",
]
