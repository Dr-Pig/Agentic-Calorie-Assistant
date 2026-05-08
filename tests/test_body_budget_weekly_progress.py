from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application.body_observation_service import record_body_observation_to_canonical
from app.composition.body_budget_weekly_progress import build_body_budget_weekly_progress
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.composition.today_routes import router as today_router
from app.database import get_db, get_or_create_user
from app.models import Base, BodyPlanRecord, DayBudgetLedgerRecord
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
    app.include_router(today_router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


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


def _commit_meal(db: Session, *, user_id: str, local_date: str, kcal: int) -> None:
    user = get_or_create_user(db, user_id)
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id=f"{user_id}-{local_date}-meal",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title=f"meal {local_date}",
            raw_input="test meal",
            estimated_kcal=kcal,
            protein_g=7,
            carb_g=1,
            fat_g=5,
            resolution_status="completed_meal",
            local_date=local_date,
        ),
    )


def _seed_week(db: Session, *, user_id: str):
    user = _bootstrap_user(db, user_id=user_id, local_date="2026-05-01")
    for offset, kcal in enumerate([1500, 1600, 1700, 1800, 1900, 0, 1300]):
        if kcal > 0:
            local_date = (datetime(2026, 5, 1) + timedelta(days=offset)).date().isoformat()
            _commit_meal(db, user_id=user_id, local_date=local_date, kcal=kcal)
    record_body_observation_to_canonical(
        db,
        user=user,
        value=70.2,
        observed_at=datetime(2026, 5, 1, 7, 0, 0),
        local_date="2026-05-01",
    )
    record_body_observation_to_canonical(
        db,
        user=user,
        value=69.8,
        observed_at=datetime(2026, 5, 4, 22, 0, 0),
        local_date="2026-05-04",
    )
    record_body_observation_to_canonical(
        db,
        user=user,
        value=69.7,
        observed_at=datetime(2026, 5, 7, 7, 0, 0),
        local_date="2026-05-07",
    )
    record_body_observation_to_canonical(
        db,
        user=user,
        value=69.5,
        observed_at=datetime(2026, 5, 7, 22, 0, 0),
        local_date="2026-05-07",
    )
    return user


def test_body_budget_weekly_progress_reads_seven_day_deficit_and_weight_loop_without_mutation() -> None:
    db = _session()
    user = _seed_week(db, user_id="weekly-progress")
    before_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()

    report = build_body_budget_weekly_progress(db, user_id=user.id, local_date="2026-05-07")

    assert report["source_kind"] == "body_budget_weekly_progress"
    assert report["read_only"] is True
    assert report["window_days"] == 7
    assert report["window_start_date"] == "2026-05-01"
    assert report["window_end_date"] == "2026-05-07"
    assert [day["local_date"] for day in report["days"]] == [
        "2026-05-01",
        "2026-05-02",
        "2026-05-03",
        "2026-05-04",
        "2026-05-05",
        "2026-05-06",
        "2026-05-07",
    ]
    assert report["logged_day_count"] == 6
    assert report["weight_observation_count"] == 4
    assert report["first_weight_kg"] == 70.2
    assert report["latest_weight_kg"] == 69.5
    assert report["weight_delta_kg"] == -0.7
    assert report["total_consumed_kcal"] == 9800
    assert report["total_remaining_kcal"] == sum(day["remaining_kcal"] for day in report["days"])
    assert report["estimated_weekly_deficit_kcal"] == sum(
        day["estimated_daily_deficit_kcal"] for day in report["days"]
    )
    assert report["days"][5]["active_meal_count"] == 0
    assert report["days"][5]["consumed_kcal"] == 0
    assert report["days"][5]["target_source"] == "active_body_plan"
    assert report["automatic_calibration_enabled"] is False
    assert report["rescue_enabled"] is False
    assert report["recommendation_enabled"] is False
    assert report["proactive_enabled"] is False
    assert db.query(BodyPlanRecord).count() == before_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count


def test_today_weekly_progress_route_returns_backend_read_model() -> None:
    db = _session()
    client = _client(db)
    _seed_week(db, user_id="weekly-progress-route")

    response = client.get(
        "/today/weekly-progress",
        params={"user_id": "weekly-progress-route", "local_date": "2026-05-07"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["source_kind"] == "body_budget_weekly_progress"
    assert payload["window_start_date"] == "2026-05-01"
    assert payload["window_end_date"] == "2026-05-07"
    assert payload["read_only"] is True
    assert payload["latest_weight_kg"] == 69.5


def test_bodybudget_current_shell_matrix_lists_weekly_progress_as_backend_owned_read_model() -> None:
    matrix = Path("docs/specs/UI_CANONICAL_TRUTH_SURFACE_MATRIX.md")
    text = matrix.read_text(encoding="utf-8-sig")

    assert "`body_budget_weekly_progress`" in text
    assert "/today/weekly-progress" in text
    assert "Do not compute weekly deficit, weight delta, or logged-day coverage in CurrentShell" in text
