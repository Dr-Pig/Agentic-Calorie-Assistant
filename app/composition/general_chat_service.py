from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Literal

from sqlalchemy.orm import Session

from app.body.application import build_active_body_plan_view
from app.composition.calibration_commit_bridge import (
    CalibrationCommitDecision,
    apply_stored_calibration_proposal_action,
)
from app.composition.calibration_preview_service import build_calibration_preview_from_history
from app.composition.current_budget_answer import build_remaining_budget_answer_contract
from app.database import get_or_create_user
from app.shared.infra.models import User

GeneralChatDisposition = Literal["answer_only", "open_new_workflow"]
GeneralChatMode = Literal[
    "budget_summary",
    "goal_summary",
    "workflow_handoff",
    "calibration_preview",
    "calibration_action",
    "fallback_answer",
]
CalibrationChatAction = Literal[
    "accept_calibration_proposal",
    "defer_calibration_proposal",
    "reject_calibration_proposal",
]


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
    calibration_diagnostic: dict[str, Any] | None = None
    calibration_action_result: dict[str, Any] | None = None
    input_assembly: dict[str, Any] | None = None
    proposal_artifact: dict[str, Any] | None = None


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


def _calibration_unavailable_response(*, reason: str) -> GeneralChatPassResult:
    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="calibration_preview_unavailable_without_state_mutation",
        required_read_surfaces=[
            "CalibrationInputAssembly",
            "CurrentBudgetView",
            "ActiveBodyPlanView",
            "CalibrationProposalPolicyPacket",
        ],
        reply_text=f"Calibration preview is unavailable: {reason}.",
        asked_follow_up=False,
        ui_hints={
            "mode": "general_chat_calibration_preview_unavailable",
            "delivery": "chat_primary_ui_mirror",
            "reason": reason,
            "proposal_actions_enabled": False,
            "root_route_activation": "active",
            "plan_mutation_authorized": False,
            "ledger_mutation_authorized": False,
        },
    )


def _calibration_action_unavailable_response(*, reason: str) -> GeneralChatPassResult:
    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="calibration_action_unavailable_without_state_mutation",
        required_read_surfaces=[
            "calibration_proposal_inbox",
            "CurrentBudgetView",
            "ActiveBodyPlanView",
            "body_budget_effective_budget_view",
        ],
        reply_text=f"Calibration proposal action is unavailable: {reason}.",
        asked_follow_up=False,
        ui_hints={
            "mode": "general_chat_calibration_action_unavailable",
            "delivery": "chat_primary_ui_mirror",
            "reason": reason,
            "plan_mutation_authorized": False,
            "ledger_mutation_authorized": False,
        },
    )


def _calibration_decision_from_action(action: CalibrationChatAction) -> CalibrationCommitDecision:
    action_map: dict[str, CalibrationCommitDecision] = {
        "accept_calibration_proposal": "accepted",
        "defer_calibration_proposal": "dismissed",
        "reject_calibration_proposal": "rejected",
    }
    return action_map[action]


def _calibration_action_response(
    db: Session,
    *,
    user: User,
    proposal_container_id: int | None,
    action: CalibrationChatAction | None,
    accepted_at: datetime | None,
) -> GeneralChatPassResult:
    if proposal_container_id is None or action is None:
        return _calibration_action_unavailable_response(reason="missing_explicit_proposal_container_id_or_action")

    try:
        result = apply_stored_calibration_proposal_action(
            db,
            user=user,
            proposal_container_id=proposal_container_id,
            decision=_calibration_decision_from_action(action),
            accepted_at=accepted_at,
        )
    except ValueError as exc:
        return _calibration_action_unavailable_response(reason=str(exc))

    current_budget = result.current_budget_view.model_dump(mode="json")
    active_body_plan = result.active_body_plan_view.model_dump(mode="json")
    action_payload = {
        "proposal_container_id": result.proposal_container_id,
        "proposal_status": result.proposal_status,
        "body_plan_id": result.body_plan_id,
        "effective_from": result.effective_from,
        "current_budget_view": current_budget,
        "active_body_plan_view": active_body_plan,
    }
    state_mutated = result.proposal_status == "accepted" and result.body_plan_id is not None
    if result.proposal_status == "accepted":
        reply_text = (
            f"Calibration proposal accepted. Effective from {result.effective_from}. "
            f"Daily target: {current_budget.get('budget_kcal')} kcal. "
            f"Remaining: {current_budget.get('remaining_kcal')} kcal."
        )
    elif result.proposal_status == "rejected":
        reply_text = "Calibration proposal rejected. Your active plan was not changed."
    elif result.proposal_status == "dismissed":
        reply_text = "Calibration proposal dismissed for now. Your active plan was not changed."
    else:
        reply_text = "Calibration proposal closed. Your active plan was not changed."

    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect=(
            "apply_calibration_proposal_action_with_state_mutation"
            if state_mutated
            else "apply_calibration_proposal_action_without_plan_mutation"
        ),
        required_read_surfaces=[
            "calibration_proposal_inbox",
            "CurrentBudgetView",
            "ActiveBodyPlanView",
            "body_budget_effective_budget_view",
        ],
        reply_text=reply_text,
        asked_follow_up=False,
        ui_hints={
            "mode": "general_chat_calibration_action",
            "delivery": "chat_primary_ui_mirror",
            "proposal_container_id": result.proposal_container_id,
            "proposal_status": result.proposal_status,
            "effective_from": result.effective_from,
            "plan_mutation_authorized": state_mutated,
            "ledger_mutation_authorized": state_mutated,
            "automatic_calibration_enabled": False,
        },
        calibration_action_result=action_payload,
    )


