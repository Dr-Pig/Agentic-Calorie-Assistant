from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_onboarding_bootstrap_creates_profile_plan_and_day_ledger() -> None:
    db = _session()
    user = get_or_create_user(db, "onboarding-user")

    result = bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
            timezone="Asia/Taipei",
        ),
    )

    assert result.body_profile.user_id == user.id
    assert result.body_profile.sex == "female"
    assert result.active_body_plan_view.user_id == user.id
    assert result.active_body_plan_view.goal_type == "lose_weight"
    assert result.active_body_plan_view.daily_budget_kcal == result.target_result.recommended_target_kcal
    assert result.current_budget_view.user_id == user.id
    assert result.current_budget_view.local_date == "2026-04-18"
    assert result.current_budget_view.budget_kcal == result.target_result.recommended_target_kcal
    assert result.current_budget_view.consumed_kcal == 0
    assert result.current_budget_view.remaining_kcal == result.target_result.recommended_target_kcal
    assert result.rescue_trigger_enabled is True


def test_onboarding_bootstrap_gain_weight_keeps_budget_but_disables_rescue_trigger() -> None:
    db = _session()
    user = get_or_create_user(db, "gain-user")

    result = bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="male",
            age_years=32,
            height_cm=180.0,
            current_weight_kg=78.0,
            activity_level="moderate",
            goal_type="gain_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
        ),
    )

    assert result.active_body_plan_view.goal_type == "gain_weight"
    assert result.target_result.daily_deficit_kcal == 0
    assert result.rescue_trigger_enabled is False
