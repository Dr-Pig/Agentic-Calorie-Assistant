from __future__ import annotations

import asyncio

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.body.application import OnboardingBootstrapInput, bootstrap_body_plan_for_date, build_active_body_plan_view
from app.body.interface.weight_routes import WeightObservationRequest, post_weight_observation
from app.database import get_or_create_user
from app.models import Base


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_weight_observation_does_not_silently_rebootstrap_body_plan() -> None:
    db = _session()
    user = get_or_create_user(db, "weight-boundary-user")
    bootstrap_body_plan_for_date(
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
    before = build_active_body_plan_view(db, user_id=user.id)

    response = asyncio.run(
        post_weight_observation(
            WeightObservationRequest(
                user_id="weight-boundary-user",
                weight_kg=70.0,
                local_date="2026-04-19",
            ),
            db=db,
        )
    )
    after = build_active_body_plan_view(db, user_id=user.id)

    assert response["status"] == "ok"
    assert response["recomputed_target_kcal"] is None
    assert after.body_plan_id == before.body_plan_id
    assert after.daily_budget_kcal == before.daily_budget_kcal
    assert after.recommended_target_kcal == before.recommended_target_kcal
    assert after.current_weight_kg == before.current_weight_kg