def _calibration_preview_response(
    db: Session,
    *,
    user: User,
    local_date: str,
    persist_calibration_proposal: bool,
) -> GeneralChatPassResult:
    try:
        preview = build_calibration_preview_from_history(
            db,
            user=user,
            local_date=local_date,
            persist_proposal=persist_calibration_proposal,
        )
    except ValueError as exc:
        return _calibration_unavailable_response(reason=str(exc))

    proposal_actions_enabled = preview.proposal_artifact is not None
    response = preview.response
    proposal_family = response.get("proposal_family")
    if response.get("surfaced") is True:
        reply_text = (
            f"Calibration preview surfaced {proposal_family}. "
            "Plan changes still require explicit proposal acceptance."
        )
    else:
        gate_result = preview.gate_result
        rationale = "; ".join(gate_result.get("gate_rationale") or []) or str(gate_result.get("primary_policy_posture"))
        reply_text = f"Calibration preview did not surface a plan-change proposal: {rationale}."

    return GeneralChatPassResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        workflow_effect="preview_calibration_proposal_without_plan_mutation",
        required_read_surfaces=[
            "CalibrationInputAssembly",
            "CurrentBudgetView",
            "ActiveBodyPlanView",
            "CalibrationProposalPolicyPacket",
        ],
        reply_text=reply_text,
        asked_follow_up=False,
        ui_hints={
            "mode": "general_chat_calibration_preview",
            "delivery": "chat_primary_ui_mirror",
            "proposal_surface": response.get("surfaced") is True,
            "proposal_family": proposal_family,
            "proposal_actions_enabled": proposal_actions_enabled,
            "proposal_container_id": (
                preview.proposal_artifact.get("proposal_container_id")
                if preview.proposal_artifact is not None
                else None
            ),
            "stored_action_route_contract": (
                "/calibration/proposal/stored-action" if proposal_actions_enabled else None
            ),
            "root_route_activation": "active",
            "automatic_calibration_enabled": False,
            "plan_mutation_authorized": False,
            "ledger_mutation_authorized": False,
        },
        calibration_diagnostic={
            "calibration_result": preview.calibration_result,
            "gate_result": preview.gate_result,
            "proposal_policy_packet": preview.proposal_policy_packet,
            "trace_envelope": preview.trace_envelope,
        },
        input_assembly=preview.input_assembly,
        proposal_artifact=preview.proposal_artifact,
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
    persist_calibration_proposal: bool = False,
    calibration_proposal_container_id: int | None = None,
    calibration_action: CalibrationChatAction | None = None,
    accepted_at: datetime | None = None,
) -> GeneralChatPassResult:
    del raw_user_input
    user = get_or_create_user(db, user_external_id)

    if mode == "budget_summary":
        return _budget_summary_response(db, user_id=user.id, local_date=local_date)
    if mode == "goal_summary":
        return _goal_summary_response(db, user_id=user.id)
    if mode == "workflow_handoff":
        return _workflow_handoff_response()
    if mode == "calibration_preview":
        return _calibration_preview_response(
            db,
            user=user,
            local_date=local_date,
            persist_calibration_proposal=persist_calibration_proposal,
        )
    if mode == "calibration_action":
        return _calibration_action_response(
            db,
            user=user,
            proposal_container_id=calibration_proposal_container_id,
            action=calibration_action,
            accepted_at=accepted_at,
        )
    return _fallback_answer_response()
