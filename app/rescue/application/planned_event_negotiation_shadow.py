from math import ceil
from typing import Any, Mapping

from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.planned_event_negotiation_shadow"
)

PLANNED_EVENT_RESCUE_INTENT = "planned_event_budget_rescue"
FALSE_FIELD_NAMES = (
    "runtime_effect_allowed", "user_facing_behavior_changed",
    "budget_mutation_allowed", "proposal_committed",
    "rescue_committed", "day_budget_mutated",
    "body_plan_mutated", "meal_thread_mutated",
    "ledger_entry_created", "durable_memory_written",
    "manager_context_packet_changed", "manager_context_injected",
    "proactive_sent", "recommendation_served",
)
FALSE_FLAGS = dict.fromkeys(FALSE_FIELD_NAMES, False)


def build_planned_event_rescue_negotiation_shadow_packet(
    *,
    planned_event_context: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
    proposal_shaping_candidate: Mapping[str, Any],
) -> dict[str, Any]:
    allocation = deterministic_allocation(planned_event_context, active_body_plan_view)
    blockers = [
        *planned_event_blockers(planned_event_context),
        *view_blockers(current_budget_view, active_body_plan_view, open_proposals_view),
        *allocation_blockers(allocation),
        *candidate_blockers(proposal_shaping_candidate),
    ]
    proposal = None if blockers else proposal_candidate(proposal_shaping_candidate, planned_event_context)
    shaping_input = {} if blockers else proposal_shaping_input(allocation)
    return {
        "artifact_type": "rescue_planned_event_negotiation_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "future_planned_event_rescue_shadow_review",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "planned_event_context": sanitized_planned_event_context(planned_event_context),
        "deterministic_allocation": allocation,
        "proposal_candidate": proposal,
        "proposal_shaping_input_shadow": shaping_input,
        "explicit_accept_required": True,
        "blockers": blockers,
        "local_only": True,
        "diagnostic_only": True,
        "shadow_only": True,
        "non_claims": [
            "not_user_facing_response",
            "not_proposal_container_write",
            "not_budget_or_ledger_mutation",
            "not_scheduler_or_notification_delivery",
            "not_runtime_activation_evidence",
        ],
        **dict(FALSE_FLAGS),
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }


