from __future__ import annotations

import asyncio
from types import SimpleNamespace

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.body.application import build_active_body_plan_view
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.models import Base
from app.schemas import EstimateRequest


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_estimate_body_observation_route_does_not_silently_rebootstrap_body_plan(monkeypatch) -> None:
    from app.composition import intake_routes

    db = _session()
    user = get_or_create_user(db, "estimate-body-observation-user")
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

    monkeypatch.setattr(intake_routes, "resolve_v2_bundle1_state", lambda *_, **__: SimpleNamespace())
    monkeypatch.setattr(intake_routes, "build_current_turn_context_v1", lambda *_, **__: SimpleNamespace())
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

    async def _parse_weight(_provider, _text):
        return {"weight_kg": 70.0}

    monkeypatch.setattr(intake_routes, "parse_weight_or_budget_intent", _parse_weight)

    response = asyncio.run(
        intake_routes.estimate(
            EstimateRequest(text="my weight is 70kg", user_id="estimate-body-observation-user"),
            raw_request=SimpleNamespace(headers={}),
            db=db,
        )
    )
    after = build_active_body_plan_view(db, user_id=user.id)

    assert response["payload"] is None
    assert after.body_plan_id == before.body_plan_id
    assert after.daily_budget_kcal == before.daily_budget_kcal
    assert after.recommended_target_kcal == before.recommended_target_kcal
    assert after.current_weight_kg == before.current_weight_kg
