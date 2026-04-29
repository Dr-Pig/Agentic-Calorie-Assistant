from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from sqlalchemy.orm import Session

from ...body.application import build_active_body_plan_view
from ...budget.application import build_remaining_budget_answer_contract
from ...database import get_or_create_user

GeneralChatDisposition = Literal["answer_only", "open_new_workflow"]


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


def _looks_like_remaining_budget_query(text: str) -> bool:
    normalized = text.strip()
    keywords = (
        "還能吃多少",
        "還剩多少",
        "剩多少",
        "剩餘熱量",
        "剩下多少熱量",
    )
    return any(token in normalized for token in keywords)


def _looks_like_goal_query(text: str) -> bool:
    normalized = text.strip()
    keywords = (
        "目標",
        "每日目標",
        "熱量目標",
    )
    return any(token in normalized for token in keywords)


def _looks_like_open_workflow_request(text: str) -> bool:
    normalized = text.strip()
    keywords = (
        "我剛吃了",
        "晚餐我吃",
        "午餐我吃",
        "早餐我吃",
        "幫我記",
        "記一下",
    )
    return any(token in normalized for token in keywords)


def build_general_chat_response_pass(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
) -> GeneralChatPassResult:
    user = get_or_create_user(db, user_external_id)
    text = raw_user_input.strip()

    if _looks_like_remaining_budget_query(text):
        answer = build_remaining_budget_answer_contract(db, user_id=user.id, local_date=local_date)
        if answer.status == "onboarding_required":
            return GeneralChatPassResult(
                target_workflow_family="general_chat",
                disposition="answer_only",
                workflow_effect="answer_budget_summary_without_state_mutation",
                required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
                reply_text="你現在還沒有可用的 body plan，所以我還不能回答剩餘熱量。先把基本資料補齊後，我就能直接告訴你今天還剩多少。",
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
                f"你今天的目標是 {answer.daily_target_kcal} kcal，"
                f"目前已吃 {answer.consumed_kcal} kcal，"
                f"還剩 {answer.remaining_kcal} kcal。"
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

    if _looks_like_goal_query(text):
        active_plan = build_active_body_plan_view(db, user_id=user.id)
        if active_plan.body_plan_id is None:
            return GeneralChatPassResult(
                target_workflow_family="general_chat",
                disposition="answer_only",
                workflow_effect="answer_goal_summary_without_state_mutation",
                required_read_surfaces=["ActiveBodyPlanView"],
                reply_text="你現在還沒有 active body plan，所以我還沒有正式的每日目標可以回答。先完成基本資料設定後再來看會比較準。",
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
            reply_text=(
                f"你現在的目標方向是 {goal_type}，"
                f"目前 active body plan 的每日目標是 {active_plan.daily_budget_kcal} kcal。"
            ),
            asked_follow_up=False,
            ui_hints={
                "mode": "general_chat_goal_answer",
                "delivery": "chat_only",
                "plan_source": plan_source,
            },
            active_body_plan_present=True,
        )

    if _looks_like_open_workflow_request(text):
        return GeneralChatPassResult(
            target_workflow_family="general_chat",
            disposition="open_new_workflow",
            workflow_effect="handoff_to_formal_workflow",
            required_read_surfaces=[],
            reply_text="這句話比較像是在開一個新的正式 workflow，我會把它交給對應的 workflow 去處理。",
            asked_follow_up=False,
            ui_hints={"mode": "general_chat_open_workflow_boundary", "delivery": "chat_only"},
        )

    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="answer_general_product_question_without_state_mutation",
        required_read_surfaces=[],
        reply_text="我現在可以先回答今天預算、剩餘熱量，或目前的 body plan 目標。",
        asked_follow_up=False,
        ui_hints={"mode": "general_chat_fallback_answer", "delivery": "chat_only"},
    )
