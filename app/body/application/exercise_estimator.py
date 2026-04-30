from __future__ import annotations

from math import isfinite

from app.body.contracts.exercise_event import ExerciseEstimateInput, ExerciseEstimateResult


_DEFAULT_MET_BY_EXERCISE_TYPE = {
    "walking": 3.5,
    "running": 8.3,
    "cycling": 6.8,
    "strength_training": 3.5,
    "other": 3.0,
}


def estimate_exercise_kcal(inputs: ExerciseEstimateInput) -> ExerciseEstimateResult:
    duration_minutes = _positive_float(inputs.duration_minutes, "duration_minutes")

    if inputs.estimation_basis == "user_asserted":
        if inputs.user_asserted_kcal is None:
            raise ValueError("user_asserted_kcal is required for user_asserted exercise estimates")
        estimated_kcal = int(round(_positive_float(inputs.user_asserted_kcal, "user_asserted_kcal")))
        return ExerciseEstimateResult(
            exercise_type=inputs.exercise_type,
            duration_minutes=duration_minutes,
            estimated_kcal=estimated_kcal,
            estimation_basis="user_asserted",
            met_value=None,
            formula_name="user_asserted",
            trace={"deterministic_formula_used": False},
        )

    if inputs.body_weight_kg is None:
        raise ValueError("body_weight_kg is required for met_formula exercise estimates")
    body_weight_kg = _positive_float(inputs.body_weight_kg, "body_weight_kg")
    met_value = _positive_float(
        inputs.met_value if inputs.met_value is not None else _DEFAULT_MET_BY_EXERCISE_TYPE[inputs.exercise_type],
        "met_value",
    )
    estimated_kcal = int(round((met_value * 3.5 * body_weight_kg / 200.0) * duration_minutes))

    return ExerciseEstimateResult(
        exercise_type=inputs.exercise_type,
        duration_minutes=duration_minutes,
        estimated_kcal=estimated_kcal,
        estimation_basis="met_formula",
        met_value=met_value,
        formula_name="met_kcal_v1",
        trace={
            "deterministic_formula_used": True,
            "formula": "met * 3.5 * body_weight_kg / 200 * duration_minutes",
        },
    )


def _positive_float(value: float | int, field_name: str) -> float:
    try:
        normalized = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be numeric") from exc
    if not isfinite(normalized) or normalized <= 0:
        raise ValueError(f"{field_name} must be positive finite")
    return normalized
