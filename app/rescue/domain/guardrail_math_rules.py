from __future__ import annotations

from math import ceil, floor
from typing import Any, Literal, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.domain.guardrail_math_rules"
)
STANDARD_CAP_FRACTION = 0.15
STRAINED_CAP_FRACTION = 0.10
MAX_RESCUE_HORIZON_DAYS = 5
RecoveryViability = Literal["viable", "strained", "non_viable", "blocked"]


def overshoot(current_budget: Mapping[str, Any]) -> int:
    if isinstance(current_budget.get("overshoot_kcal"), int):
        return int(current_budget["overshoot_kcal"])
    consumed = int_value(current_budget.get("meal_consumption_total_kcal"))
    effective = int_value(current_budget.get("effective_budget_kcal"))
    return max(0, consumed - effective)


def overshoot_summary(
    current_budget: Mapping[str, Any],
    overshoot_kcal: int,
) -> dict[str, int]:
    return {
        "meal_consumption_total_kcal": int_value(
            current_budget.get("meal_consumption_total_kcal")
        ),
        "effective_budget_kcal": int_value(current_budget.get("effective_budget_kcal")),
        "overshoot_kcal": overshoot_kcal,
    }


def recommended_days(
    *,
    overshoot_kcal: int,
    daily_cap_kcal: int,
    target_day_count: int,
) -> int | None:
    if overshoot_kcal <= 0 or daily_cap_kcal <= 0 or target_day_count <= 0:
        return None
    return min(ceil(overshoot_kcal / daily_cap_kcal), MAX_RESCUE_HORIZON_DAYS)


def target_day_checks(
    *,
    target_days: list[Mapping[str, Any]],
    daily_recovery_kcal: int,
    safety_floor_kcal: int,
) -> list[dict[str, Any]]:
    return [
        target_day_check(
            target_day=target_day,
            daily_recovery_kcal=daily_recovery_kcal,
            safety_floor_kcal=safety_floor_kcal,
        )
        for target_day in target_days
    ]


def target_day_check(
    *,
    target_day: Mapping[str, Any],
    daily_recovery_kcal: int,
    safety_floor_kcal: int,
) -> dict[str, Any]:
    base_budget = int_value(target_day.get("base_budget_kcal"))
    calibration = int_value(target_day.get("calibration_adjustment_total_kcal"))
    max_daily = floor(base_budget * STANDARD_CAP_FRACTION)
    strained_daily = floor(base_budget * STRAINED_CAP_FRACTION)
    candidate_effective = base_budget + calibration - daily_recovery_kcal
    return {
        "local_date": str(target_day.get("local_date") or ""),
        "base_budget_kcal": base_budget,
        "calibration_adjustment_total_kcal": calibration,
        "proposed_rescue_overlay_kcal": -daily_recovery_kcal,
        "candidate_effective_budget_kcal": candidate_effective,
        "safety_floor_kcal": safety_floor_kcal,
        "safety_floor_passed": candidate_effective >= safety_floor_kcal,
        "max_daily_rescue_compression_kcal": max_daily,
        "strained_threshold_kcal": strained_daily,
        "compression_within_15_percent": daily_recovery_kcal <= max_daily,
        "compression_exceeds_10_percent": daily_recovery_kcal > strained_daily,
        "cap_denominator": "base_budget_kcal",
    }


def math_blockers(
    *,
    overshoot_kcal: int,
    daily_cap_kcal: int,
    recommended_days_value: int | None,
    target_day_count: int,
    checks: list[Mapping[str, Any]],
) -> list[str]:
    blockers: list[str] = []
    if overshoot_kcal <= 0:
        blockers.append("no_overshoot")
    if daily_cap_kcal <= 0:
        blockers.append("missing_daily_cap")
    if recommended_days_value is None:
        blockers.append("missing_recommended_horizon")
    elif recommended_days_value > target_day_count:
        blockers.append("target_horizon_unavailable")
    if any(check.get("compression_within_15_percent") is False for check in checks):
        blockers.append("daily_compression_above_15_percent")
    if any(check.get("safety_floor_passed") is False for check in checks):
        blockers.append("below_safety_floor")
    return list(dict.fromkeys(blockers))


def recovery_viability(
    blockers: list[str],
    checks: list[Mapping[str, Any]],
) -> RecoveryViability:
    if blockers:
        return "non_viable"
    if any(check.get("compression_exceeds_10_percent") is True for check in checks):
        return "strained"
    return "viable"


def daily_cap(target_days: list[Mapping[str, Any]]) -> int:
    caps = [
        floor(int_value(day.get("base_budget_kcal")) * STANDARD_CAP_FRACTION)
        for day in target_days
    ]
    return min(caps) if caps else 0


def target_days(body_plan: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    rows = body_plan.get("target_days")
    if not isinstance(rows, list):
        return []
    return [item for item in rows if isinstance(item, Mapping)]


def safety_floor(body_plan: Mapping[str, Any]) -> int:
    return int_value(body_plan.get("safety_floor_kcal")) or 1500


def int_value(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "RecoveryViability",
    "SIDECAR_ACTIVATION_CONTRACT",
    "daily_cap",
    "math_blockers",
    "overshoot",
    "overshoot_summary",
    "recommended_days",
    "recovery_viability",
    "safety_floor",
    "target_day_checks",
    "target_days",
]
