from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import DayBudgetLedgerRecord
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _candidate(*, request_id: str, kcal: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id=request_id,
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title=request_id,
        raw_input=request_id,
        estimated_kcal=kcal,
        resolution_status="completed_meal",
        local_date="2026-05-02",
    )


def test_current_budget_view_derives_current_consumed_truth_from_active_meal_versions_not_stale_ledger() -> None:
    db = _session()
    user = get_or_create_user(db, "ledger-truth-active-version")
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(request_id="first meal", kcal=400),
        budget_kcal=1800,
    )
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    ledger.consumed_kcal = 999
    ledger.remaining_kcal = 801
    db.commit()

    view = build_current_budget_view(db, user_id=user.id, local_date="2026-05-02")

    assert view.consumed_kcal == 400
    assert view.remaining_kcal == 1400


def test_current_budget_view_excludes_superseded_versions_from_current_consumed_truth() -> None:
    db = _session()
    user = get_or_create_user(db, "ledger-truth-superseded")
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_candidate(request_id="initial meal", kcal=650),
        budget_kcal=1800,
    )
    assert initial is not None
    target_item = db.execute(
        select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
    ).scalar_one()
    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="corrected meal",
            manager_intent="food_estimation",
            meal_thread_id=initial.meal_thread_id,
            version_reason="correction",
            meal_title="corrected meal",
            raw_input="corrected meal",
            estimated_kcal=470,
            resolution_status="completed_meal",
            local_date="2026-05-02",
            items=[MealItemPayload(name="corrected meal", estimated_kcal=470)],
            trace_ref={
                "correction_target_ref": {
                    "meal_thread_id": initial.meal_thread_id,
                    "meal_item_id": target_item.id,
                    "canonical_name": "initial meal",
                }
            },
        ),
        budget_kcal=1800,
    )

    assert correction is not None
    view = build_current_budget_view(db, user_id=user.id, local_date="2026-05-02")

    assert view.consumed_kcal == 470
    assert view.remaining_kcal == 1330
