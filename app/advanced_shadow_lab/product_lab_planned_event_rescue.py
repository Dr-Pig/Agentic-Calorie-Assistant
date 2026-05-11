from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_rescue_handoff import (
    build_pending_rescue_commit_packet,
)
from app.rescue.application.planned_event_negotiation_shadow import (
    build_planned_event_rescue_negotiation_shadow_packet,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_planned_event_rescue"
)
ARTIFACT_TYPE = "advanced_product_lab_planned_event_rescue_runtime_artifact"
PRIMARY_ACTIONS = ["accept_rescue_plan", "dismiss_rescue_plan"]
NEGOTIATION_AFFORDANCES = [
    "request_gentler_plan",
    "request_shorter_plan",
    "ask_why_this_plan",
]


def run_product_lab_planned_event_rescue(
    *,
    fixture_inputs: Mapping[str, Any],
    enabled: bool = False,
) -> dict[str, Any]:
    if not enabled:
        return _not_applicable()
    shadow = build_planned_event_rescue_negotiation_shadow_packet(
        planned_event_context=_mapping(fixture_inputs.get("planned_event_context")),
        current_budget_view=_mapping(fixture_inputs.get("current_budget_view")),
        active_body_plan_view=_mapping(fixture_inputs.get("active_body_plan_view")),
        open_proposals_view=_mapping(fixture_inputs.get("open_proposals_view")),
        proposal_shaping_candidate=_mapping(
            fixture_inputs.get("planned_event_proposal_candidate")
        ),
    )
    blockers = _blockers("planned_event_shadow", shadow)
    proposal_card = {} if blockers else _proposal_card(shadow)
    lifecycle_packets = [] if blockers else _lifecycle_packets()
    pending_commit = build_pending_rescue_commit_packet(
        proposal_card=proposal_card,
        primary_actions=PRIMARY_ACTIONS if proposal_card else [],
        lifecycle_packets=lifecycle_packets,
    )
    blockers.extend(_blockers("pending_rescue_commit", pending_commit))
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "source_shadow_packet_status": str(shadow.get("status") or ""),
        "planned_event_shadow_packet": dict(shadow),
        "proposal_card": proposal_card,
        "guardrail_math": _guardrail_math(shadow),
        "primary_actions": PRIMARY_ACTIONS if proposal_card else [],
        "negotiation_affordances": NEGOTIATION_AFFORDANCES if proposal_card else [],
        "lifecycle_packets": lifecycle_packets,
        "pending_rescue_commit_packet": pending_commit,
        "proposal_presented_to_lab": not bool(blockers),
        "future_overlay_preview_only": True,
        "chat_first": True,
        "canonical_commit_requested": False,
        "proposal_committed": False,
        "rescue_committed": False,
        "ledger_entry_created": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "served_to_mainline_user": False,
        "mainline_activation_enabled": False,
        "self_use_v1_affected": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _proposal_card(shadow: Mapping[str, Any]) -> dict[str, Any]:
    context = _mapping(shadow.get("planned_event_context"))
    allocation = _mapping(shadow.get("deterministic_allocation"))
    candidate = _mapping(shadow.get("proposal_candidate"))
    return {
        "card_kind": "planned_event_rescue_lab",
        "default_surface": "chat",
        "event_id": str(context.get("event_id") or ""),
        "event_label": str(context.get("event_label") or ""),
        "event_local_date": str(context.get("event_local_date") or ""),
        "reserve_kcal": _int(allocation.get("reserve_kcal")),
        "recommended_days": _int(allocation.get("planning_days")),
        "daily_kcal_adjustment": _int(allocation.get("daily_kcal_adjustment")),
        "cap_mode": str(allocation.get("cap_mode") or ""),
        "special_posture": "planned_event_pre_allocation",
        "headline": str(candidate.get("headline") or ""),
        "summary": str(candidate.get("summary") or ""),
        "overlay_preview_rows": [
            dict(row)
            for row in allocation.get("target_day_checks") or []
            if isinstance(row, Mapping)
        ],
        "source_refs": [str(ref) for ref in candidate.get("source_refs") or []],
    }


def _guardrail_math(shadow: Mapping[str, Any]) -> dict[str, Any]:
    allocation = _mapping(shadow.get("deterministic_allocation"))
    return {
        "reserve_kcal": _int(allocation.get("reserve_kcal")),
        "recommended_days": _int(allocation.get("planning_days")),
        "daily_kcal_adjustment": _int(allocation.get("daily_kcal_adjustment")),
        "cap_mode": str(allocation.get("cap_mode") or ""),
        "target_day_checks": [
            dict(row)
            for row in allocation.get("target_day_checks") or []
            if isinstance(row, Mapping)
        ],
        "future_overlay_preview_only": True,
    }


def _lifecycle_packets() -> list[dict[str, Any]]:
    return [
        _lifecycle("present", "presented_lab", "await_explicit_accept_or_dismiss"),
        _lifecycle("accept", "accepted_lab_pending_explicit_commit", "await_commit"),
        _lifecycle("dismiss", "dismissed_lab", "hide_current_instance"),
    ]


def _lifecycle(intent: str, state: str, next_step: str) -> dict[str, Any]:
    return {
        "interaction_intent": intent,
        "source_lifecycle_state": state.replace("_lab", ""),
        "lab_lifecycle_state": state,
        "next_lab_step": next_step,
        "explicit_accept_required": True,
        "canonical_commit_requested": False,
        "served_to_mainline_user": False,
    }


def _not_applicable() -> dict[str, Any]:
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": "not_applicable",
        "proposal_presented_to_lab": False,
        "blockers": [],
        **dict(FALSE_FLAGS),
    }


def _blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    if artifact.get("status") == "pass":
        return []
    blockers = [f"{prefix}.status_{artifact.get('status') or 'missing'}"]
    blockers.extend(f"{prefix}.{blocker}" for blocker in artifact.get("blockers") or [])
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "run_product_lab_planned_event_rescue"]
