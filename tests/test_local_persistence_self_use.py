from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_debug_read_model import build_accurate_intake_debug_read_model
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.current_budget_read_model import build_current_budget_view
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord
from app.models import Base
from app.schemas import CommitRequestCandidate, MealItemPayload


def _session_factory(db_path: Path) -> sessionmaker[Session]:
    engine = create_engine(f"sqlite:///{db_path.as_posix()}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(bind=engine, autocommit=False, autoflush=False)


def _initial_candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="self-use-persistence-initial",
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
        request_id="self-use-persistence-correction",
        manager_intent="food_estimation",
        meal_thread_id=meal_thread_id,
        version_reason="correction",
        meal_title="chicken rice and soup",
        raw_input="chicken rice was smaller",
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
        request_id="self-use-persistence-removal",
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


def test_local_sqlite_self_use_roundtrip_preserves_active_truth_after_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "accurate_intake_self_use.sqlite3"
    SessionLocal = _session_factory(db_path)

    with SessionLocal() as db:
        user = get_or_create_user(db, "self-use-roundtrip")
        initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
        assert initial is not None
        user_id = user.id
        meal_thread_id = initial.meal_thread_id

    with SessionLocal() as db:
        current_budget = build_current_budget_view(db, user_id=user_id, local_date="2026-05-02")
        debug_model = build_accurate_intake_debug_read_model(
            db,
            user_id=user_id,
            local_date="2026-05-02",
            current_budget=current_budget,
        )
        assert debug_model["today_summary"]["consumed_kcal"] == 650
        assert debug_model["meal_threads"][0]["meal_thread_id"] == meal_thread_id
        old_item = db.execute(
            select(MealItemRecord).where(MealItemRecord.name == "chicken rice")
        ).scalar_one()
        user = get_or_create_user(db, "self-use-roundtrip")
        correction = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_correction_candidate(meal_thread_id=meal_thread_id, meal_item_id=old_item.id),
            budget_kcal=1800,
        )
        assert correction is not None

    with SessionLocal() as db:
        current_budget = build_current_budget_view(db, user_id=user_id, local_date="2026-05-02")
        debug_model = build_accurate_intake_debug_read_model(
            db,
            user_id=user_id,
            local_date="2026-05-02",
            current_budget=current_budget,
        )

    assert debug_model["today_summary"]["consumed_kcal"] == 470
    assert debug_model["today_summary"]["remaining_kcal"] == 1330
    assert debug_model["meal_threads"][0]["active_version"]["total_kcal"] == 470
    assert debug_model["meal_threads"][0]["superseded_versions"][0]["total_kcal"] == 650
    assert debug_model["correction_history"][0]["non_target_item_names_preserved"] == ["soup"]
    assert debug_model["same_truth"]["status"] == "pass"


def test_local_sqlite_self_use_roundtrip_preserves_item_removal_after_reopen(tmp_path: Path) -> None:
    db_path = tmp_path / "accurate_intake_self_use_removal.sqlite3"
    SessionLocal = _session_factory(db_path)

    with SessionLocal() as db:
        user = get_or_create_user(db, "self-use-removal-roundtrip")
        initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
        assert initial is not None
        user_id = user.id
        meal_thread_id = initial.meal_thread_id
        target_item = db.execute(
            select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
        ).scalars().first()
        assert target_item is not None
        removal = commit_meal_payload_to_canonical(
            db,
            user=user,
            candidate=_removal_candidate(meal_thread_id=meal_thread_id, meal_item_id=target_item.id),
            budget_kcal=1800,
        )
        assert removal is not None

    with SessionLocal() as db:
        current_budget = build_current_budget_view(db, user_id=user_id, local_date="2026-05-02")
        debug_model = build_accurate_intake_debug_read_model(
            db,
            user_id=user_id,
            local_date="2026-05-02",
            current_budget=current_budget,
        )

    assert debug_model["today_summary"]["consumed_kcal"] == 150
    assert debug_model["today_summary"]["remaining_kcal"] == 1650
    assert debug_model["meal_threads"][0]["active_version"]["items"] == [
        {
            "meal_item_id": debug_model["meal_threads"][0]["active_version"]["items"][0]["meal_item_id"],
            "name": "soup",
            "estimated_kcal": 150,
        }
    ]
    assert debug_model["correction_history"][0]["removed_item_names"] == ["chicken rice"]
    assert debug_model["same_truth"]["status"] == "pass"
