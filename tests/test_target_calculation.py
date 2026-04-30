import pytest

from app.body.application import TargetCalculationInputs, calculate_recommended_target_kcal


def test_recommended_target_clamps_to_floor() -> None:
    result = calculate_recommended_target_kcal(
        inputs=TargetCalculationInputs(
            age_years=40,
            sex="female",
            height_cm=152.0,
            weight_kg=45.0,
            activity_level="sedentary",
            weekly_loss_target_kg=1.0,
            safety_floor_kcal=1200,
        )
    )

    assert result.estimated_bmr_kcal == 1039
    assert result.estimated_tdee_kcal == 1247
    assert result.daily_deficit_kcal == 1100
    assert result.raw_target_kcal == 147
    assert result.recommended_target_kcal == 1200
    assert result.clamped_to_floor is True


def test_recommended_target_scales_for_larger_body_and_stays_above_floor() -> None:
    small_body = calculate_recommended_target_kcal(
        inputs=TargetCalculationInputs(
            age_years=35,
            sex="male",
            height_cm=170.0,
            weight_kg=70.0,
            activity_level="moderate",
            weekly_loss_target_kg=0.5,
            safety_floor_kcal=1500,
        )
    )
    larger_body = calculate_recommended_target_kcal(
        inputs=TargetCalculationInputs(
            age_years=35,
            sex="male",
            height_cm=190.0,
            weight_kg=120.0,
            activity_level="active",
            weekly_loss_target_kg=0.5,
            safety_floor_kcal=1500,
        )
    )

    assert small_body.recommended_target_kcal >= 1500
    assert larger_body.recommended_target_kcal > 1500
    assert larger_body.recommended_target_kcal > small_body.recommended_target_kcal
    assert larger_body.estimated_tdee_kcal > small_body.estimated_tdee_kcal
    assert larger_body.clamped_to_floor is False


def test_activity_multiplier_override_must_be_positive() -> None:
    with pytest.raises(ValueError, match="positive"):
        calculate_recommended_target_kcal(
            inputs=TargetCalculationInputs(
                age_years=35,
                sex="male",
                height_cm=175.0,
                weight_kg=75.0,
                activity_level="moderate",
                weekly_loss_target_kg=0.5,
                safety_floor_kcal=1500,
                activity_multiplier_override=0,
            )
        )
