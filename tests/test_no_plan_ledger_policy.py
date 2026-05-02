from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.database import get_or_create_user
from app.models import Base
from app.schemas import CommitRequestCandidate


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="no-plan-policy-meal",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="no plan sandwich",
        raw_input="no plan sandwich",
        estimated_kcal=420,
        protein_g=18,
        carb_g=32,
        fat_g=14,
        resolution_status="completed_meal",
        local_date="2026-05-02",
    )


def test_no_plan_meal_commit_does_not_create_day_budget_ledger_truth() -> None:
    db = _session()
    user = get_or_create_user(db, "no-plan-ledger-policy")

    result = commit_meal_payload_to_canonical(db, user=user, candidate=_candidate())

    assert result is not None
    assert db.execute(select(LedgerEntryRecord)).scalars().all()
    assert db.execute(select(DayBudgetLedgerRecord)).scalars().all() == []


def test_no_plan_budget_answer_remains_onboarding_required_after_meal_commit() -> None:
    db = _session()
    user = get_or_create_user(db, "no-plan-budget-answer")

    commit_meal_payload_to_canonical(db, user=user, candidate=_candidate())
    answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date="2026-05-02")

    assert answer.status == "onboarding_required"
    assert answer.consumed_kcal == 420
    assert answer.daily_target_kcal is None
    assert answer.remaining_kcal is None
