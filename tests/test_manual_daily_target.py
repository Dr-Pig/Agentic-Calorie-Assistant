from __future__ import annotations

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.manual_daily_target_service import ManualDailyTargetInput, set_manual_daily_target
from app.database import get_db, get_or_create_user
from app.models import Base
from app.routes import router
from app.schemas import CommitRequestCandidate


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
    app.include_router(router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _commit_meal(db: Session, *, user_external_id: str, local_date: str, kcal: int) -> None:
    user = get_or_create_user(db, user_external_id)
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id=f"{user_external_id}-meal",
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


def test_manual_daily_target_creates_plan_and_refreshes_current_budget_truth() -> None:
    db = _session()
    user_external_id = "manual-target-create"
    local_date = "2026-05-03"
    _commit_meal(db, user_external_id=user_external_id, local_date=local_date, kcal=350)
    user = get_or_create_user(db, user_external_id)

    result = set_manual_daily_target(
        db,
        user=user,
        inputs=ManualDailyTargetInput(
            daily_target_kcal=1600,
            local_date=local_date,
            source="user_chat",
        ),
    )

    assert result.active_body_plan_view.daily_budget_kcal == 1600
    assert result.active_body_plan_view.recommended_target_kcal == 1600
    assert result.active_body_plan_view.plan_source == "manual_daily_target"
    assert result.current_budget_view.budget_kcal == 1600
    assert result.current_budget_view.consumed_kcal == 350
    assert result.current_budget_view.remaining_kcal == 1250
    assert result.product_readiness_claimed is False
    assert result.production_selected is False


def test_manual_daily_target_updates_existing_plan_without_recomputing_consumed_truth() -> None:
    db = _session()
    user_external_id = "manual-target-update"
    local_date = "2026-05-03"
    user = get_or_create_user(db, user_external_id)
    set_manual_daily_target(
        db,
        user=user,
        inputs=ManualDailyTargetInput(daily_target_kcal=1800, local_date=local_date, source="user_ui"),
    )
    _commit_meal(db, user_external_id=user_external_id, local_date=local_date, kcal=420)

    result = set_manual_daily_target(
        db,
        user=user,
        inputs=ManualDailyTargetInput(
            daily_target_kcal=1500,
            local_date=local_date,
            source="user_ui",
        ),
    )

    assert result.active_body_plan_view.daily_budget_kcal == 1500
    assert result.current_budget_view.budget_kcal == 1500
    assert result.current_budget_view.consumed_kcal == 420
    assert result.current_budget_view.remaining_kcal == 1080
    assert result.target_delta_kcal == -300


def test_manual_daily_target_route_updates_body_plan_and_today_budget_same_truth() -> None:
    db = _session()
    client = _client(db)
    user_external_id = "manual-target-route"
    local_date = "2026-05-03"
    _commit_meal(db, user_external_id=user_external_id, local_date=local_date, kcal=250)

    response = client.post(
        "/body-plan/manual-daily-target",
        json={
            "user_id": user_external_id,
            "daily_target_kcal": 1700,
            "local_date": local_date,
            "source": "user_ui",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["active_body_plan"]["daily_budget_kcal"] == 1700
    assert payload["current_budget"]["budget_kcal"] == 1700
    assert payload["current_budget"]["consumed_kcal"] == 250
    assert payload["current_budget"]["remaining_kcal"] == 1450
    assert payload["product_readiness_claimed"] is False

    today = client.get(
        "/today/current-budget",
        params={"user_id": user_external_id, "local_date": local_date},
    )
    body_plan = client.get("/body-plan/active", params={"user_id": user_external_id})

    assert today.status_code == 200
    assert body_plan.status_code == 200
    assert today.json()["budget_kcal"] == body_plan.json()["daily_budget_kcal"] == 1700
    assert today.json()["remaining_kcal"] == 1450
