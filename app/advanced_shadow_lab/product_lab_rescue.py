from __future__ import annotations

from typing import Any, Mapping

from app.rescue.application.chain_lifecycle_adapter import (
    build_rescue_chain_lifecycle_shadow_packets,
)
from app.rescue.application.shadow_chain_runner import run_rescue_shadow_chain
from app.advanced_shadow_lab.product_lab_rescue_handoff import (
    build_pending_rescue_commit_packet,
)


LAB_INTERACTION_INTENTS = ["present", "accept", "dismiss", "request_gentler"]


def run_product_lab_rescue(
    *,
    fixture_inputs: Mapping[str, Any],
) -> dict[str, Any]:
    chain = run_rescue_shadow_chain(
        memory_summary_projection=_mapping(fixture_inputs.get("memory_summary_projection")),
        derived_memory_views=_mapping(fixture_inputs.get("derived_memory_views")),
        current_budget_view=_mapping(fixture_inputs.get("current_budget_view")),
        active_body_plan_view=_mapping(fixture_inputs.get("active_body_plan_view")),
        open_proposals_view=_mapping(fixture_inputs.get("open_proposals_view")),
        proposal_candidate_output=_mapping(fixture_inputs.get("proposal_candidate_output")),
    )
    lifecycle = build_rescue_chain_lifecycle_shadow_packets(
        rescue_shadow_chain_artifact=chain,
        interaction_intents=list(LAB_INTERACTION_INTENTS),
    )
    blockers = [
        *_blockers("rescue_chain", chain),
        *_blockers("rescue_lifecycle", lifecycle),
    ]
    option = _option_stage(chain)
    proposal_card = {} if blockers else _proposal_card(option)
    primary_actions = [] if blockers else _primary_actions()
    lifecycle_packets = [] if blockers else _lab_lifecycle_packets(lifecycle)
    pending_commit = build_pending_rescue_commit_packet(
        proposal_card=proposal_card,
        primary_actions=primary_actions,
        lifecycle_packets=lifecycle_packets,
    )
    blockers.extend(_blockers("pending_rescue_commit", pending_commit))
    return {
        "artifact_type": "advanced_product_lab_rescue_runtime_artifact",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "source_shadow_chain_status": str(chain.get("status") or ""),
        "source_lifecycle_status": str(lifecycle.get("status") or ""),
        "proposal_card": proposal_card,
        "guardrail_math": _guardrail_math(option),
        "primary_actions": primary_actions,
        "lifecycle_packets": lifecycle_packets,
        "pending_rescue_commit_packet": pending_commit,
        "proposal_presented_to_lab": not bool(blockers),
        "rescue_lifecycle_enabled": not bool(blockers),
        "rescue_intent_state_created": pending_commit.get("status") == "pass",
        "chat_first": True,
        "canonical_commit_requested": False,
        "proposal_committed": False,
        "rescue_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "served_to_mainline_user": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "blockers": blockers,
    }


def _proposal_card(option: Mapping[str, Any]) -> dict[str, Any]:
    days = _int(option.get("recommended_days"))
    kcal = _int(option.get("daily_kcal_adjustment"))
    return {
        "card_kind": "same_day_rescue_lab",
        "default_surface": "chat",
        "recommended_days": days,
        "daily_kcal_adjustment": kcal,
        "cap_mode": str(option.get("cap_mode") or ""),
        "special_posture": str(option.get("special_posture") or ""),
        "headline": f"Smooth today over {days} days.",
        "summary": (
            f"Shift {abs(kcal)} kcal per day while keeping the safety floor intact."
        ),
    }


def _guardrail_math(option: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "rescue_needed": option.get("rescue_needed") is True,
        "recovery_viability": str(option.get("recovery_viability") or ""),
        "recommended_days": _int(option.get("recommended_days")),
        "daily_kcal_adjustment": _int(option.get("daily_kcal_adjustment")),
        "guardrail_notes": [str(item) for item in option.get("guardrail_notes") or []],
    }


def _lab_lifecycle_packets(lifecycle: Mapping[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "interaction_intent": str(packet.get("interaction_intent") or ""),
            "source_lifecycle_state": str(packet.get("lifecycle_state") or ""),
            "lab_lifecycle_state": _lab_state(packet),
            "next_lab_step": str(packet.get("next_shadow_step") or ""),
            "explicit_accept_required": packet.get("explicit_accept_required") is True,
            "canonical_commit_requested": False,
            "served_to_mainline_user": False,
        }
        for packet in lifecycle.get("lifecycle_packets") or []
        if isinstance(packet, Mapping)
    ]


def _lab_state(packet: Mapping[str, Any]) -> str:
    intent = str(packet.get("interaction_intent") or "")
    state = str(packet.get("lifecycle_state") or "")
    if state == "presented":
        return "presented_lab"
    if state == "accepted_shadow":
        return "accepted_lab_pending_explicit_commit"
    if state == "dismissed_shadow":
        return "dismissed_lab"
    if intent == "request_gentler":
        return "gentler_requested_lab"
    return f"{state}_lab"


def _primary_actions() -> list[str]:
    return [
        "accept_rescue_plan",
        "dismiss_rescue_plan",
        "request_gentler_plan",
        "ask_why_this_plan",
    ]


def _option_stage(chain: Mapping[str, Any]) -> Mapping[str, Any]:
    for stage in chain.get("stage_artifacts") or []:
        if (
            isinstance(stage, Mapping)
            and stage.get("artifact_type") == "rescue_option_generation_shadow_packet"
        ):
            return stage
    return {}


def _blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    status = str(artifact.get("status") or "")
    blockers = [f"{prefix}.status_{status}"] if status != "pass" else []
    blockers.extend(f"{prefix}.{blocker}" for blocker in artifact.get("blockers") or [])
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["run_product_lab_rescue"]
