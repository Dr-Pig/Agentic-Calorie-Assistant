from __future__ import annotations

from math import ceil, floor
from typing import Any, Literal, Mapping

from app.rescue.domain.shadow_status import RESCUE_SHADOW_NON_RUNTIME_FLAGS
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.no_commit_viability"
)
RecoveryViability = Literal["viable", "strained", "non_viable", "blocked"]
CONTEXT_ARTIFACT = "rescue_shadow_summary_context_projection"
CONTEXT_FALSE_FLAGS = (
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_injected",
    "proactive_sent",
    "recommendation_served",
)


def build_rescue_no_commit_viability_shadow_packet(
    *,
    rescue_context_projection: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
) -> dict[str, Any]:
    input_blockers = _input_blockers(
        rescue_context_projection=rescue_context_projection,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
        open_proposals_view=open_proposals_view,
    )
    overshoot = _overshoot(current_budget_view)
    target_days = _target_days(active_body_plan_view) if not input_blockers else []
    daily_recovery = ceil(overshoot / len(target_days)) if target_days and overshoot > 0 else 0
    checks = _target_day_checks(
        target_days=target_days,
        daily_recovery_kcal=daily_recovery,
        safety_floor_kcal=_safety_floor(active_body_plan_view),
    )
    viability_blockers = [] if input_blockers else _viability_blockers(overshoot, checks)
    viability = _recovery_viability(
        input_blockers=input_blockers,
        viability_blockers=viability_blockers,
        checks=checks,
    )
    return {
        "artifact_type": "rescue_no_commit_viability_shadow_packet",
        "artifact_schema_version": "1.0",
        "status": "blocked" if input_blockers else "pass",
        "owner": "app/rescue",
        "consumer": "future_rescue_option_generation_shadow_review",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "rescue_context_projection_used": not input_blockers,
        "overshoot_summary": _overshoot_summary(current_budget_view, overshoot),
        "rescue_horizon_days": len(target_days),
        "daily_recovery_kcal": daily_recovery,
        "recovery_viability": viability,
        "target_day_checks": checks,
        "blockers": [*input_blockers, *viability_blockers],
        "proposal_card": None,
        "candidate_copy": None,
        "send_or_skip": None,
        "primary_actions": [],
        "runtime_effect_allowed": False,
        "recommendation_posture_updated": False,
        "ledger_entry_created": False,
        **dict(RESCUE_SHADOW_NON_RUNTIME_FLAGS),
    }

def _input_blockers(
    *,
    rescue_context_projection: Mapping[str, Any],
    current_budget_view: Mapping[str, Any],
    active_body_plan_view: Mapping[str, Any],
    open_proposals_view: Mapping[str, Any],
) -> list[str]:
    blockers = _context_blockers(rescue_context_projection)
    if not _budget_values_available(current_budget_view):
        blockers.append("missing_budget_view")
    target_days = _target_days(active_body_plan_view)
    if not target_days:
        blockers.append("missing_body_plan_view")
    if len(target_days) > 5:
        blockers.append("horizon_exceeds_5_days")
    if _int(open_proposals_view.get("open_rescue_proposal_count")) > 0:
        blockers.append("open_rescue_proposal")
    return blockers

def _context_blockers(projection: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if projection.get("artifact_type") != CONTEXT_ARTIFACT:
        blockers.append("rescue_context_projection.unsupported_artifact_type")
    if projection.get("status") != "pass":
        blockers.append("rescue_context_projection.status_not_pass")
    for flag in CONTEXT_FALSE_FLAGS:
        if projection.get(flag) is True:
            blockers.append(f"rescue_context_projection.{flag}")
    return blockers

def _budget_values_available(view: Mapping[str, Any]) -> bool:
    return (
        isinstance(view.get("effective_budget_kcal"), int)
        and isinstance(view.get("meal_consumption_total_kcal"), int)
    )

def _overshoot(view: Mapping[str, Any]) -> int:
    if not _budget_values_available(view):
        return 0
    consumed = int(view["meal_consumption_total_kcal"])
    effective = int(view["effective_budget_kcal"])
    return max(0, consumed - effective)

def _overshoot_summary(view: Mapping[str, Any], overshoot: int) -> dict[str, int]:
    return {
        "meal_consumption_total_kcal": _int(view.get("meal_consumption_total_kcal")),
        "effective_budget_kcal": _int(view.get("effective_budget_kcal")),
        "overshoot_kcal": overshoot,
    }

def _target_day_checks(
    *,
    target_days: list[Mapping[str, Any]],
    daily_recovery_kcal: int,
    safety_floor_kcal: int,
) -> list[dict[str, Any]]:
    return [
        _target_day_check(
            target_day=target_day,
            daily_recovery_kcal=daily_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
        )
        for target_day in target_days
    ]

def _target_day_check(
    *,
    target_day: Mapping[str, Any],
    daily_recovery_kcal: int,
    safety_floor_kcal: int,
) -> dict[str, Any]:
    base_budget = _int(target_day.get("base_budget_kcal"))
    calibration = _int(target_day.get("calibration_adjustment_total_kcal"))
    max_10 = floor(base_budget * 0.10)
    max_15 = floor(base_budget * 0.15)
    candidate_effective = base_budget + calibration - daily_recovery_kcal
    return {
        "local_date": str(target_day.get("local_date") or ""),
        "base_budget_kcal": base_budget,
        "proposed_rescue_overlay_kcal": -daily_recovery_kcal,
        "max_10_percent_kcal": max_10,
        "max_15_percent_kcal": max_15,
        "candidate_effective_budget_kcal": candidate_effective,
        "safety_floor_kcal": safety_floor_kcal,
        "compression_within_15_percent": daily_recovery_kcal <= max_15,
        "compression_exceeds_10_percent": daily_recovery_kcal > max_10,
        "safety_floor_passed": candidate_effective >= safety_floor_kcal,
    }

def _viability_blockers(overshoot: int, checks: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    if overshoot <= 0:
        blockers.append("no_overshoot")
    if any(check.get("compression_within_15_percent") is False for check in checks):
        blockers.append("daily_compression_above_15_percent")
    if any(check.get("safety_floor_passed") is False for check in checks):
        blockers.append("below_safety_floor")
    return blockers

def _recovery_viability(
    *,
    input_blockers: list[str],
    viability_blockers: list[str],
    checks: list[Mapping[str, Any]],
) -> RecoveryViability:
    if input_blockers:
        return "blocked"
    if viability_blockers:
        return "non_viable"
    if any(check.get("compression_exceeds_10_percent") is True for check in checks):
        return "strained"
    return "viable"

def _target_days(view: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    value = view.get("target_days")
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, Mapping)]

def _safety_floor(view: Mapping[str, Any]) -> int:
    if isinstance(view.get("safety_floor_kcal"), int):
        return int(view["safety_floor_kcal"])
    return 1500 if str(view.get("sex") or "").lower() == "male" else 1200

def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0

__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_rescue_no_commit_viability_shadow_packet",
]
