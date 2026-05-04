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
from app.shared.infra.models import ProposalContainerRecord, ProposalOptionRecord


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


def test_calibration_preview_can_persist_open_proposal_artifact_without_plan_mutation() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-persist-preview")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    response = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-persist-preview",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
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
    proposal_id = payload["proposal_artifact"]["proposal_container_id"]
    proposal = db.get(ProposalContainerRecord, proposal_id)
    assert proposal is not None
    assert proposal.proposal_type == "calibration"
    assert proposal.proposal_status == "open"
    assert proposal.metadata_json["local_date"] == "2026-05-04"
    assert proposal.metadata_json["proposal_policy_packet"]["plan_mutation_authorized"] is False

    options = db.execute(
        select(ProposalOptionRecord).where(ProposalOptionRecord.proposal_container_id == proposal_id)
    ).scalars().all()
    assert len(options) >= 1
    assert proposal.top_option_id == options[0].id
    assert options[0].option_type == "budget_adjustment"
    assert options[0].effect_payload_json["new_daily_budget_kcal"] == 2000

    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


def test_stored_calibration_accept_uses_persisted_option_and_updates_same_proposal() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-stored-accept")
    baseline_plan = _active_body_plan(db, user_id=user.id)
    preview = client.post(
        "/calibration/proposal/preview",
        json={
            "user_id": "calibration-stored-accept",
            "local_date": "2026-05-04",
            "current_budget_status": "over_budget",
            "rescue_recovery_viability": "non_viable",
            "persist_proposal": True,
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
    proposal_id = preview.json()["proposal_artifact"]["proposal_container_id"]

    response = client.post(
        "/calibration/proposal/stored-action",
        json={
            "user_id": "calibration-stored-accept",
            "proposal_container_id": proposal_id,
            "action": "accept_calibration_proposal",
            "accepted_at": "2026-05-04T10:30:00",
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["proposal_container_id"] == proposal_id
    assert payload["proposal_status"] == "accepted"
    assert payload["effective_from"] == "2026-05-04"
    assert payload["current_budget_view"]["budget_kcal"] == 2000
    assert payload["active_body_plan_view"]["daily_budget_kcal"] == 2000

    proposals = db.execute(select(ProposalContainerRecord)).scalars().all()
    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert len(proposals) == 1
    assert proposals[0].id == proposal_id
    assert proposals[0].proposal_status == "accepted"
    assert len(plans) == 2
    assert plans[0].id == baseline_plan.id
    assert plans[0].plan_status == "superseded"
    assert plans[1].plan_status == "active"
    assert plans[1].daily_budget_kcal == 2000
    assert ledger.budget_kcal == 2000


def test_calibration_preview_blocks_duplicate_when_open_stored_proposal_exists() -> None:
    db = _session()
    client = _client(db)
    user = get_or_create_user(db, "calibration-duplicate-open")
    _active_body_plan(db, user_id=user.id)
    request_payload = {
        "user_id": "calibration-duplicate-open",
        "local_date": "2026-05-04",
        "current_budget_status": "over_budget",
        "rescue_recovery_viability": "non_viable",
        "persist_proposal": True,
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
    }

    first = client.post("/calibration/proposal/preview", json=request_payload)
    second = client.post("/calibration/proposal/preview", json=request_payload)

    assert first.status_code == 200
    assert second.status_code == 200
    second_payload = second.json()
    assert second_payload["gate_result"]["proposal_eligibility"] is False
    assert any(
        "similar calibration proposal is still open" in reason
        for reason in second_payload["gate_result"]["gate_rationale"]
    )
    assert second_payload["response"]["surfaced"] is False
    assert second_payload["proposal_artifact"] is None
    proposals = db.execute(select(ProposalContainerRecord)).scalars().all()
    assert len(proposals) == 1
    assert proposals[0].proposal_status == "open"
