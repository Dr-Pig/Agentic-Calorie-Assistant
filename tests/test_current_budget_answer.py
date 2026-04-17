from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.current_budget_answer import build_remaining_budget_answer_contract
from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.infrastructure.canonical_persistence import commit_meal_payload_to_canonical
from app.models import Base
from app.schemas import CommitRequestCandidate


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def test_remaining_budget_answer_requires_onboarding_when_no_active_plan() -> None:
    db = _session()
    user = get_or_create_user(db, "remaining-no-plan")

    answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date="2026-04-18")

    assert answer.status == "onboarding_required"
    assert answer.daily_target_kcal == 0


def test_remaining_budget_answer_reads_bootstrap_target_and_two_meals() -> None:
    db = _session()
    user = get_or_create_user(db, "remaining-ready")
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

    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="meal-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="breakfast sandwich",
            raw_input="breakfast sandwich",
            estimated_kcal=420,
            protein_g=18,
            carb_g=32,
            fat_g=14,
            resolution_status="completed_meal",
            local_date="2026-04-18",
        ),
    )
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="meal-2",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="chicken rice",
            raw_input="chicken rice",
            estimated_kcal=610,
            protein_g=32,
            carb_g=65,
            fat_g=18,
            resolution_status="completed_meal",
            local_date="2026-04-18",
        ),
    )

    answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date="2026-04-18")

    assert answer.status == "ready"
    assert answer.daily_target_kcal == bootstrap.target_result.recommended_target_kcal
    assert answer.consumed_kcal == 1030
    assert answer.remaining_kcal == bootstrap.target_result.recommended_target_kcal - 1030
    assert answer.meal_count == 2
