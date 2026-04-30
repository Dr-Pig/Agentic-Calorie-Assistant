from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.runtime.agent.manager_fallback_policy import fallback_decision
from app.runtime.agent.manager_payload_utils import (
    json_safe,
    observed_type_name,
    tool_names,
    value_excerpt,
)
from app.runtime.contracts.phase_a import ManagerSemanticDecision


@dataclass(frozen=True)
class IntakeManagerResult:
    intent: str
    manager_action: str
    final_action: str
    workflow_effect: str
    target_attachment: dict[str, Any] = field(default_factory=dict)
    exactness: str = "unknown"
    confidence: str = "unknown"
    evidence_posture: str = "unknown"
    repair_ack: bool = False
    answer_contract: dict[str, Any] = field(default_factory=dict)
    uncertainty_posture: str = "unknown"
    evidence_honesty_posture: str = "unknown"
    semantic_decision: dict[str, Any] = field(default_factory=dict)
    intent_type: str = "log_meal"
    response_summary: str = ""
    pending_followup: str | None = None
    tool_calls: tuple[str, ...] = field(default_factory=tuple)
    tool_results: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    manager_rounds: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    guard_outcome: dict[str, Any] = field(default_factory=dict)
    repair_round_used: bool = False
    request_failure_family: str | None = None
    llm_used: bool = False
    trace: dict[str, Any] = field(default_factory=dict)


class ManagerFinalPayloadShapeError(RuntimeError):
    def __init__(self, *, field_name: str, observed_value: Any) -> None:
        self.field_name = field_name
        self.observed_value = json_safe(observed_value)
        self.observed_type = observed_type_name(observed_value)
        self.value_excerpt, self.value_truncated = value_excerpt(observed_value)
        super().__init__(f"manager final payload field {field_name} expected object, got {self.observed_type}")


def _non_authoritative_semantic_decision(*, semantic_authority: str, source: str) -> dict[str, Any]:
    return ManagerSemanticDecision(
        semantic_authority=semantic_authority,  # type: ignore[arg-type]
        current_turn_intent="unknown",
        target_attachment={},
        workflow_effect="none",
        final_action_candidate="no_commit",
        estimation_posture="unknown",
        followup_posture="none",
        mutation_intent_candidate="unknown",
        uncertainty_posture="unknown",
        source=source,
    ).model_dump(mode="json")


def _semantic_decision_from_payload(payload: dict[str, Any]) -> dict[str, Any]:
    raw_decision = payload.get("semantic_decision")
    if not isinstance(raw_decision, dict):
        return _non_authoritative_semantic_decision(
            semantic_authority="missing",
            source="missing_manager_semantic_decision",
        )
    try:
        return ManagerSemanticDecision.model_validate(raw_decision).model_dump(mode="json")
    except Exception:
        return _non_authoritative_semantic_decision(
            semantic_authority="missing",
            source="invalid_manager_semantic_decision",
        )


def fallback_result(*, raw_user_input: str, onboarding_payload: dict[str, Any] | None, resolved_state: Any) -> IntakeManagerResult:
    if onboarding_payload is not None:
        fallback = fallback_decision(
            raw_user_input=raw_user_input,
            onboarding_payload=onboarding_payload,
            onboarding_ready=bool(getattr(resolved_state, "onboarding_ready", False)),
        )
        return IntakeManagerResult(
            intent=str(getattr(fallback, "intent_type", "complete_onboarding") or "complete_onboarding"),
            manager_action="final",
            final_action="commit",
            workflow_effect=fallback.workflow_effect,
            target_attachment={},
            exactness="unknown",
            confidence="fallback",
            evidence_posture="fallback",
            repair_ack=False,
            answer_contract={"response_summary": fallback.response_summary},
            uncertainty_posture="fallback",
            evidence_honesty_posture="fallback",
            semantic_decision=_non_authoritative_semantic_decision(
                semantic_authority="degraded_fallback",
                source="fallback_structured_onboarding_degraded_mode",
            ),
            intent_type=fallback.intent_type,
            response_summary=fallback.response_summary,
            pending_followup=fallback.pending_followup,
            tool_calls=fallback.tool_calls,
            llm_used=False,
            trace={"decision_source": "fallback_structured_onboarding_degraded_mode"},
        )
    return IntakeManagerResult(
        intent="manager_unavailable",
        manager_action="final",
        final_action="no_commit",
        workflow_effect="safe_failure",
        target_attachment={},
        exactness="unknown",
        confidence="fallback",
        evidence_posture="fallback",
        repair_ack=False,
        answer_contract={"response_summary": "Manager provider is unavailable; no semantic decision was made."},
        uncertainty_posture="fallback",
        evidence_honesty_posture="fallback",
        semantic_decision=_non_authoritative_semantic_decision(
            semantic_authority="degraded_fallback",
            source="fallback_single_manager_degraded_mode",
        ),
        intent_type="manager_unavailable",
        response_summary="Manager provider is unavailable; no semantic decision was made.",
        pending_followup=None,
        tool_calls=(),
        llm_used=False,
        trace={"decision_source": "fallback_single_manager_degraded_mode"},
    )


