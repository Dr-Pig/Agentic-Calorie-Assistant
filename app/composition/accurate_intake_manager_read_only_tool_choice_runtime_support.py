from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.body.application.body_observation_service import record_body_observation_to_canonical
from app.composition.canonical_persistence import commit_meal_payload_to_canonical
from app.composition.onboarding_service import (
    OnboardingBootstrapInput,
    bootstrap_body_plan_for_date,
)
from app.database import get_or_create_user
from app.models import Base
from app.runtime.agent.manager_result_builder import IntakeManagerResult
from app.schemas import CommitRequestCandidate


REQUIRED_CASE_IDS = (
    "budget_remaining_runtime_read",
    "budget_day_meal_log_runtime_read",
    "body_active_plan_runtime_read",
    "body_latest_observation_runtime_read",
    "calibration_pending_proposal_runtime_read",
    "app_usage_help_runtime_read",
)


@dataclass(frozen=True)
class RuntimeCase:
    case_id: str
    selected_tool: str
    intent_type: str
    workflow_effect: str
    reply_text: str
    latest_weight_required: bool = False


def build_runtime_session() -> Session:
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def bootstrap_runtime_state(
    db: Session,
    *,
    user_external_id: str,
    latest_weight_required: bool,
) -> Any:
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
            request_id=f"{user_external_id}-breakfast",
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
    if latest_weight_required:
        record_body_observation_to_canonical(
            db,
            user=user,
            value=57.8,
            unit="kg",
            observed_at=datetime(2026, 5, 6, 7, 30, 0),
            local_date="2026-05-06",
        )
    return user


def runtime_cases() -> list[RuntimeCase]:
    return [
        RuntimeCase(
            case_id="budget_remaining_runtime_read",
            selected_tool="budget.get_remaining_calories",
            intent_type="answer_remaining_budget",
            workflow_effect="answer_budget_summary_without_state_mutation",
            reply_text="use remaining budget renderer",
        ),
        RuntimeCase(
            case_id="budget_day_meal_log_runtime_read",
            selected_tool="budget.get_day_meal_log",
            intent_type="general_chat",
            workflow_effect="answer_day_meal_log_without_state_mutation",
            reply_text="Day meal log is available from the budget read model.",
        ),
        RuntimeCase(
            case_id="body_active_plan_runtime_read",
            selected_tool="body.get_active_plan",
            intent_type="general_chat",
            workflow_effect="answer_goal_summary_without_state_mutation",
            reply_text="Active body plan is available from the body read model.",
        ),
        RuntimeCase(
            case_id="body_latest_observation_runtime_read",
            selected_tool="body.get_latest_observation",
            intent_type="general_chat",
            workflow_effect="answer_latest_weight_without_state_mutation",
            reply_text="Latest weight is available from the body read model.",
            latest_weight_required=True,
        ),
        RuntimeCase(
            case_id="calibration_pending_proposal_runtime_read",
            selected_tool="calibration.get_pending_proposal",
            intent_type="general_chat",
            workflow_effect="answer_calibration_pending_proposal_without_state_mutation",
            reply_text="No pending calibration proposal is available.",
        ),
        RuntimeCase(
            case_id="app_usage_help_runtime_read",
            selected_tool="app.answer_usage_question",
            intent_type="general_chat",
            workflow_effect="answer_general_product_question_without_state_mutation",
            reply_text="I can answer general product questions here, but I will not change state from this path.",
        ),
    ]


def build_fixture_manager_decision(case: RuntimeCase, tool_results: list[dict[str, Any]]) -> IntakeManagerResult:
    return IntakeManagerResult(
        intent=case.intent_type,
        manager_action="final",
        final_action="answer_only",
        workflow_effect=case.workflow_effect,
        target_attachment={"mode": "read_only_answer"},
        exactness="read_only_state",
        confidence="high",
        evidence_posture="read_only_state",
        repair_ack=False,
        answer_contract={"reply_text": case.reply_text},
        uncertainty_posture="bounded",
        evidence_honesty_posture="read_only_state",
        semantic_decision={
            "semantic_authority": "fixture_manager_structured_decision",
            "current_turn_intent": case.intent_type,
            "target_attachment": {"mode": "read_only_answer"},
            "workflow_effect": case.workflow_effect,
            "final_action_candidate": "answer_only",
            "estimation_posture": "not_applicable",
            "followup_posture": "none",
            "followup_targets": [],
            "mutation_intent_candidate": "no_mutation",
            "uncertainty_posture": "bounded",
            "source": "accurate_intake_manager_read_only_tool_choice_runtime_smoke",
        },
        intent_type=case.intent_type,
        response_summary=case.workflow_effect,
        pending_followup=None,
        tool_calls=(case.selected_tool,),
        tool_results=tuple(tool_results),
        manager_rounds=(),
        guard_outcome={},
        repair_round_used=False,
        request_failure_family=None,
        llm_used=False,
        trace={},
    )


__all__ = [
    "REQUIRED_CASE_IDS",
    "RuntimeCase",
    "bootstrap_runtime_state",
    "build_fixture_manager_decision",
    "build_runtime_session",
    "runtime_cases",
]
