from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application.body_observation_service import record_body_observation_to_canonical
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


async def test_execute_non_fooddb_read_tool_calls_supports_public_budget_tools() -> None:
    db = _session()
    user = _bootstrap_budget_state(db, user_external_id="read-tool-public-budget")

    results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[
            {"name": "budget.get_remaining_calories"},
            {"name": "budget.get_day_meal_log"},
        ],
    )

    assert [result["tool_name"] for result in results] == [
        "budget.get_remaining_calories",
        "budget.get_day_meal_log",
    ]
    for result in results:
        assert result["provenance"]["canonical_tool_name"] == "read_day_budget"
        assert result["provenance"]["tool_kind"] == "read_only"
        assert result["provenance"]["mutation_authority"] is False
        assert result["mutation_result"] == {}
    assert results[0]["provenance"]["truth_owner"] == "budget_domain"
    assert results[0]["evidence"]["remaining_budget_contract"]["remaining_kcal"] >= 0
    assert results[1]["provenance"]["truth_owner"] == "intake_and_budget_projection"
    assert results[1]["evidence"]["current_budget_view"]["meals"]


async def test_execute_non_fooddb_read_tool_calls_supports_public_body_weight_tool() -> None:
    db = _session()
    user = _bootstrap_budget_state(db, user_external_id="read-tool-public-body-weight")
    record_body_observation_to_canonical(
        db,
        user=user,
        value=57.8,
        unit="kg",
        observed_at=datetime(2026, 5, 6, 7, 30, 0),
        local_date="2026-05-06",
    )

    results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[{"name": "body.get_latest_observation"}],
    )

    assert len(results) == 1
    result = results[0]
    assert result["tool_name"] == "body.get_latest_observation"
    assert result["provenance"]["canonical_tool_name"] == "read_latest_weight_observation"
    assert result["provenance"]["truth_owner"] == "body_domain"
    assert result["provenance"]["mutation_authority"] is False
    assert result["evidence"]["latest_weight_status"] == "available"
    assert result["evidence"]["latest_weight_observation"]["value"] == 57.8


async def test_execute_non_fooddb_read_tool_calls_supports_public_calibration_inbox_read() -> None:
    db = _session()
    user = _bootstrap_budget_state(db, user_external_id="read-tool-public-calibration")

    results = await execute_non_fooddb_read_tool_calls(
        db=db,
        user_id=user.id,
        local_date="2026-05-06",
        tool_calls=[{"name": "calibration.get_pending_proposal"}],
    )

    assert len(results) == 1
    result = results[0]
    assert result["tool_name"] == "calibration.get_pending_proposal"
    assert result["provenance"]["canonical_tool_name"] == "read_calibration_pending_proposal"
    assert result["provenance"]["truth_owner"] == "calibration_domain"
    assert result["provenance"]["tool_kind"] == "read_only"
    assert result["provenance"]["mutation_authority"] is False
    assert result["evidence"]["pending_proposal_status"] == "not_available"
    assert result["evidence"]["proposal_count"] == 0
