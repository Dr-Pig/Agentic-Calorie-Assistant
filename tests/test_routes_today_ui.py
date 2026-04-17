from __future__ import annotations

from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.database import get_or_create_user, save_meal_log
from app.main import app
from app.models import Base
from app.routes import get_db as routes_get_db
from app.schemas import CommitRequestCandidate
from app.application.canonical_commit_bridge import commit_request_candidate_to_canonical
from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.infrastructure.meal_log_persistence import persist_text_meal_result
from app.infrastructure.canonical_persistence import commit_meal_payload_to_canonical
from app.models import MealLog
from app.schemas import ComponentEstimate, EstimatePayload


@pytest.fixture()
def db_session():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    db = testing_session()

    def override_get_db():
        try:
            yield db
        finally:
            pass

    app.dependency_overrides[routes_get_db] = override_get_db
    try:
        yield db
    finally:
        app.dependency_overrides.pop(routes_get_db, None)
        db.close()


@pytest.fixture()
def client(db_session):
    with TestClient(app) as test_client:
        yield test_client


def test_today_current_budget_ignores_legacy_meal_logs(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-legacy")
    save_meal_log(
        db_session,
        user,
        meal_title="legacy raw bowl",
        raw_input="legacy raw bowl",
        kcal=999,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        components=[{"name": "legacy raw bowl"}],
        debug_steps=[],
        status="completed_meal",
    )

    response = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-legacy", "local_date": "2026-04-11"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["user_id"] == user.id
    assert payload["local_date"] == "2026-04-11"
    assert payload["budget_kcal"] == 0
    assert payload["consumed_kcal"] == 0
    assert payload["remaining_kcal"] == 0
    assert payload["active_meal_count"] == 0
    assert payload["meals"] == []


def test_today_surface_renders_canonical_current_budget(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-canonical")
    commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-req-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="egg sandwich",
            raw_input="egg sandwich",
            estimated_kcal=350,
            protein_g=12,
            carb_g=28,
            fat_g=14,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 8, 30),
            local_date="2026-04-11",
        ),
        budget_kcal=1200,
    )

    response = client.get("/today", params={"user_id": "today-ui-canonical", "local_date": "2026-04-11"})

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "Today Surface" in response.text
    assert "source: current_budget_read_model" in response.text
    assert "egg sandwich" in response.text
    assert "350 kcal" in response.text
    assert "1200" in response.text
    assert "current-budget read model" in response.text


def test_today_surface_syncs_bootstrap_target_after_two_meals(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-sync")
    bootstrap = bootstrap_body_plan_for_date(
        db_session,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
        ),
    )

    commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-sync-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="breakfast sandwich",
            raw_input="breakfast sandwich",
            estimated_kcal=420,
            protein_g=18,
            carb_g=32,
            fat_g=14,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 18, 8, 0),
            local_date="2026-04-18",
        ),
    )
    commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-sync-2",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="chicken rice",
            raw_input="chicken rice",
            estimated_kcal=610,
            protein_g=32,
            carb_g=65,
            fat_g=18,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 18, 12, 30),
            local_date="2026-04-18",
        ),
    )

    response = client.get("/today/current-budget", params={"user_id": "today-ui-sync", "local_date": "2026-04-18"})

    assert response.status_code == 200
    payload = response.json()
    assert payload["budget_kcal"] == bootstrap.target_result.recommended_target_kcal
    assert payload["consumed_kcal"] == 1030
    assert payload["remaining_kcal"] == bootstrap.target_result.recommended_target_kcal - 1030
    assert payload["active_meal_count"] == 2


def test_today_surface_stays_on_active_version_after_correction(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-correction")
    first = commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-req-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="noodle bowl",
            raw_input="noodle bowl",
            estimated_kcal=610,
            protein_g=22,
            carb_g=68,
            fat_g=20,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 12, 0),
            local_date="2026-04-11",
        ),
        budget_kcal=1200,
    )
    assert first is not None

    commit_request_candidate_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-req-2",
            planner_intent="modification",
            meal_thread_id=first.meal_thread_id,
            parent_version_id=first.meal_version_id,
            version_reason="historical_correction",
            meal_title="grilled tofu plate",
            raw_input="grilled tofu plate",
            estimated_kcal=540,
            protein_g=20,
            carb_g=60,
            fat_g=18,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 12, 10),
            local_date="2026-04-11",
        ),
    )

    response_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-correction", "local_date": "2026-04-11"},
    )
    response_html = client.get(
        "/today",
        params={"user_id": "today-ui-correction", "local_date": "2026-04-11"},
    )

    assert response_json.status_code == 200
    payload = response_json.json()
    assert payload["consumed_kcal"] == 540
    assert payload["active_meal_count"] == 1
    assert [meal["meal_title"] for meal in payload["meals"]] == ["grilled tofu plate"]
    assert payload["meals"][0]["meal_version_id"] is not None

    assert response_html.status_code == 200
    assert "grilled tofu plate" in response_html.text
    assert "540 kcal" in response_html.text
    assert "noodle bowl" not in response_html.text