def result_from_payload(
    payload: dict[str, Any],
    *,
    manager_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    guard_outcome: dict[str, Any] | None = None,
    repair_round_used: bool = False,
    llm_used: bool = True,
    failure_family: str | None = None,
) -> IntakeManagerResult:
    answer_contract = payload.get("answer_contract") if isinstance(payload.get("answer_contract"), dict) else {}
    raw_target_attachment = payload.get("target_attachment")
    if raw_target_attachment not in (None, "") and not isinstance(raw_target_attachment, dict):
        raise ManagerFinalPayloadShapeError(field_name="target_attachment", observed_value=raw_target_attachment)
    semantic_decision = _semantic_decision_from_payload(payload)
    explicit_final_action = str(payload.get("final_action") or "")
    semantic_final_action = str(semantic_decision.get("final_action_candidate") or "")
    final_action = explicit_final_action or semantic_final_action or "no_commit"
    final_action_source = "payload.final_action" if explicit_final_action else (
        "semantic_decision.final_action_candidate" if semantic_final_action else "default_no_commit"
    )
    return IntakeManagerResult(
        intent=str(payload.get("intent") or payload.get("intent_type") or "log_meal"),
        manager_action=str(payload.get("manager_action") or "final"),
        final_action=final_action,
        workflow_effect=str(payload.get("workflow_effect") or "none"),
        target_attachment=dict(payload.get("target_attachment") or {}),
        exactness=str(payload.get("exactness") or "unknown"),
        confidence=str(payload.get("confidence") or "unknown"),
        evidence_posture=str(payload.get("evidence_posture") or payload.get("evidence_honesty_posture") or "unknown"),
        repair_ack=bool(payload.get("repair_ack")),
        answer_contract=dict(answer_contract or {}),
        uncertainty_posture=str(payload.get("uncertainty_posture") or "unknown"),
        evidence_honesty_posture=str(payload.get("evidence_honesty_posture") or "unknown"),
        semantic_decision=semantic_decision,
        intent_type=str(payload.get("intent_type") or "log_meal"),
        response_summary=str(payload.get("response_summary") or answer_contract.get("reply_text") or ""),
        pending_followup=payload.get("pending_followup") if payload.get("pending_followup") is not None else None,
        tool_calls=tool_names(payload.get("tool_calls") or []),
        tool_results=tuple(json_safe(tool_results)),
        manager_rounds=tuple(json_safe(manager_rounds)),
        guard_outcome=dict(guard_outcome or {}),
        repair_round_used=repair_round_used,
        request_failure_family=failure_family,
        llm_used=llm_used,
        trace={
            "decision_source": "single_manager_loop",
            "manager_rounds": json_safe(manager_rounds),
            "tool_results": json_safe(tool_results),
            "guard_outcome": json_safe(guard_outcome or {}),
            "repair_round_used": repair_round_used,
            "request_failure_family": failure_family,
            "semantic_decision": semantic_decision,
            "final_action_source": final_action_source,
        },
    )


def payload_shape_failure_result(
    payload: dict[str, Any],
    *,
    manager_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    guard_outcome: dict[str, Any] | None = None,
    repair_round_used: bool = False,
    field_error: ManagerFinalPayloadShapeError,
) -> IntakeManagerResult:
    return IntakeManagerResult(
        intent=str(payload.get("intent") or payload.get("intent_type") or "log_meal"),
        manager_action="final",
        final_action="no_commit",
        workflow_effect="safe_failure",
        target_attachment={},
        exactness="unknown",
        confidence="unknown",
        evidence_posture="unknown",
        repair_ack=False,
        answer_contract={},
        uncertainty_posture="unknown",
        evidence_honesty_posture="unknown",
        semantic_decision=_non_authoritative_semantic_decision(
            semantic_authority="missing",
            source="final_payload_shape_error",
        ),
        intent_type=str(payload.get("intent_type") or "log_meal"),
        response_summary="",
        pending_followup=None,
        tool_calls=tool_names(payload.get("tool_calls") or []),
        tool_results=tuple(json_safe(tool_results)),
        manager_rounds=tuple(json_safe(manager_rounds)),
        guard_outcome=dict(guard_outcome or {}),
        repair_round_used=repair_round_used,
        request_failure_family="final_payload_shape_error",
        llm_used=True,
        trace={
            "decision_source": "single_manager_loop",
            "manager_rounds": json_safe(manager_rounds),
            "tool_results": json_safe(tool_results),
            "guard_outcome": json_safe(guard_outcome or {}),
            "repair_round_used": repair_round_used,
            "request_failure_family": "final_payload_shape_error",
            "semantic_decision": _non_authoritative_semantic_decision(
                semantic_authority="missing",
                source="final_payload_shape_error",
            ),
            "payload_shape_error": {
                "field_name": field_error.field_name,
                "observed_type": field_error.observed_type,
                "value_excerpt": field_error.value_excerpt,
                "value_truncated": field_error.value_truncated,
            },
        },
    )
