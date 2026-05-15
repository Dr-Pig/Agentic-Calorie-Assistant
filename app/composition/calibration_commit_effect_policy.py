from __future__ import annotations

from typing import Any

from app.body.infrastructure.models import BodyPlanRecord

PLAN_CHANGING_CALIBRATION_FAMILIES = frozenset(
    {
        "budget_adjustment",
        "pace_adjustment",
        "plan_reset",
    }
)
MIN_DAILY_BUDGET_KCAL = 800
MAX_DAILY_BUDGET_KCAL = 5000
MIN_ESTIMATED_TDEE_KCAL = 800
MAX_ESTIMATED_TDEE_KCAL = 6000
MAX_TARGET_PACE_KG_PER_WEEK = 2.0


def validate_plan_changing_effect_payload(
    *,
    proposal_family: str,
    effect_payload: dict[str, Any],
    active_plan: BodyPlanRecord | None,
) -> dict[str, Any]:
    if proposal_family not in PLAN_CHANGING_CALIBRATION_FAMILIES:
        if effect_payload.get("plan_change_required") is True:
            raise ValueError(f"unknown plan-changing calibration proposal_family {proposal_family!r}")
        return effect_payload

    new_daily_budget = _coerce_required_int(effect_payload, "new_daily_budget_kcal")
    safety_floor = int(active_plan.safety_floor_kcal or 0) if active_plan is not None else 0
    if new_daily_budget < safety_floor:
        raise ValueError("new_daily_budget_kcal must not be below active plan safety_floor_kcal")
    if not MIN_DAILY_BUDGET_KCAL <= new_daily_budget <= MAX_DAILY_BUDGET_KCAL:
        raise ValueError(
            f"new_daily_budget_kcal must be between {MIN_DAILY_BUDGET_KCAL} and {MAX_DAILY_BUDGET_KCAL}"
        )

    if "new_estimated_tdee_kcal" in effect_payload and effect_payload.get("new_estimated_tdee_kcal") is not None:
        new_estimated_tdee = _coerce_required_int(effect_payload, "new_estimated_tdee_kcal")
    else:
        if active_plan is None:
            raise ValueError("new_estimated_tdee_kcal is required when no active plan TDEE can be inherited")
        new_estimated_tdee = int(active_plan.estimated_tdee or 0)
    if not MIN_ESTIMATED_TDEE_KCAL <= new_estimated_tdee <= MAX_ESTIMATED_TDEE_KCAL:
        raise ValueError(
            f"new_estimated_tdee_kcal must be between {MIN_ESTIMATED_TDEE_KCAL} and {MAX_ESTIMATED_TDEE_KCAL}"
        )

    normalized = dict(effect_payload)
    normalized["new_daily_budget_kcal"] = new_daily_budget
    normalized["new_estimated_tdee_kcal"] = new_estimated_tdee
    calibration_adjustment_delta = _coerce_optional_int(normalized, "calibration_adjustment_delta_kcal")
    if calibration_adjustment_delta is not None:
        candidate_effective_budget = new_daily_budget + calibration_adjustment_delta
        if candidate_effective_budget < safety_floor:
            raise ValueError(
                "calibration_adjustment_delta_kcal must not push effective budget below active plan safety_floor_kcal"
            )
        normalized["calibration_adjustment_delta_kcal"] = calibration_adjustment_delta
    if proposal_family in {"pace_adjustment", "plan_reset"}:
        new_pace = _coerce_optional_float(normalized, "new_target_pace_kg_per_week")
        if new_pace is not None:
            if new_pace <= 0 or new_pace > MAX_TARGET_PACE_KG_PER_WEEK:
                raise ValueError(
                    f"new_target_pace_kg_per_week must be positive and <= {MAX_TARGET_PACE_KG_PER_WEEK}"
                )
            normalized["new_target_pace_kg_per_week"] = new_pace
    return normalized


def _coerce_required_int(payload: dict[str, Any], field_name: str) -> int:
    if field_name not in payload or payload.get(field_name) is None:
        raise ValueError(f"{field_name} is required for accepted plan-changing calibration proposal")
    return _coerce_int_value(payload[field_name], field_name=field_name)


def _coerce_optional_int(payload: dict[str, Any], field_name: str) -> int | None:
    if field_name not in payload or payload.get(field_name) is None:
        return None
    return _coerce_int_value(payload[field_name], field_name=field_name)


def _coerce_int_value(value: Any, *, field_name: str) -> int:
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be an integer")
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if value.is_integer():
            return int(value)
        raise ValueError(f"{field_name} must be an integer")
    try:
        return int(str(value).strip())
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be an integer") from exc


def _coerce_optional_float(payload: dict[str, Any], field_name: str) -> float | None:
    if field_name not in payload or payload.get(field_name) is None:
        return None
    value = payload[field_name]
    if isinstance(value, bool):
        raise ValueError(f"{field_name} must be numeric")
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc


__all__ = ["PLAN_CHANGING_CALIBRATION_FAMILIES", "validate_plan_changing_effect_payload"]
