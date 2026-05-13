from __future__ import annotations

from math import ceil, floor
from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.planned_event_budget_allocation"
)
READ_MODEL_PACKET_ARTIFACT = "rescue_read_model_input_packet"
CAP_FRACTION = 0.15


def build_planned_event_budget_allocation(
    *,
    planned_event_context: Mapping[str, Any],
    read_model_input_packet: Mapping[str, Any],
) -> dict[str, Any]:
    allocation = _allocation(planned_event_context, read_model_input_packet)
    checks = _target_day_checks(allocation, read_model_input_packet)
    blockers = [
        *_context_blockers(planned_event_context),
        *_read_model_blockers(read_model_input_packet),
        *_allocation_blockers(allocation, checks),
    ]
    return {
        "artifact_type": "planned_event_budget_allocation_result",
        "status": "blocked" if blockers else "pass",
        "owner": "app/rescue",
        "consumer": "planned_event_proposal_shaping",
        "decision_mode": "deterministic",
        "proposal_kind": "planned_event_budget_allocation",
        "planned_event_context": _sanitized_event(planned_event_context),
        "deterministic_allocation": allocation,
        "target_day_checks": checks,
        "proposal_shaping_seed": _proposal_shaping_seed(allocation),
        "confirmation_required": True,
        "proposal_commit_allowed": False,
        "blockers": blockers,
        "ledger_entry_created": False,
        "runtime_effect_allowed": False,
        "canonical_mutation_changed": False,
        "production_scheduler_delivery_allowed": False,
        "manager_context_packet_changed_in_mainline": False,
        "durable_product_memory_written_in_mainline": False,
    }


def _allocation(
    context: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> dict[str, Any]:
    days = min(_int(context.get("planning_days_before_event")), len(_target_days(packet)))
    reserve = _int(context.get("reserve_kcal"))
    daily = ceil(reserve / days) if reserve > 0 and days > 0 else 0
    return {
        "reserve_kcal": reserve,
        "planning_days": days,
        "daily_kcal_adjustment": -daily if daily else None,
        "cap_mode": "planned_event_pre_allocation",
        "target_day_count": days,
    }


def _target_day_checks(
    allocation: Mapping[str, Any],
    packet: Mapping[str, Any],
) -> list[dict[str, Any]]:
    daily = abs(_int(allocation.get("daily_kcal_adjustment")))
    floor_kcal = _int(_mapping(packet.get("active_body_plan_view")).get("safety_floor_kcal"))
    checks = []
    for day in _target_days(packet)[: _int(allocation.get("planning_days"))]:
        base = _int(day.get("base_budget_kcal"))
        calibration = _int(day.get("calibration_adjustment_total_kcal"))
        candidate = base + calibration - daily
        checks.append(
            {
                "local_date": str(day.get("local_date") or ""),
                "base_budget_kcal": base,
                "calibration_adjustment_total_kcal": calibration,
                "proposed_rescue_overlay_kcal": -daily,
                "candidate_effective_budget_kcal": candidate,
                "safety_floor_kcal": floor_kcal,
                "safety_floor_passed": candidate >= floor_kcal,
                "compression_within_15_percent": daily <= floor(base * CAP_FRACTION),
            }
        )
    return checks


def _context_blockers(context: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for field in ("event_id", "event_label", "event_local_date"):
        if not str(context.get(field) or "").strip():
            blockers.append(f"planned_event_context.{field}_missing")
    if _int(context.get("reserve_kcal")) <= 0:
        blockers.append("planned_event_context.reserve_kcal_missing")
    if _int(context.get("planning_days_before_event")) <= 0:
        blockers.append("planned_event_context.planning_days_before_event_missing")
    return blockers


def _read_model_blockers(packet: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if packet.get("artifact_type") != READ_MODEL_PACKET_ARTIFACT:
        blockers.append("read_model_input_packet.unsupported_artifact_type")
    if packet.get("status") == "blocked":
        blockers.append("read_model_input_packet.status_blocked")
    open_proposals = _mapping(packet.get("open_proposals_view"))
    if _int(open_proposals.get("open_rescue_proposal_count")) > 0:
        blockers.append("open_proposals_view.open_rescue_proposal")
    if not _target_days(packet):
        blockers.append("active_body_plan_view.target_days_missing")
    return blockers


def _allocation_blockers(
    allocation: Mapping[str, Any],
    checks: list[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if _int(allocation.get("reserve_kcal")) <= 0:
        blockers.append("allocation.reserve_kcal_missing")
    if _int(allocation.get("planning_days")) <= 0:
        blockers.append("allocation.planning_days_missing")
    if any(check.get("safety_floor_passed") is False for check in checks):
        blockers.append("allocation.below_safety_floor")
    if any(check.get("compression_within_15_percent") is False for check in checks):
        blockers.append("allocation.daily_compression_above_15_percent")
    return list(dict.fromkeys(blockers))


def _proposal_shaping_seed(allocation: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "recommended_days": allocation.get("planning_days"),
        "daily_kcal_adjustment": allocation.get("daily_kcal_adjustment"),
        "cap_mode": allocation.get("cap_mode"),
        "special_posture": "planned_event_pre_allocation",
    }


def _sanitized_event(context: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "event_id": str(context.get("event_id") or ""),
        "event_label": str(context.get("event_label") or ""),
        "event_local_date": str(context.get("event_local_date") or ""),
        "reserve_kcal": _int(context.get("reserve_kcal")),
        "planning_days_before_event": _int(context.get("planning_days_before_event")),
        "source_refs": [
            str(ref)
            for ref in context.get("source_refs") or []
            if str(ref).startswith("planned_event:")
        ],
    }


def _target_days(packet: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    body = _mapping(packet.get("active_body_plan_view"))
    days = body.get("target_days")
    if not isinstance(days, list):
        return []
    return [day for day in days if isinstance(day, Mapping)]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_planned_event_budget_allocation",
]
