from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.composition.body_budget_deficit_summary import build_body_budget_deficit_summary
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.composition.today_routes import router as today_router
from app.database import get_db, get_or_create_user
from app.models import Base
from app.schemas import CommitRequestCandidate
from app.body.application.body_observation_service import record_body_observation_to_canonical


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(db: Session) -> TestClient:
    app = FastAPI()
    app.include_router(today_router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _commit_meal(db: Session, *, user_id: str, local_date: str, kcal: int) -> None:
    user = get_or_create_user(db, user_id)
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id=f"{user_id}-meal",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="tea egg",
            raw_input="tea egg",
            estimated_kcal=kcal,
            protein_g=7,
            carb_g=1,
            fat_g=5,
            resolution_status="completed_meal",
            local_date=local_date,
        ),
    )


def _bootstrap_user(db: Session, *, user_id: str, local_date: str):
    user = get_or_create_user(db, user_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=70.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date=local_date,
            timezone="Asia/Taipei",
        ),
    )
    return user


def test_body_budget_deficit_summary_combines_budget_plan_and_latest_weight_without_mutation() -> None:
    db = _session()
    user_id = "deficit-summary-user"
    local_date = "2026-05-04"
    user = _bootstrap_user(db, user_id=user_id, local_date=local_date)
    _commit_meal(db, user_id=user_id, local_date=local_date, kcal=420)
    record_body_observation_to_canonical(
        db,
        user=user,
        value=69.8,
        observed_at=datetime(2026, 5, 4, 7, 30, 0),
        local_date=local_date,
    )
    record_body_observation_to_canonical(
        db,
        user=user,
        value=69.4,
        observed_at=datetime(2026, 5, 4, 22, 30, 0),
        local_date=local_date,
    )

    summary = build_body_budget_deficit_summary(db, user_id=user.id, local_date=local_date)

    assert summary["source_kind"] == "body_budget_deficit_summary"
    assert summary["read_only"] is True
    assert summary["user_id"] == user.id
    assert summary["local_date"] == local_date
    assert summary["active_daily_target_kcal"] == summary["current_budget"]["budget_kcal"]
    assert summary["recommended_target_kcal"] == summary["active_body_plan"]["recommended_target_kcal"]
    assert summary["consumed_kcal"] == 420
    assert summary["remaining_kcal"] == summary["active_daily_target_kcal"] - 420
    assert summary["estimated_daily_deficit_kcal"] == (
        summary["active_body_plan"]["estimated_tdee"] - summary["active_daily_target_kcal"]
    )
    assert summary["latest_weight_kg"] == 69.4
    assert summary["latest_weight_observed_at"] == "2026-05-04T22:30:00"
    assert summary["weight_history_count"] == 2
    assert summary["body_profile_current_weight_kg"] == 70.0
    assert summary["automatic_calibration_enabled"] is False
    assert summary["rescue_enabled"] is False
    assert summary["recommendation_enabled"] is False
    assert summary["proactive_enabled"] is False


def test_body_budget_deficit_summary_does_not_fake_target_without_active_plan() -> None:
    db = _session()
    user_id = "deficit-summary-no-plan"
    local_date = "2026-05-04"
    user = get_or_create_user(db, user_id)
    _commit_meal(db, user_id=user_id, local_date=local_date, kcal=420)

    summary = build_body_budget_deficit_summary(db, user_id=user.id, local_date=local_date)

    assert summary["target_available"] is False
    assert summary["remaining_available"] is False
    assert summary["active_daily_target_kcal"] is None
    assert summary["remaining_kcal"] is None
    assert summary["consumed_kcal"] == 420
    assert summary["estimated_daily_deficit_kcal"] is None
    assert summary["latest_weight_kg"] is None
    assert summary["weight_history_count"] == 0


def test_today_deficit_summary_route_returns_body_budget_read_model() -> None:
    db = _session()
    client = _client(db)
    user_id = "deficit-summary-route"
    local_date = "2026-05-04"
    user = _bootstrap_user(db, user_id=user_id, local_date=local_date)
    record_body_observation_to_canonical(
        db,
        user=user,
        value=68.2,
        observed_at=datetime(2026, 5, 4, 7, 30, 0),
        local_date=local_date,
    )

    response = client.get(
        "/today/deficit-summary",
        params={"user_id": user_id, "local_date": local_date},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_kind"] == "body_budget_deficit_summary"
    assert payload["latest_weight_kg"] == 68.2
    assert payload["target_available"] is True
    assert payload["read_only"] is True
