from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.budget.infrastructure.models import LedgerEntryRecord
from app.composition.accurate_intake_debug_read_model import build_accurate_intake_debug_read_model
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_answer import build_remaining_budget_answer_contract_from_views
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _initial_candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="mvp-product-loop-initial",
        manager_intent="food_estimation",
        version_reason="new_intake",
        meal_title="chicken rice and soup",
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
        request_id="mvp-product-loop-correction",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="chicken rice and soup",
        raw_input="chicken rice smaller",
        estimated_kcal=470,
        protein_g=30,
        carb_g=55,
        fat_g=12,
        resolution_status="completed_meal",
        local_date="2026-05-02",
        items=[MealItemPayload(name="chicken rice", estimated_kcal=320, protein_g=27, carb_g=50, fat_g=9)],
        trace_ref={
            "correction_target_ref": {
                "meal_thread_id": meal_thread_id,
                "meal_item_id": meal_item_id,
                "canonical_name": "chicken rice",
            }
        },
    )


def _removal_candidate(*, meal_thread_id: int, meal_item_id: int) -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="mvp-product-loop-removal",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="chicken rice and soup",
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
                "canonical_name": "chicken rice",
            },
        },
    )


def _items_for_version(db: Session, version_id: int) -> list[MealItemRecord]:
    return db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()


def test_product_loop_roundtrip_debug_read_model_uses_active_versions_and_preserves_non_targets() -> None:
    db = _session()
    user = get_or_create_user(db, "mvp-product-loop-roundtrip")
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
    db.expire_all()

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-02")
    debug_model = build_accurate_intake_debug_read_model(
        db,
        user_id=user.id,
        local_date="2026-05-02",
        current_budget=current_budget,
    )

    assert debug_model["today_summary"] == {
        "source_kind": "current_budget_read_model",
        "read_only": True,
        "user_id": user.id,
        "local_date": "2026-05-02",
        "budget_kcal": 1800,
        "consumed_kcal": 470,
        "remaining_kcal": 1330,
        "active_meal_count": 1,
    }
    assert debug_model["meal_threads"] == [
        {
            "meal_thread_id": initial.meal_thread_id,
            "active_version_id": correction.meal_version_id,
            "title": "chicken rice and soup",
            "active_version": {
                "meal_version_id": correction.meal_version_id,
                "parent_version_id": initial.meal_version_id,
                "version_reason": "correction",
                "total_kcal": 470,
                "items": [
                    {"meal_item_id": debug_model["meal_threads"][0]["active_version"]["items"][0]["meal_item_id"], "name": "chicken rice", "estimated_kcal": 320},
                    {"meal_item_id": debug_model["meal_threads"][0]["active_version"]["items"][1]["meal_item_id"], "name": "soup", "estimated_kcal": 150},
                ],
            },
            "superseded_versions": [
                {
                    "meal_version_id": initial.meal_version_id,
                    "total_kcal": 650,
                    "version_reason": "new_intake",
                }
            ],
        }
    ]
    assert debug_model["correction_history"] == [
        {
            "meal_thread_id": initial.meal_thread_id,
            "old_version_id": initial.meal_version_id,
            "new_version_id": correction.meal_version_id,
            "new_total_kcal": 470,
            "old_total_kcal": 650,
            "non_target_item_names_preserved": ["soup"],
            "removed_item_names": [],
        }
    ]
    assert debug_model["ledger_audit_events"] == [
        {"entry_type": "meal_consumption", "source_id": initial.meal_version_id, "delta_kcal": 650, "role": "audit_event", "current_truth_owner": False},
        {"entry_type": "meal_consumption", "source_id": correction.meal_version_id, "delta_kcal": 470, "role": "audit_event", "current_truth_owner": False},
    ]
    assert debug_model["same_truth"] == {
        "status": "pass",
        "source_truth": "active_meal_versions",
        "debug_model_consumed_kcal": 470,
        "current_budget_consumed_kcal": 470,
    }


def test_debug_read_model_and_chat_budget_answer_copy_same_current_budget_view_without_recompute() -> None:
    db = _session()
    user = get_or_create_user(db, "mvp-read-model-no-recompute")
    commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-02")
    inconsistent_view = CurrentBudgetView(
        **{
            **current_budget.model_dump(),
            "remaining_kcal": 1200,
        }
    )
    active_plan = ActiveBodyPlanView(body_plan_id=1, daily_budget_kcal=1800)

    answer = build_remaining_budget_answer_contract_from_views(
        current_budget=inconsistent_view,
        active_plan=active_plan,
    )
    debug_model = build_accurate_intake_debug_read_model(
        db,
        user_id=user.id,
        local_date="2026-05-02",
        current_budget=inconsistent_view,
    )

    assert answer.consumed_kcal == debug_model["today_summary"]["consumed_kcal"]
    assert answer.remaining_kcal == 1200
    assert debug_model["today_summary"]["remaining_kcal"] == 1200
    assert debug_model["same_truth"]["status"] == "pass"


def test_debug_read_model_keeps_ledger_audit_separate_from_current_truth_when_audit_is_stale() -> None:
    db = _session()
    user = get_or_create_user(db, "mvp-audit-not-truth")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None
    stale_audit = db.execute(select(LedgerEntryRecord).where(LedgerEntryRecord.source_id == initial.meal_version_id)).scalar_one()
    stale_audit.delta_kcal = 999
    db.commit()

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-02")
    debug_model = build_accurate_intake_debug_read_model(
        db,
        user_id=user.id,
        local_date="2026-05-02",
        current_budget=current_budget,
    )

    assert debug_model["today_summary"]["consumed_kcal"] == 650
    assert debug_model["ledger_audit_events"][0]["delta_kcal"] == 999
    assert debug_model["ledger_audit_events"][0]["current_truth_owner"] is False
    assert debug_model["same_truth"]["source_truth"] == "active_meal_versions"


def test_product_loop_read_model_tracks_explicit_item_removal_as_new_active_version() -> None:
    db = _session()
    user = get_or_create_user(db, "mvp-product-loop-removal")
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

    current_budget = build_current_budget_view(db, user_id=user.id, local_date="2026-05-02")
    debug_model = build_accurate_intake_debug_read_model(
        db,
        user_id=user.id,
        local_date="2026-05-02",
        current_budget=current_budget,
    )

    active_version = debug_model["meal_threads"][0]["active_version"]
    assert debug_model["today_summary"]["consumed_kcal"] == 150
    assert debug_model["today_summary"]["remaining_kcal"] == 1650
    assert active_version["total_kcal"] == 150
    assert [item["name"] for item in active_version["items"]] == ["soup"]
    assert debug_model["correction_history"][0]["removed_item_names"] == ["chicken rice"]
    assert debug_model["correction_history"][0]["non_target_item_names_preserved"] == ["soup"]
    assert debug_model["same_truth"]["status"] == "pass"
