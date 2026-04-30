from __future__ import annotations

from math import inf

import pytest
from pydantic import ValidationError

from app.body.application.exercise_estimator import estimate_exercise_kcal
from app.body.contracts.exercise_event import ExerciseEstimateInput


def test_met_formula_estimates_exercise_kcal_without_ledger_write_authority() -> None:
    result = estimate_exercise_kcal(
        ExerciseEstimateInput(
            exercise_type="walking",
            duration_minutes=60,
            body_weight_kg=70,
            estimation_basis="met_formula",
        )
    )

    assert result.estimated_kcal == 257
    assert result.estimation_basis == "met_formula"
    assert result.met_value == 3.5
    assert result.formula_name == "met_kcal_v1"
    assert result.ledger_write_authorized is False


def test_user_asserted_exercise_kcal_is_preserved_without_formula_recalculation() -> None:
    result = estimate_exercise_kcal(
        ExerciseEstimateInput(
            exercise_type="strength_training",
            duration_minutes=45,
            estimation_basis="user_asserted",
            user_asserted_kcal=320,
        )
    )

    assert result.estimated_kcal == 320
    assert result.estimation_basis == "user_asserted"
    assert result.met_value is None
    assert result.formula_name == "user_asserted"
    assert result.ledger_write_authorized is False


def test_exercise_estimate_contract_rejects_mutation_authority() -> None:
    with pytest.raises(ValidationError):
        ExerciseEstimateInput(
            exercise_type="cycling",
            duration_minutes=30,
            body_weight_kg=70,
            estimation_basis="met_formula",
            ledger_write_authorized=True,
        )


@pytest.mark.parametrize(
    "field_name, value",
    [
        ("duration_minutes", inf),
        ("body_weight_kg", inf),
        ("met_value", inf),
    ],
)
def test_met_formula_rejects_non_finite_numeric_inputs(field_name: str, value: float) -> None:
    payload = {
        "exercise_type": "walking",
        "duration_minutes": 30,
        "body_weight_kg": 70,
        "met_value": 3.5,
        "estimation_basis": "met_formula",
    }
    payload[field_name] = value

    with pytest.raises(ValueError, match="finite"):
        estimate_exercise_kcal(ExerciseEstimateInput(**payload))


def test_user_asserted_exercise_kcal_rejects_non_finite_value() -> None:
    with pytest.raises(ValueError, match="finite"):
        estimate_exercise_kcal(
            ExerciseEstimateInput(
                exercise_type="walking",
                duration_minutes=30,
                estimation_basis="user_asserted",
                user_asserted_kcal=inf,
            )
        )
