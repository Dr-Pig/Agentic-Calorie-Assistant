from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.active_body_plan_read_model import build_active_body_plan_view
from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_active_body_plan_view_is_inactive_without_bootstrap() -> None:
    db = _session()
    user = get_or_create_user(db, "inactive-plan-user")

    view = build_active_body_plan_view(db, user_id=user.id)

    assert view.user_id == user.id
    assert view.body_plan_id is None
    assert view.plan_status == "inactive"
    assert view.profile_status == "missing"


def test_active_body_plan_view_reads_bootstrap_target_fields() -> None:
    db = _session()
    user = get_or_create_user(db, "active-plan-user")
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=28,
            height_cm=160.0,
            current_weight_kg=54.0,
            activity_level="light",
            goal_type="maintain",
            local_date="2026-04-18",
        ),
    )

    view = build_active_body_plan_view(db, user_id=user.id)

    assert view.body_plan_id is not None
    assert view.plan_status == "active"
    assert view.goal_type == "maintain"
    assert view.daily_budget_kcal == view.recommended_target_kcal
    assert view.plan_source == "onboarding_bootstrap"
