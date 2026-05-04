from __future__ import annotations

import asyncio
from datetime import datetime

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application import build_active_body_plan_view
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.composition.weight_routes import WeightObservationRequest, post_weight_observation, router as weight_router
from app.database import get_db, get_or_create_user
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


def _client(db: Session) -> TestClient:
    app = FastAPI()
    app.include_router(weight_router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


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
    before_ledgers = db.execute(
        select(DayBudgetLedgerRecord)
        .where(DayBudgetLedgerRecord.user_id == user.id)
        .order_by(DayBudgetLedgerRecord.local_date.asc(), DayBudgetLedgerRecord.id.asc())
    ).scalars().all()
    before_ledger_snapshot = [
        (ledger.local_date, ledger.budget_kcal, ledger.consumed_kcal, ledger.adjustment_kcal, ledger.remaining_kcal)
        for ledger in before_ledgers
    ]

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
    after_ledgers = db.execute(
        select(DayBudgetLedgerRecord)
        .where(DayBudgetLedgerRecord.user_id == user.id)
        .order_by(DayBudgetLedgerRecord.local_date.asc(), DayBudgetLedgerRecord.id.asc())
    ).scalars().all()
    after_ledger_snapshot = [
        (ledger.local_date, ledger.budget_kcal, ledger.consumed_kcal, ledger.adjustment_kcal, ledger.remaining_kcal)
        for ledger in after_ledgers
    ]

    assert response["status"] == "ok"
    assert response["recomputed_target_kcal"] is None
    assert response["observed_at"] is not None
    assert response["local_date"] == "2026-04-19"
    assert response["observation"]["unit"] == "kg"
    assert after.body_plan_id == before.body_plan_id
    assert after.daily_budget_kcal == before.daily_budget_kcal
    assert after.recommended_target_kcal == before.recommended_target_kcal
    assert after.current_weight_kg == before.current_weight_kg
    assert after_ledger_snapshot == before_ledger_snapshot
    assert {ledger.local_date for ledger in after_ledgers} == {"2026-04-18"}


def test_weight_observation_route_preserves_explicit_observed_at_and_derives_local_date() -> None:
    db = _session()
    observed_at = datetime(2026, 4, 20, 21, 45, 0)

    response = asyncio.run(
        post_weight_observation(
            WeightObservationRequest(
                user_id="weight-time-policy-user",
                weight_kg=68.4,
                observed_at=observed_at,
            ),
            db=db,
        )
    )

    assert response["status"] == "ok"
    assert response["observed_at"] == observed_at.isoformat()
    assert response["local_date"] == "2026-04-20"
    assert response["observation"]["observed_at"] == observed_at.isoformat()
    assert response["observation"]["local_date"] == "2026-04-20"


def test_weight_observation_route_rejects_lb_unit_without_conversion() -> None:
    db = _session()
    client = _client(db)

    response = client.post(
        "/weight/observation",
        json={
            "user_id": "weight-unit-boundary-user",
            "weight_kg": 160.0,
            "unit": "lb",
            "local_date": "2026-04-21",
        },
    )

    assert response.status_code == 422
    assert "kg" in response.json()["detail"]


@pytest.mark.parametrize("unit", [None, "", "kg", " KG ", "Kg"])
def test_weight_observation_route_normalizes_empty_or_kg_unit(unit: str | None) -> None:
    db = _session()
    client = _client(db)
    payload = {
        "user_id": f"weight-unit-{unit!r}",
        "weight_kg": 69.0,
        "local_date": "2026-04-21",
    }
    if unit is not None:
        payload["unit"] = unit

    response = client.post("/weight/observation", json=payload)

    assert response.status_code == 200
    body = response.json()
    assert body["unit"] == "kg"
    assert body["observation"]["unit"] == "kg"
