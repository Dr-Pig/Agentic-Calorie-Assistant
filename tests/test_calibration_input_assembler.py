from __future__ import annotations

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application.calibration_model import build_calibration_model
from app.body.infrastructure.models import BodyObservationRecord, BodyPlanRecord, BodyProfileRecord
from app.composition.calibration_input_assembler import assemble_calibration_model_inputs_from_history
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealThreadRecord, MealVersionRecord
from app.models import Base


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _active_profile(db: Session, *, user_id: int, timezone: str = "Asia/Taipei") -> BodyProfileRecord:
    profile = BodyProfileRecord(
        user_id=user_id,
        profile_status="active",
        sex="female",
        age_years=31,
        height_cm=165.0,
        current_weight_kg=70.0,
        activity_level="light",
        goal_type="lose_weight",
        timezone=timezone,
        created_at=datetime(2026, 5, 1, 8, 0, 0),
        updated_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


def _active_body_plan(db: Session, *, user_id: int, estimated_tdee: int = 2100) -> BodyPlanRecord:
    plan = BodyPlanRecord(
        user_id=user_id,
        plan_status="active",
        plan_label="assembler baseline",
        estimated_tdee=estimated_tdee,
        daily_budget_kcal=1800,
        safety_floor_kcal=1200,
        target_pace_kg_per_week=0.5,
        metadata_json={"recommended_target_kcal": 1800, "plan_source": "test_baseline"},
        started_at=datetime(2026, 5, 1, 8, 0, 0),
        created_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def _weight(db: Session, *, user_id: int, local_date: str, value: float, hour: int = 7) -> BodyObservationRecord:
    observed_date = datetime.fromisoformat(local_date)
    observation = BodyObservationRecord(
        user_id=user_id,
        observation_type="weight",
        value=value,
        unit="kg",
        observed_at=observed_date.replace(hour=hour, minute=0, second=0),
        local_date=local_date,
        source="manual",
        metadata_json={},
        created_at=observed_date.replace(hour=hour, minute=5, second=0),
    )
    db.add(observation)
    db.commit()
    db.refresh(observation)
    return observation


def _meal(
    db: Session,
    *,
    user_id: int,
    local_date: str,
    kcal: int = 1800,
    created_date: str | None = None,
) -> MealVersionRecord:
    thread = MealThreadRecord(
        user_id=user_id,
        title=f"meal {local_date}",
        thread_kind="text_intake",
        created_at=datetime.fromisoformat(local_date).replace(hour=12),
        updated_at=datetime.fromisoformat(local_date).replace(hour=12),
    )
    db.add(thread)
    db.flush()
    occurred_at = datetime.fromisoformat(local_date).replace(hour=12)
    version = MealVersionRecord(
        meal_thread_id=thread.id,
        version_status="active",
        version_reason="new_intake",
        meal_title=f"meal {local_date}",
        raw_input="test meal",
        resolution_status="completed_meal",
        total_kcal=kcal,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        occurred_at=occurred_at,
        local_date=local_date,
        created_at=datetime.fromisoformat(created_date or local_date).replace(hour=13),
    )
    db.add(version)
    db.flush()
    thread.active_version_id = version.id
    db.commit()
    db.refresh(version)
    return version


def test_calibration_input_assembler_builds_trace_and_high_confidence_inputs_from_real_history() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-assembler-high-confidence")
    _active_profile(db, user_id=user.id)
    _active_body_plan(db, user_id=user.id, estimated_tdee=2100)
    for offset in range(14):
        _meal(db, user_id=user.id, local_date=(datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat())
    first_weight = _weight(db, user_id=user.id, local_date="2026-05-01", value=70.0)
    _weight(db, user_id=user.id, local_date="2026-05-04", value=69.7)
    _weight(db, user_id=user.id, local_date="2026-05-07", value=69.4)
    _weight(db, user_id=user.id, local_date="2026-05-10", value=69.1)
    last_weight = _weight(db, user_id=user.id, local_date="2026-05-14", value=68.8)

    result = assemble_calibration_model_inputs_from_history(
        db,
        user_id=user.id,
        local_date="2026-05-14",
        window_days=14,
    )

    assert result.model_inputs.body_plan_estimated_tdee_kcal == 2100
    assert result.model_inputs.observation_window_days == 14
    assert result.model_inputs.body_observation_count == 5
    assert result.model_inputs.intake_coverage == 1.0
    assert result.model_inputs.logging_gap_ratio == 0.0
    assert result.model_inputs.late_logged_meal_ratio == 0.0
    assert result.model_inputs.rough_meal_ratio == 0.0
    assert result.model_inputs.rescue_overlay_influence == 0.0
    assert result.model_inputs.operating_expenditure_shift_kcal == 411
    assert result.model_inputs.trend_mismatch_consistency == 1.0
    assert result.model_inputs.trend_volatility <= 0.30

    trace = result.trace
    assert trace["timezone"] == "Asia/Taipei"
    assert trace["local_date_end"] == "2026-05-14"
    assert trace["window_start_date"] == "2026-05-01"
    assert trace["window_end_date"] == "2026-05-14"
    assert trace["inclusive_end"] is True
    assert trace["window_days"] == 14
    assert trace["body_observation_count"] == 5
    assert trace["selected_first_weight_observation_id"] == first_weight.id
    assert trace["selected_last_weight_observation_id"] == last_weight.id
    assert trace["weight_delta_kg"] == -1.2
    assert trace["intake_coverage_method"] == "days_with_at_least_one_completed_meal"
    assert trace["intake_coverage_limitation"] == "does_not_prove_full_day_logging"
    assert trace["intake_coverage_confidence"] == "weak_proxy"
    assert trace["average_daily_intake_kcal"] == 1800
    assert trace["kcal_per_kg_assumption"] == 7700
    assert trace["inferred_daily_energy_balance_kcal"] == -711
    assert trace["inferred_operating_expenditure_kcal"] == 2511
    assert trace["active_plan_estimated_tdee"] == 2100
    assert trace["operating_expenditure_shift_kcal"] == 411
    assert trace["rough_meal_ratio_default_reason"] == "not_available_v1_default_zero"
    assert trace["rescue_overlay_influence_default_reason"] == "rescue_integration_deferred_v1"

    calibration_result = build_calibration_model(result.model_inputs)
    assert calibration_result.calibration_posture == "high_confidence_mismatch"


def test_calibration_input_assembler_marks_intake_coverage_as_weak_proxy_and_logging_quality_first() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-assembler-weak-coverage")
    _active_profile(db, user_id=user.id)
    _active_body_plan(db, user_id=user.id, estimated_tdee=2100)
    for local_date in ["2026-05-01", "2026-05-03", "2026-05-05", "2026-05-07", "2026-05-09"]:
        _meal(db, user_id=user.id, local_date=local_date)
    for local_date, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 69.7),
        ("2026-05-07", 69.4),
        ("2026-05-10", 69.1),
        ("2026-05-14", 68.8),
    ]:
        _weight(db, user_id=user.id, local_date=local_date, value=value)

    result = assemble_calibration_model_inputs_from_history(
        db,
        user_id=user.id,
        local_date="2026-05-14",
        window_days=14,
    )

    assert result.model_inputs.intake_coverage == pytest.approx(5 / 14, abs=0.001)
    assert result.model_inputs.logging_gap_ratio == pytest.approx(9 / 14, abs=0.001)
    assert result.trace["intake_coverage_method"] == "days_with_at_least_one_completed_meal"
    assert result.trace["intake_coverage_limitation"] == "does_not_prove_full_day_logging"
    assert result.trace["intake_coverage_confidence"] == "weak_proxy"
    assert build_calibration_model(result.model_inputs).calibration_posture == "logging_quality_first"


def test_calibration_input_assembler_requires_active_body_plan() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-assembler-no-plan")
    _active_profile(db, user_id=user.id)
    _weight(db, user_id=user.id, local_date="2026-05-01", value=70.0)
    _weight(db, user_id=user.id, local_date="2026-05-14", value=68.8)

    with pytest.raises(ValueError, match="active_body_plan_required_for_calibration_input_assembly"):
        assemble_calibration_model_inputs_from_history(
            db,
            user_id=user.id,
            local_date="2026-05-14",
            window_days=14,
        )


def test_calibration_input_assembler_does_not_treat_same_day_cluster_as_trend_window() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-assembler-same-day-cluster")
    _active_profile(db, user_id=user.id)
    _active_body_plan(db, user_id=user.id, estimated_tdee=2100)
    for offset in range(14):
        _meal(db, user_id=user.id, local_date=(datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat())
    for hour, value in [(6, 70.0), (8, 69.5), (10, 69.0), (12, 68.5), (14, 68.0)]:
        _weight(db, user_id=user.id, local_date="2026-05-14", value=value, hour=hour)

    result = assemble_calibration_model_inputs_from_history(
        db,
        user_id=user.id,
        local_date="2026-05-14",
        window_days=14,
    )

    assert result.model_inputs.body_observation_count == 1
    assert result.trace["raw_body_observation_count"] == 5
    assert result.trace["valid_body_observation_day_count"] == 1
    assert result.trace["weight_delta_kg"] == 0.0
    assert result.model_inputs.operating_expenditure_shift_kcal == 0
    assert build_calibration_model(result.model_inputs).calibration_posture == "insufficient_data"


def test_calibration_input_assembler_selects_latest_active_plan_and_profile_when_duplicates_exist() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-assembler-duplicate-active")
    _active_profile(db, user_id=user.id, timezone="UTC")
    _active_profile(db, user_id=user.id, timezone="Asia/Taipei")
    _active_body_plan(db, user_id=user.id, estimated_tdee=2000)
    _active_body_plan(db, user_id=user.id, estimated_tdee=2100)
    for offset in range(14):
        _meal(db, user_id=user.id, local_date=(datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat())
    for local_date, value in [
        ("2026-05-01", 70.0),
        ("2026-05-04", 69.7),
        ("2026-05-07", 69.4),
        ("2026-05-10", 69.1),
        ("2026-05-14", 68.8),
    ]:
        _weight(db, user_id=user.id, local_date=local_date, value=value)

    result = assemble_calibration_model_inputs_from_history(
        db,
        user_id=user.id,
        local_date="2026-05-14",
        window_days=14,
    )

    assert result.model_inputs.body_plan_estimated_tdee_kcal == 2100
    assert result.trace["timezone"] == "Asia/Taipei"


def test_calibration_input_assembler_orders_same_day_weights_by_observed_at_then_id() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-assembler-ordering")
    _active_profile(db, user_id=user.id)
    _active_body_plan(db, user_id=user.id, estimated_tdee=2100)
    for offset in range(14):
        _meal(db, user_id=user.id, local_date=(datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat())
    first = _weight(db, user_id=user.id, local_date="2026-05-01", value=70.3, hour=6)
    _weight(db, user_id=user.id, local_date="2026-05-01", value=70.0, hour=20)
    _weight(db, user_id=user.id, local_date="2026-05-04", value=69.7)
    _weight(db, user_id=user.id, local_date="2026-05-07", value=69.4)
    _weight(db, user_id=user.id, local_date="2026-05-10", value=69.1)
    last = _weight(db, user_id=user.id, local_date="2026-05-14", value=68.8, hour=22)
    _weight(db, user_id=user.id, local_date="2026-05-14", value=69.0, hour=7)

    result = assemble_calibration_model_inputs_from_history(
        db,
        user_id=user.id,
        local_date="2026-05-14",
        window_days=14,
    )

    assert result.trace["selected_first_weight_observation_id"] == first.id
    assert result.trace["selected_last_weight_observation_id"] == last.id
    assert result.trace["weight_delta_kg"] == -1.5
    assert db.execute(select(BodyObservationRecord)).scalars().all()