def test_today_surface_keeps_canonical_local_day_after_cross_midnight_correction(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-midnight")
    first = commit_meal_payload_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-midnight-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="late dinner",
            raw_input="late dinner",
            estimated_kcal=510,
            protein_g=18,
            carb_g=60,
            fat_g=16,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 11, 23, 55),
            local_date="2026-04-11",
        ),
        budget_kcal=1200,
    )
    assert first is not None

    commit_request_candidate_to_canonical(
        db_session,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="today-ui-midnight-2",
            planner_intent="modification",
            meal_thread_id=first.meal_thread_id,
            parent_version_id=first.meal_version_id,
            version_reason="historical_correction",
            meal_title="late dinner corrected",
            raw_input="late dinner corrected",
            estimated_kcal=470,
            protein_g=17,
            carb_g=54,
            fat_g=15,
            resolution_status="completed_meal",
            occurred_at=datetime(2026, 4, 12, 0, 5),
            local_date="2026-04-11",
        ),
    )

    same_day_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-midnight", "local_date": "2026-04-11"},
    )
    next_day_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-midnight", "local_date": "2026-04-12"},
    )
    same_day_html = client.get("/today", params={"user_id": "today-ui-midnight", "local_date": "2026-04-11"})

    assert same_day_json.status_code == 200
    same_day_payload = same_day_json.json()
    assert same_day_payload["local_date"] == "2026-04-11"
    assert same_day_payload["consumed_kcal"] == 470
    assert same_day_payload["active_meal_count"] == 1
    assert [meal["meal_title"] for meal in same_day_payload["meals"]] == ["late dinner corrected"]

    assert next_day_json.status_code == 200
    next_day_payload = next_day_json.json()
    assert next_day_payload["local_date"] == "2026-04-12"
    assert next_day_payload["consumed_kcal"] == 0
    assert next_day_payload["active_meal_count"] == 0
    assert next_day_payload["meals"] == []

    assert same_day_html.status_code == 200
    assert "late dinner corrected" in same_day_html.text
    assert "470 kcal" in same_day_html.text
    assert "2026-04-11" in same_day_html.text
    assert "source: current_budget_read_model" in same_day_html.text


def _followup_payload(
    *,
    request_id: str,
    title: str,
    kcal: int,
    action_taken: str,
    route_target: str = "best_effort_answer",
    followup_question: str | None = None,
    quality_signals: dict[str, object] | None = None,
    trace_contract: dict[str, object] | None = None,
) -> EstimatePayload:
    return EstimatePayload(
        request_id=request_id,
        meal_title=title,
        estimated_kcal=kcal,
        protein_g=10,
        carb_g=20,
        fat_g=5,
        route_target=route_target,
        action_taken=action_taken,
        reply_text=f"{title} ok",
        quality_signals={"estimate_mode": "llm_only", **dict(quality_signals or {})},
        trace_contract={"local_date": "2026-04-11", **dict(trace_contract or {})},
        boundary_trace={},
        followup_question=followup_question,
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


def test_today_surface_shows_turn2_completion_but_not_turn1_unresolved_draft(client, db_session) -> None:
    user = get_or_create_user(db_session, "today-ui-followup")

    first = persist_text_meal_result(
        db_session,
        user=user,
        latest_log=None,
        planner_intent="food_estimation",
        payload=_followup_payload(
            request_id="today-ui-followup-1",
            title="milk tea",
            kcal=394,
            action_taken="answer_with_uncertainty",
            followup_question="大杯還是中杯？",
            trace_contract={
                "response_mode_hint": "estimate_with_followup",
                "unresolved_info": ["cup_size"],
                "followup_question": "大杯還是中杯？",
            },
        ),
        raw_input="我剛剛喝珍珠奶茶",
        request_id="today-ui-followup-1",
    )

    assert first["status"] == "draft_unresolved"
    draft_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-followup", "local_date": "2026-04-11"},
    )
    draft_html = client.get(
        "/today",
        params={"user_id": "today-ui-followup", "local_date": "2026-04-11"},
    )
    assert draft_json.status_code == 200
    assert draft_json.json()["active_meal_count"] == 0
    assert "milk tea" not in draft_html.text

    latest_log = db_session.get(MealLog, first["persisted_log_id"])
    assert latest_log is not None

    second = persist_text_meal_result(
        db_session,
        user=user,
        latest_log=latest_log,
        planner_intent="clarification",
        payload=_followup_payload(
            request_id="today-ui-followup-2",
            title="milk tea large half sugar",
            kcal=450,
            action_taken="direct_answer",
            quality_signals={"estimate_mode": "anchored_component"},
        ),
        raw_input="大杯、半糖、正常冰",
        request_id="today-ui-followup-2",
    )

    assert second["status"] == "completed_meal"
    resolved_json = client.get(
        "/today/current-budget",
        params={"user_id": "today-ui-followup", "local_date": "2026-04-11"},
    )
    resolved_html = client.get(
        "/today",
        params={"user_id": "today-ui-followup", "local_date": "2026-04-11"},
    )

    assert resolved_json.status_code == 200
    payload = resolved_json.json()
    assert payload["consumed_kcal"] == 450
    assert payload["active_meal_count"] == 1
    assert [meal["meal_title"] for meal in payload["meals"]] == ["milk tea large half sugar"]

    assert resolved_html.status_code == 200
    assert "milk tea large half sugar" in resolved_html.text
    assert "450 kcal" in resolved_html.text
    assert "大杯還是中杯？" not in resolved_html.text
