from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

from ...runtime.contracts.phase_a import AttachmentDecision, CurrentTurnContextV1, TransitionGuardResult
from .attachment_resolver import resolve_attachment_decision
from .phase_a_trace import build_phase_a_trace
from .transition_guard import resolve_transition_guard

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
    attachment_decision: AttachmentDecision | None = None
    transition_guard_result: TransitionGuardResult | None = None
    phase_a_trace: dict[str, Any] = field(default_factory=dict)


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
    current_turn_context: CurrentTurnContextV1 | None = None,
    resolved_state: Any | None = None,
) -> WorkflowRoutingResult:
    hints = state_hints or WorkflowRoutingStateHints()
    attachment_decision = None
    transition_guard_result = None
    phase_a_trace: dict[str, Any] = {}
    if current_turn_context is not None:
        hints = WorkflowRoutingStateHints(
            has_open_rescue_proposal=current_turn_context.open_workflow_type == "proposal",
            has_pending_intake_followup=current_turn_context.pending_followup is not None,
            has_active_body_plan=bool(current_turn_context.current_turn_runtime_summary.get("onboarding_ready")),
            recent_message_summary=tuple(
                item
                for item in (current_turn_context.last_system_question, current_turn_context.user_utterance)
                if item
            ),
        )
        attachment_decision = resolve_attachment_decision(current_turn_context)
        transition_guard_result = resolve_transition_guard(current_turn_context, attachment_decision)
        history_activation_trace = None
        if resolved_state is not None:
            from .history_expansion_runtime import activate_pre_manager_history_expansion

            activation = activate_pre_manager_history_expansion(
                current_turn_context=current_turn_context,
                resolved_state=resolved_state,
                pre_attachment_decision=attachment_decision,
                pre_transition_guard_result=transition_guard_result,
            )
            current_turn_context = activation.enriched_current_turn_context
            attachment_decision = activation.post_attachment_decision
            transition_guard_result = activation.post_transition_guard_result
            history_activation_trace = activation.trace_payload() if activation.applied else None
        phase_a_trace = build_phase_a_trace(
            current_turn_context=current_turn_context,
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            history_expansion_activation=history_activation_trace,
        )
    text = raw_user_input.strip()

    if (
        current_turn_context is not None
        and current_turn_context.current_interaction_event.source in {"ui", "smart_chip"}
        and current_turn_context.current_interaction_event.target_object_id
    ):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="correct"
            if attachment_decision is not None and attachment_decision.disposition == "target_committed_thread"
            else "continue",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="explicit interaction target bypasses text-only routing heuristics",
            required_read_surfaces=[],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    if attachment_decision is not None and attachment_decision.disposition == "target_committed_thread":
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="correct",
            routing_confidence=attachment_decision.confidence,
            ambiguity_posture="none" if not attachment_decision.ambiguity_flag else "allow_uncertain",
            reasoning_summary="phase_a_attachment identified a committed meal target for correction handling",
            required_read_surfaces=[],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    if attachment_decision is not None and attachment_decision.disposition == "attach_existing_thread":
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="continue",
            routing_confidence=attachment_decision.confidence,
            ambiguity_posture="none" if not attachment_decision.ambiguity_flag else "allow_uncertain",
            reasoning_summary="phase_a_attachment identified an existing intake thread continuation",
            required_read_surfaces=[],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

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
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    if _looks_like_calibration_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="calibration",
            disposition="open_new_workflow",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="explicit plan-adjustment request belongs to calibration family",
            required_read_surfaces=["CurrentBudgetView", "ActiveBodyPlanView"],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    if _looks_like_body_observation_create(text):
        return WorkflowRoutingResult(
            target_workflow_family="body_observation",
            disposition="create",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="body metric update should route to body_observation create path",
            required_read_surfaces=[],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    if _looks_like_intake_continuation(text, has_pending_intake_followup=hints.has_pending_intake_followup):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="continue",
            routing_confidence="medium",
            ambiguity_posture="none",
            reasoning_summary="pending intake follow-up is present, so this turn continues intake by default",
            required_read_surfaces=[],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    if _looks_like_intake_request(text):
        return WorkflowRoutingResult(
            target_workflow_family="intake",
            disposition="open_new_workflow",
            routing_confidence="high",
            ambiguity_posture="none",
            reasoning_summary="meal logging request should hand off into intake",
            required_read_surfaces=[],
            attachment_decision=attachment_decision,
            transition_guard_result=transition_guard_result,
            phase_a_trace=phase_a_trace,
        )

    return WorkflowRoutingResult(
        target_workflow_family="general_chat",
        disposition="answer_only",
        routing_confidence="low",
        ambiguity_posture="allow_uncertain",
        reasoning_summary="no formal workflow signal dominated, so stay in general_chat with ambiguity visible",
        required_read_surfaces=[],
        attachment_decision=attachment_decision,
        transition_guard_result=transition_guard_result,
        phase_a_trace=phase_a_trace,
    )
