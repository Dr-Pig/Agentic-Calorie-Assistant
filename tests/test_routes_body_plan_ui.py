from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.main import app
from app.models import Base
from app.routes import get_db as routes_get_db


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = testing_session()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_get_db] = override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.pop(routes_get_db, None)
        db.close()


@pytest.fixture()
def client(db_session):
    with TestClient(app) as test_client:
        yield test_client


def test_body_plan_routes_surface_active_bootstrap_truth(client, db_session) -> None:
    user = get_or_create_user(db_session, "body-plan-ui-user")
    bootstrap_body_plan_for_date(
        db_session,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=29,
            height_cm=164.0,
            current_weight_kg=57.0,
            activity_level="light",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
        ),
    )

    response_json = client.get("/body-plan/active", params={"user_id": "body-plan-ui-user"})
    response_html = client.get("/body-plan", params={"user_id": "body-plan-ui-user"})

    assert response_json.status_code == 200
    payload = response_json.json()
    assert payload["plan_status"] == "active"
    assert payload["goal_type"] == "lose_weight"
    assert payload["daily_budget_kcal"] > 0
    assert payload["recommended_target_kcal"] == payload["daily_budget_kcal"]
    assert payload["plan_source"] == "onboarding_bootstrap"

    assert response_html.status_code == 200
    assert "Active body-plan truth" in response_html.text
    assert "onboarding_bootstrap" in response_html.text
