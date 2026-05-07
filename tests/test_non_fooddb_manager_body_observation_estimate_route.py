from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application import build_active_body_plan_view
from app.body.application.body_observation_service import get_latest_weight_observation
from app.composition import intake_routes
from app.intake.application import chat_intents as intake_chat_intents
import app.intake.application as intake_application
from app.composition.onboarding_service import (
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from scripts.accurate_intake_body_observation_manager_fixture import BodyObservationManagerFixtureProvider


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _client(db: Session, provider: BodyObservationManagerFixtureProvider, monkeypatch: Any) -> TestClient:
    monkeypatch.setattr(intake_routes, "manager_provider", provider)
    monkeypatch.setattr(intake_routes, "search_provider", None)
    monkeypatch.setattr(intake_routes, "extract_provider", None)

    app = FastAPI()
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _bootstrap_user_with_plan(db: Session, *, user_external_id: str) -> int:
    user = get_or_create_user(db, user_external_id)
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
            local_date="2026-05-07",
            timezone="Asia/Taipei",
        ),
    )
    return int(user.id)


def test_estimate_route_records_weight_via_manager_tool_loop_without_direct_parser(monkeypatch: Any) -> None:
    db = _session()
    provider = BodyObservationManagerFixtureProvider()
    client = _client(db, provider, monkeypatch)
    user_external_id = "manager-body-observation-route"
    user_id = _bootstrap_user_with_plan(db, user_external_id=user_external_id)
    before_plan = build_active_body_plan_view(db, user_id=user_id)

    monkeypatch.setattr(
        intake_routes,
        "build_workflow_routing_decision",
        lambda **_: SimpleNamespace(
            target_workflow_family="body_observation",
            disposition="open_new_workflow",
            phase_a_trace={},
            required_read_surfaces=[],
        ),
    )

    async def _unexpected_parser(*_args: Any, **_kwargs: Any) -> dict[str, Any]:
        raise AssertionError("direct weight parser must not run on manager-owned body observation path")

    monkeypatch.setattr(intake_chat_intents, "parse_weight_or_budget_intent", _unexpected_parser)
    monkeypatch.setattr(intake_application, "parse_weight_or_budget_intent", _unexpected_parser)

    response = client.post(
        "/estimate",
        json={
            "text": "my weight is 70kg",
            "allow_search": False,
            "user_id": user_external_id,
            "local_date": "2026-05-07",
        },
    )

    after_plan = build_active_body_plan_view(db, user_id=user_id)
    latest_weight = get_latest_weight_observation(db, user_id=user_id, local_date="2026-05-07")

    assert response.status_code == 200
    assert provider.calls[0]["available_tools"] == ["body.record_observation"]
    assert provider.calls[0]["tool_results"] == []
    assert provider.calls[1]["tool_results"][0]["tool_name"] == "body.record_observation"
    assert provider.calls[1]["tool_results"][0]["provenance"]["canonical_tool_name"] == "body.record_observation"
    assert response.json()["coach_message"] == "Recorded weight 70.0 kg. Body plan was not changed."

    payload = response.json()["payload"]
    assert payload["manager_decision"]["intent_type"] == "body_observation"
    assert payload["manager_decision"]["workflow_effect"] == "record_weight"
    assert payload["state_delta"]["body_observation_recorded"] is True
    assert payload["state_delta"]["meal_logged"] is False
    assert payload["state_delta"]["canonical_commit"] is False
    assert payload["state_delta"]["ledger_updated"] is False

    assert latest_weight is not None
    assert latest_weight.value == 70.0
    assert latest_weight.unit == "kg"
    assert after_plan.body_plan_id == before_plan.body_plan_id
    assert after_plan.daily_budget_kcal == before_plan.daily_budget_kcal
    assert after_plan.recommended_target_kcal == before_plan.recommended_target_kcal
