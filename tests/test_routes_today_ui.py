from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_or_create_user, save_meal_log
from app.main import app
from app.models import Base
from app.routes import get_db as routes_get_db
from app.schemas import CommitRequestCandidate
from app.application.canonical_commit_bridge import commit_request_candidate_to_canonical
from app.infrastructure.canonical_persistence import commit_meal_payload_to_canonical


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


def test_today_current_budget_ignores_legacy_meal_logs(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-legacy")
    save_meal_log(
        db_session,
        user,
        meal_title="legacy raw bowl",
        raw_input="legacy raw bowl",
        kcal=999,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        components=[{"name": "legacy raw bowl"}],
        debug_steps=[],
        status="completed_meal",
    )

    response = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-legacy", "local_date": "2026-04-11"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == user.id
    assert payload["local_date"] == "2026-04-11"
    assert payload["budget_kcal"] == 0
    assert payload["consumed_kcal"] == 0
    assert payload["remaining_kcal"] == 0
    assert payload["active_meal_count"] == 0
    assert payload["meals"] == []


def test_today_surface_renders_canonical_current_budget(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-canonical")
    commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-req-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="egg sandwich",
            raw_input="egg sandwich",
            estimated_kcal=350,
            protein_g=12,
            carb_g=28,
            fat_g=14,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 8, 30),
            local_date="2026-04-11",
        ),
        budget_kcal=1200,
    )

    response = client.get("/today", params={"user_id": "today-ui-canonical", "local_date": "2026-04-11"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Today Surface" in response.text
    assert "source: current_budget_read_model" in response.text
    assert "egg sandwich" in response.text
    assert "350 kcal" in response.text
    assert "1200" in response.text
    assert "current-budget read model" in response.text


def test_today_surface_stays_on_active_version_after_correction(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-correction")
    first = commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-req-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="noodle bowl",
            raw_input="noodle bowl",
            estimated_kcal=610,
            protein_g=22,
            carb_g=68,
            fat_g=20,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 12, 0),
            local_date="2026-04-11",
        ),
        budget_kcal=1200,
    )
    assert first is not None

    commit_request_candidate_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-req-2",
            planner_intent="modification",
            meal_thread_id=first.meal_thread_id,
            parent_version_id=first.meal_version_id,
            version_reason="historical_correction",
            meal_title="grilled tofu plate",
            raw_input="grilled tofu plate",
            estimated_kcal=540,
            protein_g=20,
            carb_g=60,
            fat_g=18,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 12, 10),
            local_date="2026-04-11",
        ),
    )

    response_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-correction", "local_date": "2026-04-11"},
    )
    response_html = client.get(
        "/today",
        params={"user_id": "today-ui-correction", "local_date": "2026-04-11"},
    )

    assert response_json.status_code == 200
    payload = response_json.json()
    assert payload["consumed_kcal"] == 540
    assert payload["active_meal_count"] == 1
    assert [meal["meal_title"] for meal in payload["meals"]] == ["grilled tofu plate"]
    assert payload["meals"][0]["meal_version_id"] is not None

    assert response_html.status_code == 200
    assert "grilled tofu plate" in response_html.text
    assert "540 kcal" in response_html.text
    assert "noodle bowl" not in response_html.text


def test_today_surface_keeps_canonical_local_day_after_cross_midnight_correction(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-midnight")
    first = commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-midnight-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="late dinner",
            raw_input="late dinner",
            estimated_kcal=510,
            protein_g=18,
            carb_g=60,
            fat_g=16,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 23, 55),
            local_date="2026-04-11",
        ),
        budget_kcal=1200,
    )
    assert first is not None

    commit_request_candidate_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-midnight-2",
            planner_intent="modification",
            meal_thread_id=first.meal_thread_id,
            parent_version_id=first.meal_version_id,
            version_reason="historical_correction",
            meal_title="late dinner corrected",
            raw_input="late dinner corrected",
            estimated_kcal=470,
            protein_g=17,
            carb_g=54,
            fat_g=15,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 12, 0, 5),
            local_date="2026-04-11",
        ),
    )

    same_day_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-midnight", "local_date": "2026-04-11"},
    )
    next_day_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-midnight", "local_date": "2026-04-12"},
    )
    same_day_html = client.get("/today", params={"user_id": "today-ui-midnight", "local_date": "2026-04-11"})

    assert same_day_json.status_code == 200
    same_day_payload = same_day_json.json()
    assert same_day_payload["local_date"] == "2026-04-11"
    assert same_day_payload["consumed_kcal"] == 470
    assert same_day_payload["active_meal_count"] == 1
    assert [meal["meal_title"] for meal in same_day_payload["meals"]] == ["late dinner corrected"]

    assert next_day_json.status_code == 200
    next_day_payload = next_day_json.json()
    assert next_day_payload["local_date"] == "2026-04-12"
    assert next_day_payload["consumed_kcal"] == 0
    assert next_day_payload["active_meal_count"] == 0
    assert next_day_payload["meals"] == []

    assert same_day_html.status_code == 200
    assert "late dinner corrected" in same_day_html.text
    assert "470 kcal" in same_day_html.text
    assert "2026-04-11" in same_day_html.text
    assert "source: current_budget_read_model" in same_day_html.text