def planned_event_blockers(context: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if context.get("intent_kind") != PLANNED_EVENT_RESCUE_INTENT:
        blockers.append("planned_event_context.not_budget_rescue_intent")
    for field in ("event_id", "event_label", "event_local_date"):
        if not str(context.get(field) or "").strip():
            blockers.append(f"planned_event_context.{field}_missing")
    if int_value(context.get("reserve_kcal")) <= 0:
        blockers.append("planned_event_context.reserve_kcal_missing")
    if int_value(context.get("planning_days_before_event")) <= 0:
        blockers.append("planned_event_context.planning_days_before_event_missing")
    return blockers


def view_blockers(
    budget: Mapping[str, Any],
    body_plan: Mapping[str, Any],
    open_proposals: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if int_value(open_proposals.get("open_rescue_proposal_count")) > 0:
        blockers.append("open_proposals_view.open_rescue_proposal")
    for name, view in (("current_budget_view", budget), ("active_body_plan_view", body_plan)):
        for flag in FALSE_FLAGS:
            if view.get(flag) is True:
                blockers.append(f"{name}.{flag}")
    if not target_days(body_plan):
        blockers.append("active_body_plan_view.target_days_missing")
    return blockers


def deterministic_allocation(
    context: Mapping[str, Any],
    body_plan: Mapping[str, Any],
) -> dict[str, Any]:
    reserve = int_value(context.get("reserve_kcal"))
    days = min(int_value(context.get("planning_days_before_event")), len(target_days(body_plan)))
    daily = ceil(reserve / days) if reserve > 0 and days > 0 else 0
    floor_kcal = int_value(body_plan.get("safety_floor_kcal"))
    checks = [day_check(day, daily, floor_kcal) for day in target_days(body_plan)[:days]]
    return {
        "reserve_kcal": reserve,
        "planning_days": days,
        "daily_kcal_adjustment": -daily if daily else None,
        "cap_mode": "planned_event_pre_allocation",
        "target_day_checks": checks,
        "source_refs": source_refs(context),
    }


def allocation_blockers(allocation: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if int_value(allocation.get("reserve_kcal")) <= 0:
        blockers.append("deterministic_allocation.reserve_kcal_missing")
    if int_value(allocation.get("planning_days")) <= 0:
        blockers.append("deterministic_allocation.planning_days_missing")
    for check in allocation.get("target_day_checks") or []:
        if isinstance(check, Mapping) and check.get("safety_floor_passed") is False:
            blockers.append("deterministic_allocation.below_safety_floor")
        if isinstance(check, Mapping) and check.get("compression_within_15_percent") is False:
            blockers.append("deterministic_allocation.daily_compression_above_15_percent")
    return list(dict.fromkeys(blockers))


def candidate_blockers(candidate: Mapping[str, Any]) -> list[str]:
    blockers = [
        f"proposal_shaping_candidate.{flag}"
        for flag in FALSE_FIELD_NAMES
        if candidate.get(flag) is True
    ]
    if not str(candidate.get("headline") or "").strip():
        blockers.append("proposal_shaping_candidate.headline_missing")
    if not str(candidate.get("summary") or "").strip():
        blockers.append("proposal_shaping_candidate.summary_missing")
    actions = candidate.get("primary_actions")
    if actions != ["accept_rescue_plan", "dismiss_rescue_plan"]:
        blockers.append("proposal_shaping_candidate.primary_actions_invalid")
    return blockers


def proposal_candidate(
    candidate: Mapping[str, Any],
    context: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "headline": str(candidate.get("headline") or ""),
        "summary": str(candidate.get("summary") or ""),
        "primary_actions": list(candidate.get("primary_actions") or []),
        "source_refs": source_refs(context),
    }


def proposal_shaping_input(allocation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": "rescue_proposal_shaping_input_shadow_packet",
        "status": "pass",
        "shaping_input_envelope": {
            "deterministic_option": {
                "recommended_days": allocation.get("planning_days"),
                "daily_kcal_adjustment": allocation.get("daily_kcal_adjustment"),
                "cap_mode": allocation.get("cap_mode"),
                "special_posture": "planned_event_pre_allocation",
            },
        },
        **dict(FALSE_FLAGS),
        "live_llm_invoked": False,
        "provider_called": False,
    }


def sanitized_planned_event_context(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(context.get("event_id") or ""),
        "intent_kind": str(context.get("intent_kind") or ""),
        "event_label": str(context.get("event_label") or ""),
        "event_local_date": str(context.get("event_local_date") or ""),
        "reserve_kcal": int_value(context.get("reserve_kcal")),
        "planning_days_before_event": int_value(context.get("planning_days_before_event")),
        "source_refs": source_refs(context),
    }


def day_check(day: Mapping[str, Any], daily: int, safety_floor: int) -> dict[str, Any]:
    base = int_value(day.get("base_budget_kcal"))
    return {
        "local_date": str(day.get("local_date") or ""),
        "base_budget_kcal": base,
        "proposed_rescue_overlay_kcal": -daily,
        "candidate_effective_budget_kcal": base - daily,
        "safety_floor_kcal": safety_floor,
        "compression_within_15_percent": daily <= int(base * 0.15),
        "safety_floor_passed": base - daily >= safety_floor,
    }


def target_days(view: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = view.get("target_days")
    return [item for item in value if isinstance(item, Mapping)] if isinstance(value, list) else []


def source_refs(context: Mapping[str, Any]) -> list[str]:
    return [
        str(ref)
        for ref in context.get("source_refs") or []
        if str(ref).startswith("planned_event:")
    ]


def int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0
