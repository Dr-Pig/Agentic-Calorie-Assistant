from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from statistics import pstdev
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.body.application.calibration_model import CalibrationModelInputs
from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord

KCAL_PER_KG = 7700
DEFAULT_ROUGH_MEAL_RATIO_REASON = "not_available_v1_default_zero"
DEFAULT_RESCUE_OVERLAY_REASON = "rescue_integration_deferred_v1"


@dataclass(frozen=True)
class CalibrationInputAssemblyResult:
    model_inputs: CalibrationModelInputs
    trace: dict[str, Any]


def _parse_local_date(local_date: str) -> date:
    try:
        return date.fromisoformat(local_date)
    except ValueError as exc:
        raise ValueError("local_date_must_be_iso_date") from exc


def _ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 3)


def _load_active_body_plan(db: Session, *, user_id: int) -> BodyPlanRecord:
    active_body_plan = db.execute(
        select(BodyPlanRecord)
        .where(
            BodyPlanRecord.user_id == user_id,
            BodyPlanRecord.plan_status == "active",
        )
        .order_by(BodyPlanRecord.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if active_body_plan is None or int(active_body_plan.estimated_tdee or 0) <= 0:
        raise ValueError("active_body_plan_required_for_calibration_input_assembly")
    return active_body_plan


def _load_timezone(db: Session, *, user_id: int) -> str:
    active_profile = db.execute(
        select(BodyProfileRecord)
        .where(
            BodyProfileRecord.user_id == user_id,
            BodyProfileRecord.profile_status == "active",
        )
        .order_by(BodyProfileRecord.id.desc())
        .limit(1)
    ).scalar_one_or_none()
    if active_profile is None or not active_profile.timezone:
        return "unknown"
    return str(active_profile.timezone)


def _load_weight_observations(
    db: Session,
    *,
    user_id: int,
    window_start_date: str,
    window_end_date: str,
) -> list[BodyObservationRecord]:
    return list(
        db.execute(
            select(BodyObservationRecord)
            .where(
                BodyObservationRecord.user_id == user_id,
                BodyObservationRecord.observation_type == "weight",
                BodyObservationRecord.local_date >= window_start_date,
                BodyObservationRecord.local_date <= window_end_date,
            )
            .order_by(BodyObservationRecord.observed_at.asc(), BodyObservationRecord.id.asc())
        )
        .scalars()
        .all()
    )


def _load_active_completed_meals(
    db: Session,
    *,
    user_id: int,
    window_start_date: str,
    window_end_date: str,
) -> list[MealVersionRecord]:
    return list(
        db.execute(
            select(MealVersionRecord)
            .join(
                MealThreadRecord,
                MealThreadRecord.id == MealVersionRecord.meal_thread_id,
            )
            .where(
                MealThreadRecord.user_id == user_id,
                MealThreadRecord.active_version_id == MealVersionRecord.id,
                MealVersionRecord.version_status == "active",
                MealVersionRecord.resolution_status == "completed_meal",
                MealVersionRecord.local_date >= window_start_date,
                MealVersionRecord.local_date <= window_end_date,
            )
            .order_by(MealVersionRecord.local_date.asc(), MealVersionRecord.id.asc())
        )
        .scalars()
        .all()
    )


def _trend_volatility(weights: list[BodyObservationRecord]) -> float:
    if len(weights) < 3:
        return 0.0
    volatility = pstdev([float(weight.value) for weight in weights]) / 2.0
    return round(min(1.0, max(0.0, volatility)), 3)


def _weights_by_local_date(weights: list[BodyObservationRecord]) -> dict[str, list[BodyObservationRecord]]:
    grouped: dict[str, list[BodyObservationRecord]] = {}
    for weight in weights:
        if not weight.local_date:
            continue
        grouped.setdefault(str(weight.local_date), []).append(weight)
    return grouped


def _ordered_by_observed_at_then_id(weights: list[BodyObservationRecord]) -> list[BodyObservationRecord]:
    return sorted(weights, key=lambda weight: (weight.observed_at, weight.id))


def _select_weight_trend_endpoints(
    weights: list[BodyObservationRecord],
) -> tuple[BodyObservationRecord | None, BodyObservationRecord | None, int, list[BodyObservationRecord]]:
    grouped = _weights_by_local_date(weights)
    if not grouped:
        return None, None, 0, []

    ordered_dates = sorted(grouped)
    first_day_weights = _ordered_by_observed_at_then_id(grouped[ordered_dates[0]])
    last_day_weights = _ordered_by_observed_at_then_id(grouped[ordered_dates[-1]])
    daily_trend_weights = [
        _ordered_by_observed_at_then_id(grouped[local_date])[-1]
        for local_date in ordered_dates
    ]
    return first_day_weights[0], last_day_weights[-1], len(ordered_dates), daily_trend_weights


def assemble_calibration_model_inputs_from_history(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    window_days: int = 14,
) -> CalibrationInputAssemblyResult:
    if window_days <= 0:
        raise ValueError("window_days_must_be_positive")

    local_date_end = _parse_local_date(local_date)
    window_start = local_date_end - timedelta(days=window_days - 1)
    window_start_date = window_start.isoformat()
    window_end_date = local_date_end.isoformat()

    active_body_plan = _load_active_body_plan(db, user_id=user_id)
    timezone = _load_timezone(db, user_id=user_id)
    weights = _load_weight_observations(
        db,
        user_id=user_id,
        window_start_date=window_start_date,
        window_end_date=window_end_date,
    )
    meals = _load_active_completed_meals(
        db,
        user_id=user_id,
        window_start_date=window_start_date,
        window_end_date=window_end_date,
    )

    meal_dates = {meal.local_date for meal in meals if meal.local_date}
    meal_count = len(meals)
    intake_coverage = _ratio(len(meal_dates), window_days)
    total_intake_kcal = sum(int(meal.total_kcal or 0) for meal in meals)
    average_daily_intake_kcal = int(round(total_intake_kcal / window_days)) if window_days else 0
    late_logged_meal_count = sum(
        1
        for meal in meals
        if meal.created_at is not None
        and meal.local_date
        and meal.created_at.date().isoformat() > str(meal.local_date)
    )
    late_logged_meal_ratio = _ratio(late_logged_meal_count, meal_count)
    logging_gap_ratio = round(max(0.0, 1.0 - intake_coverage), 3)

    raw_body_observation_count = len(weights)
    first_weight, last_weight, valid_body_observation_day_count, daily_trend_weights = _select_weight_trend_endpoints(
        weights
    )
    body_observation_count = valid_body_observation_day_count
    selected_first_weight_observation_id = first_weight.id if first_weight is not None else None
    selected_last_weight_observation_id = last_weight.id if last_weight is not None else None

    weight_delta_kg = 0.0
    inferred_daily_energy_balance_kcal = 0
    inferred_operating_expenditure_kcal = int(active_body_plan.estimated_tdee)
    operating_expenditure_shift_kcal = 0
    if (
        first_weight is not None
        and last_weight is not None
        and str(first_weight.local_date) != str(last_weight.local_date)
    ):
        weight_delta_kg = round(float(last_weight.value) - float(first_weight.value), 3)
        first_local_date = _parse_local_date(str(first_weight.local_date))
        last_local_date = _parse_local_date(str(last_weight.local_date))
        trend_days = max(1, (last_local_date - first_local_date).days)
        inferred_daily_energy_balance_kcal = int(round((weight_delta_kg * KCAL_PER_KG) / trend_days))
        inferred_operating_expenditure_kcal = int(
            round(average_daily_intake_kcal - inferred_daily_energy_balance_kcal)
        )
        operating_expenditure_shift_kcal = int(
            inferred_operating_expenditure_kcal - int(active_body_plan.estimated_tdee)
        )

    trend_mismatch_consistency = round(min(1.0, abs(operating_expenditure_shift_kcal) / 400.0), 3)
    trend_volatility = _trend_volatility(daily_trend_weights)

    model_inputs = CalibrationModelInputs(
        body_plan_estimated_tdee_kcal=int(active_body_plan.estimated_tdee),
        observation_window_days=window_days,
        body_observation_count=body_observation_count,
        intake_coverage=intake_coverage,
        operating_expenditure_shift_kcal=operating_expenditure_shift_kcal,
        trend_mismatch_consistency=trend_mismatch_consistency,
        trend_volatility=trend_volatility,
        logging_gap_ratio=logging_gap_ratio,
        late_logged_meal_ratio=late_logged_meal_ratio,
        rough_meal_ratio=0.0,
        rescue_overlay_influence=0.0,
    )
    trace: dict[str, Any] = {
        "timezone": timezone,
        "local_date_end": window_end_date,
        "window_start_date": window_start_date,
        "window_end_date": window_end_date,
        "inclusive_end": True,
        "window_days": window_days,
        "body_observation_count": body_observation_count,
        "raw_body_observation_count": raw_body_observation_count,
        "valid_body_observation_day_count": valid_body_observation_day_count,
        "selected_first_weight_observation_id": selected_first_weight_observation_id,
        "selected_last_weight_observation_id": selected_last_weight_observation_id,
        "weight_delta_kg": weight_delta_kg,
        "intake_coverage_method": "days_with_at_least_one_completed_meal",
        "intake_coverage_limitation": "does_not_prove_full_day_logging",
        "intake_coverage_confidence": "weak_proxy",
        "meal_day_count": len(meal_dates),
        "meal_count": meal_count,
        "average_daily_intake_kcal": average_daily_intake_kcal,
        "kcal_per_kg_assumption": KCAL_PER_KG,
        "inferred_daily_energy_balance_kcal": inferred_daily_energy_balance_kcal,
        "inferred_operating_expenditure_kcal": inferred_operating_expenditure_kcal,
        "active_plan_estimated_tdee": int(active_body_plan.estimated_tdee),
        "operating_expenditure_shift_kcal": operating_expenditure_shift_kcal,
        "rough_meal_ratio_default_reason": DEFAULT_ROUGH_MEAL_RATIO_REASON,
        "rescue_overlay_influence_default_reason": DEFAULT_RESCUE_OVERLAY_REASON,
    }
    return CalibrationInputAssemblyResult(model_inputs=model_inputs, trace=trace)
