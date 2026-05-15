from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import DayBudgetLedgerRecord, LedgerEntryRecord
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _initial_candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="correction-uow-initial",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="lunch plate",
        raw_input="chicken rice and soup",
        estimated_kcal=650,
        protein_g=35,
        carb_g=70,
        fat_g=18,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[
            MealItemPayload(name="chicken rice", estimated_kcal=500, protein_g=32, carb_g=65, fat_g=15),
            MealItemPayload(name="soup", estimated_kcal=150, protein_g=3, carb_g=5, fat_g=3),
        ],
    )


def _correction_candidate(*, meal_thread_id: int, meal_item_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="correction-uow-update",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="the chicken rice was smaller",
        estimated_kcal=470,
        protein_g=30,
        carb_g=55,
        fat_g=12,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[
            MealItemPayload(name="chicken rice", estimated_kcal=320, protein_g=27, carb_g=50, fat_g=9),
        ],
        trace_ref={
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": "chicken rice",
            }
        },
    )


def _removal_candidate(*, meal_thread_id: int, meal_item_id: int, canonical_name: str = "chicken rice") -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="correction-uow-remove-item",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="remove the chicken rice",
        estimated_kcal=150,
        protein_g=3,
        carb_g=5,
        fat_g=3,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[],
        trace_ref={
            "correction_operation": "remove_item",
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": canonical_name,
            },
        },
    )


def _thread_level_correction_candidate(*, meal_thread_id: int, meal_version_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="correction-uow-thread-level-update",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="replace the whole lunch with a smaller plate",
        estimated_kcal=360,
        protein_g=22,
        carb_g=44,
        fat_g=10,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[
            MealItemPayload(name="half chicken rice", estimated_kcal=260, protein_g=20, carb_g=40, fat_g=8),
            MealItemPayload(name="soup", estimated_kcal=100, protein_g=2, carb_g=4, fat_g=2),
        ],
        trace_ref={
            "correction_operation": "correct_meal",
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_version_id": meal_version_id,
                "operation": "correct_meal",
            },
        },
    )


def _items_for_version(db: Session, version_id: int) -> list[MealItemRecord]:
    return db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()


def test_item_level_correction_replaces_target_item_and_preserves_non_target_items() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-preserve")
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_initial_candidate(),
        budget_kcal=1800,
    )
    assert initial is not None
    old_items = _items_for_version(db, initial.meal_version_id)

    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_correction_candidate(
            meal_thread_id=initial.meal_thread_id,
            meal_item_id=old_items[0].id,
        ),
        budget_kcal=1800,
    )

    assert correction is not None
    assert correction.superseded_version_id == initial.meal_version_id
    thread = db.get(MealThreadRecord, initial.meal_thread_id)
    assert thread is not None
    assert thread.active_version_id == correction.meal_version_id
    old_version = db.get(MealVersionRecord, initial.meal_version_id)
    assert old_version is not None
    assert old_version.version_status == "superseded"

    new_items = _items_for_version(db, correction.meal_version_id)
    assert [(item.name, item.estimated_kcal) for item in new_items] == [
        ("chicken rice", 320),
        ("soup", 150),
    ]
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert ledger.consumed_kcal == 470
    assert ledger.remaining_kcal == 1330


def test_item_level_correction_keeps_ledger_audit_as_event_not_current_truth() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-audit-event")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None
    old_items = _items_for_version(db, initial.meal_version_id)

    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_correction_candidate(meal_thread_id=initial.meal_thread_id, meal_item_id=old_items[0].id),
        budget_kcal=1800,
    )

    assert correction is not None
    audit_events = db.execute(
        select(LedgerEntryRecord).where(LedgerEntryRecord.entry_type == "meal_consumption")
    ).scalars().all()
    assert [event.delta_kcal for event in audit_events] == [650, 470]
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert ledger.consumed_kcal == 470


def test_item_level_correction_requires_explicit_target_reference() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-requires-target")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None

    missing_target = CommitRequestCandidate(
        request_id="correction-uow-missing-target",
        manager_intent="food_estimation",
        meal_thread_id=initial.meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="the lunch was smaller",
        estimated_kcal=470,
        protein_g=30,
        carb_g=55,
        fat_g=12,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[MealItemPayload(name="lunch plate", estimated_kcal=470, protein_g=30, carb_g=55, fat_g=12)],
    )

    with pytest.raises(ValueError, match="correction_requires_explicit_item_target"):
        commit_meal_payload_to_canonical(db, user=user, candidate=missing_target, budget_kcal=1800)

    db.expire_all()
    thread = db.get(MealThreadRecord, initial.meal_thread_id)
    assert thread is not None
    assert thread.active_version_id == initial.meal_version_id
    assert len(db.execute(select(MealVersionRecord)).scalars().all()) == 1
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert ledger.consumed_kcal == 650


