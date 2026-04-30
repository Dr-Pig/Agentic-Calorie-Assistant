from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.composition.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.database import get_or_create_user
from app.composition.general_chat_service import build_general_chat_response_pass
from app.models import Base, BodyPlanRecord, DayBudgetLedgerRecord, MealThreadRecord
from app.schemas import CommitRequestCandidate
from app.composition.canonical_persistence import commit_meal_payload_to_canonical


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _bootstrap_user(db: Session, external_id: str):
    user = get_or_create_user(db, external_id)
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
    return user, bootstrap


def test_general_chat_budget_mode_reads_shared_budget_views() -> None:
    db = _session()
    user, bootstrap = _bootstrap_user(db, "general-chat-budget")
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="general-chat-meal-1",
            manager_intent="food_estimation",
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
            request_id="general-chat-meal-2",
            manager_intent="food_estimation",
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

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-budget",
        raw_user_input="log chicken rice",
        mode="budget_summary",
        local_date="2026-04-18",
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.workflow_effect == "answer_budget_summary_without_state_mutation"
    assert result.required_read_surfaces == ["CurrentBudgetView", "ActiveBodyPlanView"]
    assert str(bootstrap.target_result.recommended_target_kcal) in result.reply_text
    assert "1030" in result.reply_text
    assert str(bootstrap.target_result.recommended_target_kcal - 1030) in result.reply_text


def test_general_chat_goal_mode_reads_active_body_plan_view() -> None:
    db = _session()
    _bootstrap_user(db, "general-chat-goal")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-goal",
        raw_user_input="how many calories are left?",
        mode="goal_summary",
        local_date="2026-04-18",
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "answer_only"
    assert result.workflow_effect == "answer_goal_summary_without_state_mutation"
    assert result.required_read_surfaces == ["ActiveBodyPlanView"]
    assert "lose_weight" in result.reply_text


def test_general_chat_mode_not_raw_text_selects_read_surface() -> None:
    db = _session()
    _bootstrap_user(db, "general-chat-explicit-mode")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-explicit-mode",
        raw_user_input="how many calories are left?",
        mode="fallback_answer",
        local_date="2026-04-18",
    )

    assert result.disposition == "answer_only"
    assert result.workflow_effect == "answer_general_product_question_without_state_mutation"
    assert result.required_read_surfaces == []


def test_general_chat_has_no_state_mutation_side_effects() -> None:
    db = _session()
    _bootstrap_user(db, "general-chat-no-mutation")
    before_body_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()
    before_meal_thread_count = db.query(MealThreadRecord).count()

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-no-mutation",
        raw_user_input="any text",
        mode="budget_summary",
        local_date="2026-04-18",
    )

    assert result.disposition == "answer_only"
    assert db.query(BodyPlanRecord).count() == before_body_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count
    assert db.query(MealThreadRecord).count() == before_meal_thread_count


def test_general_chat_open_workflow_boundary_does_not_silently_enter_intake() -> None:
    db = _session()
    get_or_create_user(db, "general-chat-open-workflow")

    result = build_general_chat_response_pass(
        db,
        user_external_id="general-chat-open-workflow",
        raw_user_input="log chicken rice",
        mode="workflow_handoff",
        local_date="2026-04-18",
    )

    assert result.target_workflow_family == "general_chat"
    assert result.disposition == "open_new_workflow"
    assert result.workflow_effect == "handoff_to_formal_workflow"
