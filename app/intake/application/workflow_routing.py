from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

WorkflowFamily = Literal[
    "intake",
    "calibration",
    "body_observation",
    "general_chat",
]
WorkflowDisposition = Literal[
    "create",
    "continue",
    "correct",
    "accept",
    "reject",
    "defer",
    "adjust",
    "answer_only",
    "open_new_workflow",
]
RoutingConfidence = Literal["high", "medium", "low"]
AmbiguityPosture = Literal["none", "allow_uncertain"]


@dataclass(frozen=True)
class WorkflowRoutingStateHints:
    has_open_rescue_proposal: bool = False
    has_pending_intake_followup: bool = False
    has_active_body_plan: bool = False
    recent_message_summary: tuple[str, ...] = ()


@dataclass(frozen=True)
class WorkflowRoutingResult:
    target_workflow_family: WorkflowFamily
    disposition: WorkflowDisposition
    routing_confidence: RoutingConfidence
    ambiguity_posture: AmbiguityPosture
    reasoning_summary: str
    required_read_surfaces: list[str] = field(default_factory=list)


def _contains_any(text: str, keywords: tuple[str, ...]) -> bool:
    return any(token and token in text for token in keywords)


def _looks_like_remaining_budget_query(text: str) -> bool:
    return _contains_any(
        text,
        ("?拙?撠?", "?格?", "remaining", "budget", "calorie", "kcal"),
    )


def _looks_like_body_observation_create(text: str) -> bool:
    return _contains_any(
        text,
        ("??憭?", "kg", "weight", "?祆"),
    ) and _contains_any(text, ("??", "update", "?曉", "隞予"))


def _looks_like_calibration_request(text: str) -> bool:
    return _contains_any(
        text,
        ("?餈瘝", "adjust", "change plan", "body plan"),
    )


def _looks_like_intake_continuation(text: str, *, has_pending_intake_followup: bool) -> bool:
    if not has_pending_intake_followup:
        return False
    return not _contains_any(text, ("?拙?", "kg", "adjust", "plan", "budget")) and bool(text.strip())


def _looks_like_intake_request(text: str) -> bool:
    return _contains_any(
        text,
        ("????", "??鈭?", "meal", "eat", "ate", "log", "閮?銝?"),
    )


def build_workflow_routing_decision(
    *,
    raw_user_input: str,
    state_hints: WorkflowRoutingStateHints | None = None,
) -> WorkflowRoutingResult:
    hints = state_hints or WorkflowRoutingStateHints()
    text = raw_user_input.strip()

    if _looks_like_remaining_budget_query(text):
        surfaces = ["CurrentBudgetView"]
        if _contains_any(text, ("?格?", "goal", "plan")):
            surfaces.append("ActiveBodyPlanView")
        return WorkflowRoutingResult(
            target_workflow_family="general_chat",
            disposition="answer_only",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="budget-or-goal query uses shared read surfaces and should stay in general_chat",
            required_read_surfaces=surfaces,
        )

    if _looks_like_calibration_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="calibration",
            disposition="open_new_workflow",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="explicit plan-adjustment request belongs to calibration family",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
        )

    if _looks_like_body_observation_create(text):
        return WorkflowRoutingResult(
            target_workflow_family="body_observation",
            disposition="create",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="body metric update should route to body_observation create path",
            required_read_surfaces=[],
        )

    if _looks_like_intake_continuation(text, has_pending_intake_followup=hints.has_pending_intake_followup):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="continue",
            routing_confidence="medium",
            ambiguity_posture="none",
            reasoning_summary="pending intake follow-up is present, so this turn continues intake by default",
            required_read_surfaces=[],
        )

    if _looks_like_intake_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="open_new_workflow",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="meal logging request should hand off into intake",
            required_read_surfaces=[],
        )

    return WorkflowRoutingResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        routing_confidence="low",
        ambiguity_posture="allow_uncertain",
        reasoning_summary="no formal workflow signal dominated, so stay in general_chat with ambiguity visible",
        required_read_surfaces=[],
    )
