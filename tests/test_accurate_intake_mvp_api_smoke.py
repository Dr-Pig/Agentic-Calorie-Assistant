from __future__ import annotations

import secrets

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from pathlib import Path

from sqlalchemy.orm import Session, sessionmaker

from app.composition import intake_routes
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from scripts.run_accurate_intake_mvp_manager_style_smoke import DeterministicSelfUseManagerProvider


def _session(db_path: Path) -> Session:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _seed_body_plan(db: Session, *, user_external_id: str, local_date: str) -> None:
    user = get_or_create_user(db, user_external_id)
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=34,
            height_cm=170,
            current_weight_kg=70,
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            timezone="Asia/Taipei",
            daily_lifestyle="sedentary_with_some_walking",
            weekly_exercise_days_band="1_2",
            local_date=local_date,
        ),
    )


def _client(db: Session, monkeypatch) -> tuple[TestClient, DeterministicSelfUseManagerProvider]:
    provider = DeterministicSelfUseManagerProvider()
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app), provider


def test_estimate_route_closes_manager_style_product_loop_against_debug_surface(monkeypatch, tmp_path: Path) -> None:
    debug_token = secrets.token_urlsafe(24)
    monkeypatch.setenv("LOCAL_DEBUG_API_TOKEN", debug_token)
    db = _session(tmp_path / "api-smoke.sqlite3")
    user_external_id = "api-smoke-user"
    local_date = "2026-05-02"
    _seed_body_plan(db, user_external_id=user_external_id, local_date=local_date)
    client, provider = _client(db, monkeypatch)

    initial_response = client.post(
        "/estimate",
        json={"text": "chicken sandwich", "allow_search": False, "user_id": user_external_id},
    )
    assert initial_response.status_code == 200
    initial_payload = initial_response.json()["payload"]
    assert initial_payload["state_delta"]["canonical_commit"] is True
    assert initial_payload["intake_execution_manager"]["final"]["final_action"] == "commit"
    route_local_date = initial_payload["remaining_budget"]["local_date"]

    correction_response = client.post(
        "/estimate",
        json={"text": "the chicken sandwich was smaller", "allow_search": False, "user_id": user_external_id},
    )
    assert correction_response.status_code == 200
    correction_payload = correction_response.json()["payload"]
    assert correction_payload["state_delta"]["canonical_commit"] is True
    assert correction_payload["state_delta"]["old_version_superseded"] is True
    assert correction_payload["intake_execution_manager"]["final"]["final_action"] == "correction_applied"

    query_response = client.post(
        "/estimate",
        json={"text": "how much have I eaten today", "allow_search": False, "user_id": user_external_id},
    )
    assert query_response.status_code == 200
    query_payload = query_response.json()["payload"]
    assert query_payload["state_delta"]["canonical_commit"] is False
    assert query_payload["manager_decision"]["intent_type"] == "answer_remaining_budget"

    debug_response = client.get(
        "/accurate-intake/debug",
        params={"user_id": user_external_id, "local_date": route_local_date},
        headers={"X-Local-Debug-Token": debug_token},
    )
    assert debug_response.status_code == 200
    debug_payload = debug_response.json()
    model = debug_payload["model"]
    assert debug_payload["read_only"] is True
    assert model["today_summary"]["consumed_kcal"] > 0
    assert model["same_truth"]["status"] == "pass"
    assert provider.readiness()["live_llm_invoked"] is False
    assert any(
        "estimate_nutrition" in call["available_tools"]
        for call in provider.calls
    )
