from __future__ import annotations

from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.non_fooddb_read_tool_executor import execute_non_fooddb_read_tool_calls
from app.composition.onboarding_service import (
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_or_create_user
from app.models import Base
from app.schemas import CommitRequestCandidate


def _session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _bootstrap_budget_state(db: Session, *, user_external_id: str) -> Any:
    user = get_or_create_user(db, user_external_id)
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
            local_date="2026-05-06",
        ),
    )
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="budget-read-breakfast",
            manager_intent="food_estimation",
            version_reason="new_intake",
            meal_title="breakfast sandwich",
            raw_input="breakfast sandwich",
            estimated_kcal=420,
            protein_g=18,
            carb_g=32,
            fat_g=14,
            resolution_status="completed_meal",
            local_date="2026-05-06",
        ),
    )
    return user


async def test_execute_non_fooddb_read_tool_calls_returns_read_only_budget_metadata() -> None:
    db = _session()
    user = _bootstrap_budget_state(db, user_external_id="read-tool-budget")

    results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[{"name": "read_day_budget"}],
    )

    assert len(results) == 1
    result = results[0]
    assert result["tool_name"] == "read_day_budget"
    assert result["provenance"]["tool_kind"] == "read_only"
    assert result["provenance"]["mutation_authority"] is False
    assert result["provenance"]["truth_owner"] == "budget_read_model"
    assert result["evidence"]["remaining_budget_contract"]["remaining_kcal"] >= 0


async def test_execute_non_fooddb_read_tool_calls_marks_unknown_tool_without_mutation() -> None:
    db = _session()
    user = _bootstrap_budget_state(db, user_external_id="read-tool-unknown")

    results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[{"name": "not_a_supported_tool"}],
    )

    assert len(results) == 1
    result = results[0]
    assert result["tool_name"] == "not_a_supported_tool"
    assert result["failure_family"] == "unknown_tool"
    assert result["mutation_result"] == {}
    assert result["provenance"]["mutation_authority"] is False


async def test_execute_non_fooddb_read_tool_calls_returns_app_usage_policy_metadata() -> None:
    db = _session()
    user = _bootstrap_budget_state(db, user_external_id="read-tool-app-usage")

    results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[{"name": "answer_usage_question"}],
    )

    assert len(results) == 1
    result = results[0]
    assert result["tool_name"] == "answer_usage_question"
    assert result["provenance"]["tool_kind"] == "read_only"
    assert result["provenance"]["mutation_authority"] is False
    assert result["provenance"]["truth_owner"] == "app_product_policy"
    assert result["evidence"]["app_usage_policy"]["workflow_effect"] == (
        "answer_general_product_question_without_state_mutation"
    )
