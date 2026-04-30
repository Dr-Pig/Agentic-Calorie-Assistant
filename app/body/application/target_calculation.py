from __future__ import annotations

from dataclasses import dataclass
from math import isnan
from typing import Literal

Sex = Literal["female", "male"]
ActivityLevel = Literal["sedentary", "light", "moderate", "active", "very_active"]

_ACTIVITY_MULTIPLIERS: dict[str, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

_MIFFLIN_ST_JEOR_SEX_OFFSET: dict[str, int] = {
    "female": -161,
    "male": 5,
}

_KCAL_PER_KG_LOSS = 7700.0


@dataclass(frozen=True)
class TargetCalculationInputs:
    age_years: int
    sex: Sex
    height_cm: float
    weight_kg: float
    activity_level: ActivityLevel
    weekly_loss_target_kg: float
    safety_floor_kcal: int
    activity_multiplier_override: float | None = None


@dataclass(frozen=True)
class TargetCalculationResult:
    estimated_bmr_kcal: int
    estimated_tdee_kcal: int
    weekly_loss_target_kg: float
    daily_deficit_kcal: int
    raw_target_kcal: int
    recommended_target_kcal: int
    safety_floor_kcal: int
    activity_multiplier: float
    clamped_to_floor: bool
    formula_name: str = "mifflin_st_jeor"


def _normalize_positive_number(value: float | int) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError("target calculation inputs must be numeric") from exc
    if isnan(normalized) or normalized <= 0:
        raise ValueError("target calculation inputs must be positive")
    return normalized


def _resolve_activity_multiplier(activity_level: ActivityLevel) -> float:
    try:
        return _ACTIVITY_MULTIPLIERS[str(activity_level)]
    except KeyError as exc:  # pragma: no cover - guardrail for invalid callers
        allowed = ", ".join(sorted(_ACTIVITY_MULTIPLIERS))
        raise ValueError(f"unsupported activity_level {activity_level!r}; expected one of: {allowed}") from exc


def _resolve_sex_offset(sex: Sex) -> int:
    try:
        return _MIFFLIN_ST_JEOR_SEX_OFFSET[str(sex)]
    except KeyError as exc:  # pragma: no cover - guardrail for invalid callers
        allowed = ", ".join(sorted(_MIFFLIN_ST_JEOR_SEX_OFFSET))
        raise ValueError(f"unsupported sex {sex!r}; expected one of: {allowed}") from exc


def calculate_recommended_target_kcal(
    *,
    inputs: TargetCalculationInputs | None = None,
    age_years: int | None = None,
    sex: Sex | None = None,
    height_cm: float | None = None,
    weight_kg: float | None = None,
    activity_level: ActivityLevel | None = None,
    weekly_loss_target_kg: float | None = None,
    safety_floor_kcal: int | None = None,
) -> TargetCalculationResult:
    if inputs is None:
        required_fields = {
            "age_years": age_years,
            "sex": sex,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "activity_level": activity_level,
            "weekly_loss_target_kg": weekly_loss_target_kg,
            "safety_floor_kcal": safety_floor_kcal,
        }
        missing = [name for name, value in required_fields.items() if value is None]
        if missing:
            raise ValueError(f"missing target calculation inputs: {', '.join(missing)}")
        inputs = TargetCalculationInputs(
            age_years=int(age_years),
            sex=sex,
            height_cm=float(height_cm),
            weight_kg=float(weight_kg),
            activity_level=activity_level,
            weekly_loss_target_kg=float(weekly_loss_target_kg),
            safety_floor_kcal=int(safety_floor_kcal),
        )
    elif any(
        value is not None
        for value in (age_years, sex, height_cm, weight_kg, activity_level, weekly_loss_target_kg, safety_floor_kcal)
    ):
        raise ValueError("pass either inputs or direct keyword fields, not both")

    age_years = int(_normalize_positive_number(inputs.age_years))
    height_cm = _normalize_positive_number(inputs.height_cm)
    weight_kg = _normalize_positive_number(inputs.weight_kg)
    safety_floor_kcal = int(_normalize_positive_number(inputs.safety_floor_kcal))
    weekly_loss_target_kg = max(0.0, float(inputs.weekly_loss_target_kg))
    activity_multiplier = (
        _normalize_positive_number(inputs.activity_multiplier_override)
        if inputs.activity_multiplier_override is not None
        else _resolve_activity_multiplier(inputs.activity_level)
    )
    sex_offset = _resolve_sex_offset(inputs.sex)

    estimated_bmr_kcal = int(round((10.0 * weight_kg) + (6.25 * height_cm) - (5.0 * age_years) + sex_offset))
    estimated_tdee_kcal = int(round(estimated_bmr_kcal * activity_multiplier))
    daily_deficit_kcal = int(round((weekly_loss_target_kg * _KCAL_PER_KG_LOSS) / 7.0))
    raw_target_kcal = int(round(estimated_tdee_kcal - daily_deficit_kcal))
    recommended_target_kcal = max(safety_floor_kcal, raw_target_kcal)

    return TargetCalculationResult(
        estimated_bmr_kcal=estimated_bmr_kcal,
        estimated_tdee_kcal=estimated_tdee_kcal,
        weekly_loss_target_kg=weekly_loss_target_kg,
        daily_deficit_kcal=daily_deficit_kcal,
        raw_target_kcal=raw_target_kcal,
        recommended_target_kcal=recommended_target_kcal,
        safety_floor_kcal=safety_floor_kcal,
        activity_multiplier=activity_multiplier,
        clamped_to_floor=recommended_target_kcal == safety_floor_kcal and raw_target_kcal < safety_floor_kcal,
    )
