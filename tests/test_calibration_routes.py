from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.infrastructure.models import BodyPlanRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.calibration_routes import router as calibration_router
from app.database import get_db, get_or_create_user
from app.models import Base
from app.shared.infra.models import ProposalContainerRecord


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
    app.include_router(calibration_router)

    def override_get_db():
        yield db

    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def _active_body_plan(db: Session, *, user_id: int) -> BodyPlanRecord:
    plan = BodyPlanRecord(
        user_id=user_id,
        plan_status="active",
        plan_label="route baseline",
        estimated_tdee=2100,
        daily_budget_kcal=1800,
        safety_floor_kcal=1200,
        target_pace_kg_per_week=0.5,
        metadata_json={"recommended_target_kcal": 1800, "plan_source": "test_baseline"},
        started_at=datetime(2026, 5, 1, 8, 0, 0),
        created_at=datetime(2026, 5, 1, 8, 0, 0),
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def test_calibration_preview_route_preserves_existing_fields_and_adds_diagnostic_packet() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-preview-route")
    _active_body_plan(db, user_id=user.id)

    response = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-preview-route",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "model_inputs": {
                "body_plan_estimated_tdee_kcal": 2100,
                "observation_window_days": 21,
                "body_observation_count": 9,
                "intake_coverage": 0.93,
                "operating_expenditure_shift_kcal": 340,
                "trend_mismatch_consistency": 0.9,
                "trend_volatility": 0.1,
                "logging_gap_ratio": 0.05,
                "late_logged_meal_ratio": 0.05,
            },
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert {"calibration_result", "gate_result", "response"} <= set(payload)
    assert {"diagnostic", "proposal_policy_packet", "trace_envelope"} <= set(payload)
    assert payload["calibration_result"]["calibration_posture"] == "high_confidence_mismatch"
    assert payload["gate_result"]["proposal_eligibility"] is True
    assert payload["response"]["proposal_family"] == "budget_adjustment"
    assert payload["proposal_policy_packet"]["proposal_family"] == "budget_adjustment"
    assert payload["proposal_policy_packet"]["plan_change_required"] is True
    assert payload["proposal_policy_packet"]["plan_mutation_authorized"] is False
    assert payload["proposal_policy_packet"]["ledger_mutation_authorized"] is False
    assert payload["trace_envelope"]["automatic_calibration_enabled"] is False
    assert payload["trace_envelope"]["live_tool_calling"] is False
    assert payload["diagnostic"]["proposal_policy_packet"] == payload["proposal_policy_packet"]
    assert payload["diagnostic"]["trace_envelope"] == payload["trace_envelope"]
    assert db.execute(select(ProposalContainerRecord)).scalars().all() == []
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []
