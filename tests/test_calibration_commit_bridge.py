from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.body.infrastructure.models import BodyPlanRecord
from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.calibration_commit_bridge import apply_calibration_proposal_commit
from app.database import get_or_create_user
from app.models import Base
from app.shared.infra.models import ProposalContainerRecord, ProposalOptionRecord


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _active_body_plan(db: Session, *, user_id: int) -> BodyPlanRecord:
    plan = BodyPlanRecord(
        user_id=user_id,
        plan_status="active",
        plan_label="baseline",
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


def _effect_payload(*, budget: int = 1650) -> dict[str, object]:
    return {
        "new_daily_budget_kcal": budget,
        "new_estimated_tdee_kcal": 2050,
        "review_after_days": 14,
        "rationale_summary": "accepted calibration test effect",
    }


def _counts(db: Session) -> dict[str, int]:
    return {
        "body_plans": len(db.execute(select(BodyPlanRecord)).scalars().all()),
        "day_ledgers": len(db.execute(select(DayBudgetLedgerRecord)).scalars().all()),
        "ledger_entries": len(db.execute(select(LedgerEntryRecord)).scalars().all()),
        "proposals": len(db.execute(select(ProposalContainerRecord)).scalars().all()),
        "proposal_options": len(db.execute(select(ProposalOptionRecord)).scalars().all()),
    }


@pytest.mark.parametrize("decision", ["rejected", "deferred_pending_reminder"])
def test_rejecting_or_deferring_plan_changing_calibration_only_commits_proposal_bookkeeping(decision: str) -> None:
    db = _session()
    user = get_or_create_user(db, f"calibration-{decision}")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-05-04",
        proposal_family="budget_adjustment",
        effect_payload=_effect_payload(),
        decision=decision,  # type: ignore[arg-type]
        accepted_at=datetime(2026, 5, 4, 10, 30, 0),
    )

    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert result.proposal_status == decision
    assert result.body_plan_id is None
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert active_plan.ended_at is None
    assert _counts(db) == {
        "body_plans": 1,
        "day_ledgers": 0,
        "ledger_entries": 0,
        "proposals": 1,
        "proposal_options": 1,
    }


def test_accepting_logging_quality_first_only_commits_proposal_bookkeeping() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-logging-quality")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-05-04",
        proposal_family="logging_quality_first",
        effect_payload={
            "logging_window_days": 7,
            "plan_change_required": False,
            "rationale_summary": "clean logging window",
        },
        decision="accepted",
        accepted_at=datetime(2026, 5, 4, 10, 30, 0),
    )

    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert result.proposal_status == "accepted"
    assert result.body_plan_id is None
    assert result.current_budget_view.budget_kcal == 1800
    assert result.current_budget_view.remaining_kcal == 1800
    assert active_plan.id == baseline_plan.id
    assert active_plan.daily_budget_kcal == 1800
    assert active_plan.ended_at is None
    assert _counts(db) == {
        "body_plans": 1,
        "day_ledgers": 0,
        "ledger_entries": 0,
        "proposals": 1,
        "proposal_options": 1,
    }


def test_rejected_plan_changing_proposal_returns_active_plan_budget_without_creating_ledger() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-rejected-budget-view")
    _active_body_plan(db, user_id=user.id)

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-05-04",
        proposal_family="budget_adjustment",
        effect_payload=_effect_payload(),
        decision="rejected",
        accepted_at=datetime(2026, 5, 4, 10, 30, 0),
    )

    assert result.current_budget_view.budget_kcal == 1800
    assert result.current_budget_view.remaining_kcal == 1800
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


@pytest.mark.parametrize("budget", [-100, 1100])
def test_accepting_budget_adjustment_with_invalid_daily_budget_rejects_before_side_effects(budget: int) -> None:
    db = _session()
    user = get_or_create_user(db, f"calibration-invalid-budget-{budget}")
    _active_body_plan(db, user_id=user.id)

    with pytest.raises(ValueError, match="new_daily_budget_kcal"):
        apply_calibration_proposal_commit(
            db,
            user=user,
            local_date="2026-05-04",
            proposal_family="budget_adjustment",
            effect_payload=_effect_payload(budget=budget),
            decision="accepted",
            accepted_at=datetime(2026, 5, 4, 10, 30, 0),
        )

    assert _counts(db) == {
        "body_plans": 1,
        "day_ledgers": 0,
        "ledger_entries": 0,
        "proposals": 0,
        "proposal_options": 0,
    }
    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.daily_budget_kcal == 1800


def test_accepting_budget_adjustment_with_missing_estimated_tdee_inherits_active_plan_tdee() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-missing-tdee-inherits")
    _active_body_plan(db, user_id=user.id)
    payload = _effect_payload()
    payload.pop("new_estimated_tdee_kcal")

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-05-04",
        proposal_family="budget_adjustment",
        effect_payload=payload,
        decision="accepted",
        accepted_at=datetime(2026, 5, 4, 10, 30, 0),
    )

    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    assert result.proposal_status == "accepted"
    assert len(plans) == 2
    assert plans[0].plan_status == "superseded"
    assert plans[1].plan_status == "active"
    assert plans[1].estimated_tdee == 2100
    assert plans[1].daily_budget_kcal == 1650


@pytest.mark.parametrize("estimated_tdee", ["not-a-number", 700])
def test_accepting_budget_adjustment_with_invalid_estimated_tdee_rejects_before_side_effects(
    estimated_tdee: object,
) -> None:
    db = _session()
    user = get_or_create_user(db, f"calibration-invalid-tdee-{estimated_tdee}")
    _active_body_plan(db, user_id=user.id)
    payload = _effect_payload()
    payload["new_estimated_tdee_kcal"] = estimated_tdee

    with pytest.raises(ValueError, match="new_estimated_tdee_kcal"):
        apply_calibration_proposal_commit(
            db,
            user=user,
            local_date="2026-05-04",
            proposal_family="budget_adjustment",
            effect_payload=payload,
            decision="accepted",
            accepted_at=datetime(2026, 5, 4, 10, 30, 0),
        )

    assert _counts(db) == {
        "body_plans": 1,
        "day_ledgers": 0,
        "ledger_entries": 0,
        "proposals": 0,
        "proposal_options": 0,
    }
    active_plan = db.execute(select(BodyPlanRecord).where(BodyPlanRecord.plan_status == "active")).scalar_one()
    assert active_plan.daily_budget_kcal == 1800


def test_accepting_pace_adjustment_without_estimated_tdee_inherits_tdee_and_updates_plan_and_ledger() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-pace-generated-shape")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-05-04",
        proposal_family="pace_adjustment",
        effect_payload={
            "new_daily_budget_kcal": 1950,
            "new_target_pace_kg_per_week": 0.4,
            "review_after_days": 21,
            "rationale_summary": "pace adjustment generated payload shape",
        },
        decision="accepted",
        accepted_at=datetime(2026, 5, 4, 10, 30, 0),
    )

    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert result.proposal_status == "accepted"
    assert result.body_plan_id is not None
    assert len(plans) == 2
    assert plans[0].id == baseline_plan.id
    assert plans[0].plan_status == "superseded"
    assert plans[1].plan_status == "active"
    assert plans[1].estimated_tdee == 2100
    assert plans[1].daily_budget_kcal == 1950
    assert plans[1].target_pace_kg_per_week == 0.4
    assert ledger.local_date == "2026-05-04"
    assert ledger.budget_kcal == 1950
    assert ledger.remaining_kcal == 1950


def test_accepting_budget_adjustment_creates_new_active_body_plan_and_refreshes_day_budget_ledger() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-budget-accept")
    baseline_plan = _active_body_plan(db, user_id=user.id)

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-05-04",
        proposal_family="budget_adjustment",
        effect_payload=_effect_payload(budget=1650),
        decision="accepted",
        accepted_at=datetime(2026, 5, 4, 10, 30, 0),
    )

    plans = db.execute(select(BodyPlanRecord).order_by(BodyPlanRecord.id.asc())).scalars().all()
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert result.proposal_status == "accepted"
    assert result.body_plan_id is not None
    assert len(plans) == 2
    assert plans[0].id == baseline_plan.id
    assert plans[0].plan_status == "superseded"
    assert plans[1].plan_status == "active"
    assert plans[1].daily_budget_kcal == 1650
    assert ledger.local_date == "2026-05-04"
    assert ledger.budget_kcal == 1650
    assert ledger.remaining_kcal == 1650
    assert db.execute(select(LedgerEntryRecord)).scalars().all() == []
