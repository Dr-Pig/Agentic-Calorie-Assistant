from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.canonical_commit_bridge import (
    build_commit_request_candidate,
    commit_request_candidate_to_canonical,
)
from app.application.current_budget_read_model import build_current_budget_view
from app.infrastructure.meal_log_persistence import persist_text_meal_result
from app.domain import CurrentBudgetMealSummary, CurrentBudgetView
from app.models import Base, MealLog, User
from app.schemas import ComponentEstimate, EstimatePayload


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _user(db: Session) -> User:
    user = User(user_id="read-model-user")
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _payload(*, request_id: str, title: str, kcal: int, local_date: str = "2026-04-11") -> EstimatePayload:
    return EstimatePayload(
        request_id=request_id,
        meal_title=title,
        estimated_kcal=kcal,
        protein_g=10,
        carb_g=20,
        fat_g=5,
        route_target="best_effort_answer",
        action_taken="direct_answer",
        reply_text=f"{title} ok",
        quality_signals={"estimate_mode": "exact_item"},
        trace_contract={"local_date": local_date},
        boundary_trace={},
        component_estimates=[
            ComponentEstimate(
                name=title,
                quantity_hint="1 serving",
                estimated_kcal=kcal,
                protein_g=10,
                carb_g=20,
                fat_g=5,
            )
        ],
    )


def test_current_budget_view_reads_canonical_ledger_and_active_meals() -> None:
    db = _session()
    user = _user(db)

    persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="egg sandwich", kcal=350),
        raw_input="egg sandwich",
        request_id="req-1",
    )
    persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-2", title="chicken salad", kcal=420),
        raw_input="chicken salad",
        request_id="req-2",
    )

    view = build_current_budget_view(db, user_id=user.id, local_date="2026-04-11")

    assert view.user_id == user.id
    assert view.local_date == "2026-04-11"
    assert view.consumed_kcal == 770
    assert view.adjustment_kcal == 0
    assert view.remaining_kcal == -770
    assert view.active_meal_count == 2
    assert [meal.meal_title for meal in view.meals] == ["egg sandwich", "chicken salad"]


def test_current_budget_view_only_surfaces_active_versions_after_correction() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="beef bowl", kcal=600),
        raw_input="beef bowl",
        request_id="req-1",
    )
    latest_log = db.get(MealLog, first["persisted_log_id"])

    persist_text_meal_result(
        db,
        user=user,
        latest_log=latest_log,
        planner_intent="modification",
        payload=_payload(request_id="req-2", title="beef bowl no sauce", kcal=480),
        raw_input="beef bowl no sauce",
        request_id="req-2",
    )

    view = build_current_budget_view(db, user_id=user.id, local_date="2026-04-11")

    assert view.consumed_kcal == 480
    assert view.active_meal_count == 1
    assert [meal.meal_title for meal in view.meals] == ["beef bowl no sauce"]


def test_current_budget_view_exposes_today_surface_query_shape() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="rice bowl", kcal=520),
        raw_input="rice bowl",
        request_id="req-1",
    )
    latest_log = db.get(MealLog, first["persisted_log_id"])

    persist_text_meal_result(
        db,
        user=user,
        latest_log=latest_log,
        planner_intent="modification",
        payload=_payload(request_id="req-2", title="rice bowl no sauce", kcal=430),
        raw_input="rice bowl no sauce",
        request_id="req-2",
    )

    view = build_current_budget_view(db, user_id=user.id, local_date="2026-04-11")

    assert isinstance(view, CurrentBudgetView)
    assert view.user_id == user.id
    assert view.local_date == "2026-04-11"
    assert view.budget_kcal == 0
    assert view.consumed_kcal == 430
    assert view.adjustment_kcal == 0
    assert view.remaining_kcal == -430
    assert view.active_meal_count == 1
    assert view.last_recomputed_at is not None
    assert len(view.meals) == 1

    meal = view.meals[0]
    assert isinstance(meal, CurrentBudgetMealSummary)
    assert meal.meal_thread_id is not None
    assert meal.meal_version_id is not None
    assert meal.meal_title == "rice bowl no sauce"
    assert meal.total_kcal == 430
    assert meal.occurred_at is not None
    assert meal.resolution_status == "completed_meal"
    assert meal.planner_intent == "modification"


def test_current_budget_view_stays_on_active_version_after_historical_correction() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="pasta bowl", kcal=610),
        raw_input="pasta bowl",
        request_id="req-1",
    )
    first_thread_id = first["canonical_commit"]["meal_thread_id"]
    first_version_id = first["canonical_commit"]["meal_version_id"]
    first_log = db.get(MealLog, first["persisted_log_id"])
    assert first_log is not None

    second = persist_text_meal_result(
        db,
        user=user,
        latest_log=first_log,
        planner_intent="modification",
        payload=_payload(request_id="req-2", title="pasta bowl with cheese", kcal=690),
        raw_input="pasta bowl with cheese",
        request_id="req-2",
    )
    second_version_id = second["canonical_commit"]["meal_version_id"]

    correction_payload = _payload(request_id="req-3", title="pasta bowl corrected", kcal=560)
    candidate = build_commit_request_candidate(
        payload=correction_payload,
        raw_input="pasta bowl corrected",
        planner_intent="correction",
        request_id="req-3",
        meal_thread_id=first_thread_id,
        parent_version_id=first_version_id,
        version_reason="historical_correction",
    )

    commit = commit_request_candidate_to_canonical(
        db,
        user=user,
        candidate=candidate,
    )

    assert commit is not None
    assert commit.meal_thread_id == first_thread_id
    assert commit.superseded_version_id == second_version_id

    view = build_current_budget_view(db, user_id=user.id, local_date="2026-04-11")

    assert view.consumed_kcal == 560
    assert view.active_meal_count == 1
    assert [meal.meal_title for meal in view.meals] == ["pasta bowl corrected"]
    assert [meal.meal_version_id for meal in view.meals] == [commit.meal_version_id]


def test_current_budget_view_keeps_correction_on_the_canonical_local_day_only() -> None:
    db = _session()
    user = _user(db)

    first = persist_text_meal_result(
        db,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_payload(request_id="req-1", title="late dinner", kcal=510, local_date="2026-04-11"),
        raw_input="late dinner",
        request_id="req-1",
    )
    latest_log = db.get(MealLog, first["persisted_log_id"])
    assert latest_log is not None

    persist_text_meal_result(
        db,
        user=user,
        latest_log=latest_log,
        planner_intent="modification",
        payload=_payload(
            request_id="req-2",
            title="late dinner corrected",
            kcal=470,
            local_date="2026-04-11",
        ),
        raw_input="late dinner corrected",
        request_id="req-2",
    )

    same_day_view = build_current_budget_view(db, user_id=user.id, local_date="2026-04-11")
    next_day_view = build_current_budget_view(db, user_id=user.id, local_date="2026-04-12")

    assert same_day_view.consumed_kcal == 470
    assert same_day_view.active_meal_count == 1
    assert [meal.meal_title for meal in same_day_view.meals] == ["late dinner corrected"]

    assert next_day_view.consumed_kcal == 0
    assert next_day_view.active_meal_count == 0
    assert next_day_view.meals == []
