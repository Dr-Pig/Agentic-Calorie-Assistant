from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.body.application import build_active_body_plan_view
from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.database import get_or_create_user

GeneralChatDisposition = Literal["answer_only", "open_new_workflow"]
GeneralChatMode = Literal["budget_summary", "goal_summary", "workflow_handoff", "fallback_answer"]


@dataclass(frozen=True)
class GeneralChatPassResult:
    target_workflow_family: Literal["general_chat"]
    disposition: GeneralChatDisposition
    workflow_effect: str
    required_read_surfaces: list[str]
    reply_text: str
    asked_follow_up: bool
    ui_hints: dict[str, Any]
    remaining_budget_contract: Any | None = None
    active_body_plan_present: bool | None = None


def _budget_summary_response(db: Session, *, user_id: int, local_date: str) -> GeneralChatPassResult:
    answer = build_remaining_budget_answer_contract(db, user_id=user_id, local_date=local_date)
    if answer.status == "onboarding_required":
        consumed_clause = (
            f"I can see {answer.consumed_kcal} kcal consumed today, but "
            if int(answer.consumed_kcal or 0) > 0
            else ""
        )
        return GeneralChatPassResult(
            target_workflow_family="general_chat",
            disposition="answer_only",
            workflow_effect="answer_budget_summary_without_state_mutation",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
            reply_text=f"{consumed_clause}onboarding is required before I can answer remaining budget.",
            asked_follow_up=False,
            ui_hints={"mode": "general_chat_onboarding_required", "delivery": "chat_only"},
            remaining_budget_contract=answer,
            active_body_plan_present=False,
        )
    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="answer_budget_summary_without_state_mutation",
        required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
        reply_text=(
            f"Daily target: {answer.daily_target_kcal} kcal. "
            f"Consumed: {answer.consumed_kcal} kcal. "
            f"Remaining: {answer.remaining_kcal} kcal."
        ),
        asked_follow_up=False,
        ui_hints={
            "mode": "general_chat_budget_answer",
            "delivery": "chat_only",
            "meal_count": answer.meal_count,
        },
        remaining_budget_contract=answer,
        active_body_plan_present=True,
    )


def _goal_summary_response(db: Session, *, user_id: int) -> GeneralChatPassResult:
    active_plan = build_active_body_plan_view(db, user_id=user_id)
    if active_plan.body_plan_id is None:
        return GeneralChatPassResult(
            target_workflow_family="general_chat",
            disposition="answer_only",
            workflow_effect="answer_goal_summary_without_state_mutation",
            required_read_surfaces=["ActiveBodyPlanView"],
            reply_text="No active body plan is available yet.",
            asked_follow_up=False,
            ui_hints={"mode": "general_chat_goal_unavailable", "delivery": "chat_only"},
            active_body_plan_present=False,
        )
    goal_type = active_plan.goal_type or "unknown"
    plan_source = active_plan.plan_source or "unknown"
    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="answer_goal_summary_without_state_mutation",
        required_read_surfaces=["ActiveBodyPlanView"],
        reply_text=f"Your current goal is {goal_type}. Active daily budget: {active_plan.daily_budget_kcal} kcal.",
        asked_follow_up=False,
        ui_hints={
            "mode": "general_chat_goal_answer",
            "delivery": "chat_only",
            "plan_source": plan_source,
        },
        active_body_plan_present=True,
    )


def _workflow_handoff_response() -> GeneralChatPassResult:
    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="open_new_workflow",
        workflow_effect="handoff_to_formal_workflow",
        required_read_surfaces=[],
        reply_text="That needs a formal workflow decision before any state change.",
        asked_follow_up=False,
        ui_hints={"mode": "general_chat_open_workflow_boundary", "delivery": "chat_only"},
    )


def _fallback_answer_response() -> GeneralChatPassResult:
    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="answer_general_product_question_without_state_mutation",
        required_read_surfaces=[],
        reply_text="I can answer general product questions here, but I will not change state from this path.",
        asked_follow_up=False,
        ui_hints={"mode": "general_chat_fallback_answer", "delivery": "chat_only"},
    )


def build_general_chat_response_pass(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    mode: GeneralChatMode,
    local_date: str,
) -> GeneralChatPassResult:
    del raw_user_input
    user = get_or_create_user(db, user_external_id)

    if mode == "budget_summary":
        return _budget_summary_response(db, user_id=user.id, local_date=local_date)
    if mode == "goal_summary":
        return _goal_summary_response(db, user_id=user.id)
    if mode == "workflow_handoff":
        return _workflow_handoff_response()
    return _fallback_answer_response()
