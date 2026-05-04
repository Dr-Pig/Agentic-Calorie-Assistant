from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.body.application.calibration_model import CalibrationModelInputs
from app.body.infrastructure.models import BodyPlanRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.calibration_preview_service import build_calibration_preview_from_model_inputs
from app.database import get_or_create_user
from app.models import Base
from app.shared.infra.models import ProposalContainerRecord


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _active_body_plan(db: Session, *, user_id: int) -> BodyPlanRecord:
    plan = BodyPlanRecord(
        user_id=user_id,
        plan_status="active",
        plan_label="preview service baseline",
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


def _model_inputs() -> CalibrationModelInputs:
    return CalibrationModelInputs(
        body_plan_estimated_tdee_kcal=2100,
        observation_window_days=21,
        body_observation_count=9,
        intake_coverage=0.93,
        operating_expenditure_shift_kcal=340,
        trend_mismatch_consistency=0.9,
        trend_volatility=0.1,
        logging_gap_ratio=0.05,
        late_logged_meal_ratio=0.05,
    )


def test_calibration_preview_persistence_requires_clean_session() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-preview-clean-session")
    _active_body_plan(db, user_id=user.id)
    dirty_ledger = DayBudgetLedgerRecord(
        user_id=user.id,
        local_date="2026-05-14",
        budget_kcal=1800,
        consumed_kcal=0,
        adjustment_kcal=0,
        remaining_kcal=1800,
    )
    db.add(dirty_ledger)

    with pytest.raises(ValueError, match="calibration_proposal_persistence_requires_clean_session"):
        build_calibration_preview_from_model_inputs(
            db,
            user=user,
            local_date="2026-05-14",
            model_inputs=_model_inputs(),
            current_budget_status="over_budget",
            rescue_recovery_viability="non_viable",
            persist_proposal=True,
        )

    assert db.query(ProposalContainerRecord).count() == 0
    assert dirty_ledger in db.new


def test_calibration_preview_persistence_rejects_dirty_existing_proposal_session_state() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-preview-clean-proposal-session")
    _active_body_plan(db, user_id=user.id)
    existing = ProposalContainerRecord(
        user_id=user.id,
        proposal_type="calibration",
        proposal_status="open",
        metadata_json={"local_date": "2026-05-13"},
    )
    db.add(existing)
    db.commit()
    existing.proposal_status = "negotiating"

    with pytest.raises(ValueError, match="calibration_proposal_persistence_requires_clean_session"):
        build_calibration_preview_from_model_inputs(
            db,
            user=user,
            local_date="2026-05-14",
            model_inputs=_model_inputs(),
            current_budget_status="over_budget",
            rescue_recovery_viability="non_viable",
            persist_proposal=True,
        )

    proposals = db.query(ProposalContainerRecord).all()
    assert len(proposals) == 1
    assert existing in db.dirty
