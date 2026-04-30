from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


ExerciseEstimationBasis = Literal["met_formula", "user_asserted"]
ExerciseType = Literal["walking", "running", "cycling", "strength_training", "other"]


class ExerciseEstimateInput(BaseModel):
    exercise_type: ExerciseType
    duration_minutes: float
    estimation_basis: ExerciseEstimationBasis = "met_formula"
    body_weight_kg: float | None = None
    met_value: float | None = None
    user_asserted_kcal: int | None = None
    ledger_write_authorized: Literal[False] = False


class ExerciseEstimateResult(BaseModel):
    exercise_type: ExerciseType
    duration_minutes: float
    estimated_kcal: int
    estimation_basis: ExerciseEstimationBasis
    met_value: float | None = None
    formula_name: Literal["met_kcal_v1", "user_asserted"]
    ledger_write_authorized: Literal[False] = False
    trace: dict[str, object] = Field(default_factory=dict)
