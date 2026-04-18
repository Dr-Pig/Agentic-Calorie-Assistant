from __future__ import annotations

from datetime import datetime

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.calibration_commit_bridge import apply_calibration_proposal_commit
from app.application.calibration_model import CalibrationModelInputs, build_calibration_model
from app.application.calibration_proposal_gate import CalibrationProposalGateInputs, build_calibration_proposal_gate
from app.application.calibration_proposal_response import build_calibration_proposal_response
from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.domain import ActiveBodyPlanView, CurrentBudgetView
from app.models import Base, BodyPlanRecord
from app.web import calibration_routes


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _candidate_model():
    return build_calibration_model(
        CalibrationModelInputs(
            body_plan_estimated_tdee_kcal=2100,
            observation_window_days=14,
            body_observation_count=6,
            intake_coverage=0.80,
            operating_expenditure_shift_kcal=240,
            trend_mismatch_consistency=0.75,
            trend_volatility=0.2,
            logging_gap_ratio=0.18,
            late_logged_meal_ratio=0.22,
        )
    )


def _logging_quality_model():
    return build_calibration_model(
        CalibrationModelInputs(
            body_plan_estimated_tdee_kcal=2100,
            observation_window_days=14,
            body_observation_count=5,
            intake_coverage=0.79,
            operating_expenditure_shift_kcal=260,
            trend_mismatch_consistency=0.8,
            trend_volatility=0.2,
            logging_gap_ratio=0.2,
            late_logged_meal_ratio=0.3,
        )
    )


def test_calibration_response_surfaces_single_primary_proposal() -> None:
    calibration_result = _candidate_model()
    gate_result = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=calibration_result,
            current_budget_status="tight",
            active_body_plan_status="active",
        )
    )

    response = build_calibration_proposal_response(
        calibration_result=calibration_result,
        gate_result=gate_result,
        current_budget_view=CurrentBudgetView(user_id=1, local_date="2026-04-18", budget_kcal=1600, remaining_kcal=480),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=1,
            body_plan_id=1,
            daily_budget_kcal=1600,
            estimated_tdee=2100,
            safety_floor_kcal=1200,
            target_pace_kg_per_week=0.5,
        ),
    )

    assert response.surfaced is True
    assert response.top_option is not None
    assert response.top_option.option_type == "budget_adjustment"
    assert response.proposal_family == "budget_adjustment"
    assert any(action["action"] == "accept_calibration_proposal" for action in response.quick_actions)


def test_calibration_accept_writes_new_body_plan_and_refreshes_budget() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-accept")
    bootstrap = bootstrap_body_plan_for_date(
        db,
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
    previous_active_plan = db.query(BodyPlanRecord).filter(BodyPlanRecord.user_id == user.id, BodyPlanRecord.plan_status == "active").one()

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-04-18",
        proposal_family="budget_adjustment",
        effect_payload={
            "new_daily_budget_kcal": bootstrap.active_body_plan_view.daily_budget_kcal - 150,
            "new_estimated_tdee_kcal": bootstrap.active_body_plan_view.estimated_tdee,
            "rationale_summary": "calibration adjustment",
        },
        decision="accepted",
        accepted_at=datetime(2026, 4, 18, 10, 30),
    )

    assert result.body_plan_id is not None
    db.expire_all()
    previous = db.get(BodyPlanRecord, previous_active_plan.id)
    current = db.get(BodyPlanRecord, result.body_plan_id)
    assert previous is not None and previous.plan_status == "superseded"
    assert current is not None and current.plan_status == "active"
    assert current.daily_budget_kcal == bootstrap.active_body_plan_view.daily_budget_kcal - 150
    assert result.current_budget_view.budget_kcal == current.daily_budget_kcal


def test_calibration_accept_respects_11am_effective_from_rule() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-11am")
    bootstrap_body_plan_for_date(
        db,
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

    result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-04-18",
        proposal_family="budget_adjustment",
        effect_payload={
            "new_daily_budget_kcal": 1450,
            "new_estimated_tdee_kcal": 2000,
            "rationale_summary": "calibration adjustment",
        },
        decision="accepted",
        accepted_at=datetime(2026, 4, 18, 11, 30),
    )

    assert result.effective_from == "2026-04-19"


def test_logging_quality_first_surfaces_without_plan_change() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-logging-first")
    bootstrap_body_plan_for_date(
        db,
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
    before_plan_count = db.query(BodyPlanRecord).count()

    calibration_result = _logging_quality_model()
    gate_result = build_calibration_proposal_gate(
        CalibrationProposalGateInputs(
            calibration_result=calibration_result,
            current_budget_status="on_track",
            active_body_plan_status="active",
        )
    )
    response = build_calibration_proposal_response(
        calibration_result=calibration_result,
        gate_result=gate_result,
        current_budget_view=CurrentBudgetView(user_id=user.id, local_date="2026-04-18", budget_kcal=1600),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=user.id,
            body_plan_id=1,
            daily_budget_kcal=1600,
            estimated_tdee=2100,
            safety_floor_kcal=1200,
            target_pace_kg_per_week=0.5,
        ),
    )

    assert response.surfaced is True
    assert response.top_option is not None
    assert response.top_option.option_type == "logging_quality_first"

    commit_result = apply_calibration_proposal_commit(
        db,
        user=user,
        local_date="2026-04-18",
        proposal_family="logging_quality_first",
        effect_payload=dict(response.top_option.effect_payload),
        decision="accepted",
        accepted_at=datetime(2026, 4, 18, 13, 0),
    )

    assert commit_result.effective_from == "2026-04-18"
    assert db.query(BodyPlanRecord).count() == before_plan_count


def test_calibration_preview_route_returns_chat_primary_surface() -> None:
    db = _session()
    user = get_or_create_user(db, "calibration-preview")
    bootstrap_body_plan_for_date(
        db,
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
    mini_app = FastAPI()
    mini_app.include_router(calibration_routes.router)

    def override_get_db():
        try:
            yield db
        finally:
            pass

    mini_app.dependency_overrides[calibration_routes.get_db] = override_get_db
    with TestClient(mini_app) as client:
        response = client.post(
            "/calibration/proposal/preview",
            json={
                "user_id": "calibration-preview",
                "local_date": "2026-04-18",
                "current_budget_status": "tight",
                "model_inputs": {
                    "body_plan_estimated_tdee_kcal": 2100,
                    "observation_window_days": 14,
                    "body_observation_count": 6,
                    "intake_coverage": 0.80,
                    "operating_expenditure_shift_kcal": 240,
                    "trend_mismatch_consistency": 0.75,
                    "trend_volatility": 0.2,
                    "logging_gap_ratio": 0.18,
                    "late_logged_meal_ratio": 0.22,
                    "rough_meal_ratio": 0.0,
                    "rescue_overlay_influence": 0.0,
                },
            },
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["response"]["surfaced"] is True
    assert payload["response"]["proposal_family"] == "budget_adjustment"