def test_thread_level_correction_replaces_whole_meal_without_item_target() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-thread-level")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None

    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_thread_level_correction_candidate(
            meal_thread_id=initial.meal_thread_id,
            meal_version_id=initial.meal_version_id,
        ),
        budget_kcal=1800,
    )

    assert correction is not None
    assert correction.superseded_version_id == initial.meal_version_id
    thread = db.get(MealThreadRecord, initial.meal_thread_id)
    assert thread is not None
    assert thread.active_version_id == correction.meal_version_id
    old_version = db.get(MealVersionRecord, initial.meal_version_id)
    assert old_version is not None
    assert old_version.version_status == "superseded"

    new_items = _items_for_version(db, correction.meal_version_id)
    assert [(item.name, item.estimated_kcal) for item in new_items] == [
        ("half chicken rice", 260),
        ("soup", 100),
    ]
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert ledger.consumed_kcal == 360
    assert ledger.remaining_kcal == 1440


def test_explicit_item_removal_creates_new_version_without_deleting_thread_or_non_target_items() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-remove-target")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None
    old_items = _items_for_version(db, initial.meal_version_id)

    removal = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_removal_candidate(meal_thread_id=initial.meal_thread_id, meal_item_id=old_items[0].id),
        budget_kcal=1800,
    )

    assert removal is not None
    assert removal.superseded_version_id == initial.meal_version_id
    thread = db.get(MealThreadRecord, initial.meal_thread_id)
    assert thread is not None
    assert thread.active_version_id == removal.meal_version_id
    old_version = db.get(MealVersionRecord, initial.meal_version_id)
    assert old_version is not None
    assert old_version.version_status == "superseded"

    new_items = _items_for_version(db, removal.meal_version_id)
    assert [(item.name, item.estimated_kcal) for item in new_items] == [("soup", 150)]
    assert db.get(MealThreadRecord, initial.meal_thread_id) is not None
    ledger = db.execute(select(DayBudgetLedgerRecord)).scalar_one()
    assert ledger.consumed_kcal == 150
    assert ledger.remaining_kcal == 1650


def test_raw_text_remove_without_structured_operation_does_not_remove_item() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-remove-raw-text-not-owner")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None
    old_items = _items_for_version(db, initial.meal_version_id)
    raw_text_only = CommitRequestCandidate(
        request_id="correction-uow-raw-text-remove",
        manager_intent="food_estimation",
        meal_thread_id=initial.meal_thread_id,
        version_reason="correction",
        meal_title="lunch plate",
        raw_input="remove the chicken rice",
        estimated_kcal=150,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[],
        trace_ref={
            "correction_target_ref": {
                "meal_thread_id": initial.meal_thread_id,
                "meal_item_id": old_items[0].id,
                "canonical_name": "chicken rice",
            }
        },
    )

    with pytest.raises(ValueError, match="correction_replacement_item_missing"):
        commit_meal_payload_to_canonical(db, user=user, candidate=raw_text_only, budget_kcal=1800)

    db.expire_all()
    thread = db.get(MealThreadRecord, initial.meal_thread_id)
    assert thread is not None
    assert thread.active_version_id == initial.meal_version_id
    assert [(item.name, item.estimated_kcal) for item in _items_for_version(db, initial.meal_version_id)] == [
        ("chicken rice", 500),
        ("soup", 150),
    ]
    assert len(db.execute(select(MealVersionRecord)).scalars().all()) == 1


def test_explicit_item_removal_rejects_whole_meal_undo_when_no_non_target_items_remain() -> None:
    db = _session()
    user = get_or_create_user(db, "correction-uow-remove-last-item")
    initial = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="correction-uow-single-item",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="tea egg",
            raw_input="tea egg",
            estimated_kcal=80,
            resolution_status="completed_meal",
            local_date="2026-05-02",
            items=[MealItemPayload(name="tea egg", estimated_kcal=80)],
        ),
        budget_kcal=1800,
    )
    assert initial is not None
    only_item = _items_for_version(db, initial.meal_version_id)[0]

    with pytest.raises(ValueError, match="item_removal_cannot_empty_meal_thread"):
        commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_removal_candidate(
                meal_thread_id=initial.meal_thread_id,
                meal_item_id=only_item.id,
                canonical_name="tea egg",
            ),
            budget_kcal=1800,
        )

    db.expire_all()
    thread = db.get(MealThreadRecord, initial.meal_thread_id)
    assert thread is not None
    assert thread.active_version_id == initial.meal_version_id
    assert len(db.execute(select(MealVersionRecord)).scalars().all()) == 1
