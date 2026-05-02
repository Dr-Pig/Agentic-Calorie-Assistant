from __future__ import annotations

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.composition.accurate_intake_debug_routes import build_accurate_intake_debug_payload
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.database import get_or_create_user
from app.intake.infrastructure.models import MealItemRecord, MealThreadRecord, MealVersionRecord
from app.intake.interface.accurate_intake_debug_surface import render_accurate_intake_debug_surface
from app.models import Base
from app.routes import router
from app.schemas import CommitRequestCandidate, MealItemPayload
from app.shared.infra.models import User


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _initial_candidate() -> CommitRequestCandidate:
    return CommitRequestCandidate(
        request_id="debug-surface-initial",
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
        request_id="debug-surface-correction",
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


def test_debug_payload_for_missing_user_is_read_only_and_does_not_create_user() -> None:
    db = _session()

    payload = build_accurate_intake_debug_payload(
        db,
        user_external_id="missing-user",
        local_date="2026-05-02",
    )

    assert payload["read_only"] is True
    assert payload["state_posture"] == "no_user"
    assert payload["model"]["meal_threads"] == []
    assert payload["model"]["pending_drafts"] == []
    assert db.execute(select(User)).scalars().all() == []


def test_debug_payload_exposes_canonical_product_loop_state_without_recomputing_truth() -> None:
    db = _session()
    user = get_or_create_user(db, "debug-surface-user")
    initial = commit_meal_payload_to_canonical(db, user=user, candidate=_initial_candidate(), budget_kcal=1800)
    assert initial is not None
    target_item = db.execute(
        select(MealItemRecord).where(MealItemRecord.meal_version_id == initial.meal_version_id)
    ).scalars().first()
    assert target_item is not None
    correction = commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=_correction_candidate(meal_thread_id=initial.meal_thread_id, meal_item_id=target_item.id),
        budget_kcal=1800,
    )
    assert correction is not None

    payload = build_accurate_intake_debug_payload(
        db,
        user_external_id="debug-surface-user",
        local_date="2026-05-02",
    )

    assert payload["surface_id"] == "accurate_intake_debug_surface_v1"
    assert payload["read_only"] is True
    assert payload["state_posture"] == "canonical_user_state"
    assert set(payload["not_claiming"]) >= {"product_ready", "live_llm_ready", "production_db_ready"}
    model = payload["model"]
    assert model["today_summary"]["consumed_kcal"] == 470
    assert model["today_summary"]["remaining_kcal"] == 1330
    assert model["meal_threads"][0]["active_version"]["total_kcal"] == 470
    assert model["correction_history"][0]["non_target_item_names_preserved"] == ["soup"]
    assert model["same_truth"]["status"] == "pass"
    assert model["ledger_audit_events"]
    assert all(event["role"] == "audit_event" for event in model["ledger_audit_events"])


def test_debug_read_model_surfaces_pending_drafts_as_read_only() -> None:
    db = _session()
    user = get_or_create_user(db, "debug-surface-drafts")
    thread = MealThreadRecord(user_id=user.id, title="pending drink")
    db.add(thread)
    db.flush()
    draft = MealVersionRecord(
        meal_thread_id=thread.id,
        version_reason="new_intake",
        meal_title="pending drink",
        raw_input="bubble tea",
        manager_intent="food_estimation",
        resolution_status="draft_unresolved",
        total_kcal=0,
        local_date="2026-05-02",
    )
    db.add(draft)
    db.flush()
    thread.active_version_id = draft.id
    db.commit()

    payload = build_accurate_intake_debug_payload(
        db,
        user_external_id="debug-surface-drafts",
        local_date="2026-05-02",
    )

    assert payload["model"]["pending_drafts"] == [
        {
            "meal_thread_id": thread.id,
            "meal_version_id": draft.id,
            "title": "pending drink",
            "resolution_status": "draft_unresolved",
            "total_kcal": 0,
            "read_only": True,
        }
    ]


def test_debug_surface_route_is_registered_and_renderer_is_read_only() -> None:
    route_paths = {route.path for route in router.routes}
    assert "/accurate-intake/debug" in route_paths
    assert "/accurate-intake/debug/surface" in route_paths

    html = render_accurate_intake_debug_surface(
        {
            "user_external_id": "debug-surface-user",
            "local_date": "2026-05-02",
            "state_posture": "canonical_user_state",
            "model": {
                "today_summary": {"consumed_kcal": 470, "remaining_kcal": 1330},
                "meal_threads": [{"meal_thread_id": 1, "title": "chicken rice"}],
                "pending_drafts": [],
                "correction_history": [{"new_total_kcal": 470}],
                "same_truth": {"status": "pass"},
            },
        }
    )

    assert "Accurate Intake Debug Surface" in html
    assert "Read-only local MVP surface" in html
    assert "Ledger Audit Events" in html
    assert "Same Truth Trace" in html
    assert "chicken rice" in html
