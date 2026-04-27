from __future__ import annotations

import inspect
import json
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable

from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.runtime.agent.manager_support import fallback_decision


ToolExecutor = Callable[..., Awaitable[list[dict[str, Any]]] | list[dict[str, Any]]]
GuardChecker = Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]


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


class _ManagerFinalPayloadShapeError(RuntimeError):
    def __init__(self, *, field_name: str, observed_value: Any) -> None:
        self.field_name = field_name
        self.observed_value = _json_safe(observed_value)
        self.observed_type = _observed_type_name(observed_value)
        self.value_excerpt, self.value_truncated = _value_excerpt(observed_value)
        super().__init__(f"manager final payload field {field_name} expected object, got {self.observed_type}")


def _json_safe(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False, default=str))


def _observed_type_name(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, dict):
        return "object"
    if isinstance(value, list):
        return "array"
    if isinstance(value, str):
        return "string"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, (int, float)):
        return "number"
    if isinstance(value, tuple):
        return "tuple"
    return "unknown"


def _value_excerpt(value: Any, *, max_chars: int = 1000) -> tuple[str, bool]:
    rendered = json.dumps(_json_safe(value), ensure_ascii=False, default=str)
    if len(rendered) <= max_chars:
        return rendered, False
    return rendered[:max_chars], True


def _provider_ready(provider: Any) -> bool:
    readiness = provider.readiness() if hasattr(provider, "readiness") else {}
    return bool(readiness.get("configured")) and hasattr(provider, "complete_with_trace")


def _fallback_result(*, raw_user_input: str, onboarding_payload: dict[str, Any] | None, resolved_state: Any) -> IntakeManagerResult:
    fallback = fallback_decision(
        raw_user_input=raw_user_input,
        onboarding_payload=onboarding_payload,
        onboarding_ready=bool(getattr(resolved_state, "onboarding_ready", False)),
    )
    final_action = "commit" if fallback.intent_type in {"complete_onboarding", "log_meal"} else "answer_only"
    return IntakeManagerResult(
        intent=str(getattr(fallback, "intent_type", "log_meal") or "log_meal"),
        manager_action="final",
        final_action=final_action,
        workflow_effect=fallback.workflow_effect,
        target_attachment={},
        exactness="unknown",
        confidence="fallback",
        evidence_posture="fallback",
        repair_ack=False,
        answer_contract={"response_summary": fallback.response_summary},
        uncertainty_posture="fallback",
        evidence_honesty_posture="fallback",
        intent_type=fallback.intent_type,
        response_summary=fallback.response_summary,
        pending_followup=fallback.pending_followup,
        tool_calls=fallback.tool_calls,
        llm_used=False,
        trace={"decision_source": "fallback_single_manager_degraded_mode"},
    )


def _tool_names(raw_tool_calls: Any) -> tuple[str, ...]:
    names: list[str] = []
    if not isinstance(raw_tool_calls, list):
        return tuple()
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
        else:
            name = str(item or "").strip()
        if name:
            names.append(name)
    return tuple(names)


def _tool_call_dicts(raw_tool_calls: Any) -> list[dict[str, Any]]:
    if not isinstance(raw_tool_calls, list):
        return []
    result: list[dict[str, Any]] = []
    for item in raw_tool_calls:
        if isinstance(item, dict):
            name = str(item.get("name") or item.get("tool_name") or "").strip()
            arguments = item.get("arguments") if isinstance(item.get("arguments"), dict) else {}
        else:
            name = str(item or "").strip()
            arguments = {}
        if name:
            result.append({"name": name, "arguments": dict(arguments or {})})
    return result


async def _maybe_await(value: Awaitable[Any] | Any) -> Any:
    if inspect.isawaitable(value):
        return await value
    return value


def _result_from_payload(
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
        raise _ManagerFinalPayloadShapeError(field_name="target_attachment", observed_value=raw_target_attachment)
    return IntakeManagerResult(
        intent=str(payload.get("intent") or payload.get("intent_type") or "log_meal"),
        manager_action=str(payload.get("manager_action") or "final"),
        final_action=str(payload.get("final_action") or "no_commit"),
        workflow_effect=str(payload.get("workflow_effect") or "none"),
        target_attachment=dict(payload.get("target_attachment") or {}),
        exactness=str(payload.get("exactness") or "unknown"),
        confidence=str(payload.get("confidence") or "unknown"),
        evidence_posture=str(payload.get("evidence_posture") or payload.get("evidence_honesty_posture") or "unknown"),
        repair_ack=bool(payload.get("repair_ack")),
        answer_contract=dict(answer_contract or {}),
        uncertainty_posture=str(payload.get("uncertainty_posture") or "unknown"),
        evidence_honesty_posture=str(payload.get("evidence_honesty_posture") or "unknown"),
        intent_type=str(payload.get("intent_type") or "log_meal"),
        response_summary=str(payload.get("response_summary") or answer_contract.get("reply_text") or ""),
        pending_followup=payload.get("pending_followup") if payload.get("pending_followup") is not None else None,
        tool_calls=_tool_names(payload.get("tool_calls") or []),
        tool_results=tuple(_json_safe(tool_results)),
        manager_rounds=tuple(_json_safe(manager_rounds)),
        guard_outcome=dict(guard_outcome or {}),
        repair_round_used=repair_round_used,
        request_failure_family=failure_family,
        llm_used=llm_used,
        trace={
            "decision_source": "single_manager_loop",
            "manager_rounds": _json_safe(manager_rounds),
            "tool_results": _json_safe(tool_results),
            "guard_outcome": _json_safe(guard_outcome or {}),
            "repair_round_used": repair_round_used,
            "request_failure_family": failure_family,
        },
    )


def _payload_shape_failure_result(
    payload: dict[str, Any],
    *,
    manager_rounds: list[dict[str, Any]],
    tool_results: list[dict[str, Any]],
    guard_outcome: dict[str, Any] | None = None,
    repair_round_used: bool = False,
    field_error: _ManagerFinalPayloadShapeError,
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
        intent_type=str(payload.get("intent_type") or "log_meal"),
        response_summary="",
        pending_followup=None,
        tool_calls=_tool_names(payload.get("tool_calls") or []),
        tool_results=tuple(_json_safe(tool_results)),
        manager_rounds=tuple(_json_safe(manager_rounds)),
        guard_outcome=dict(guard_outcome or {}),
        repair_round_used=repair_round_used,
        request_failure_family="final_payload_shape_error",
        llm_used=True,
        trace={
            "decision_source": "single_manager_loop",
            "manager_rounds": _json_safe(manager_rounds),
            "tool_results": _json_safe(tool_results),
            "guard_outcome": _json_safe(guard_outcome or {}),
            "repair_round_used": repair_round_used,
            "request_failure_family": "final_payload_shape_error",
            "payload_shape_error": {
                "field_name": field_error.field_name,
                "observed_type": field_error.observed_type,
                "value_excerpt": field_error.value_excerpt,
                "value_truncated": field_error.value_truncated,
            },
        },
    )


async def run_intake_manager(
    *,
    provider: Any,
    raw_user_input: str,
    resolved_state: Any,
    available_tools: tuple[str, ...] | list[str],
    tool_executor: ToolExecutor | None = None,
    guard_checker: GuardChecker | None = None,
    onboarding_payload: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    max_rounds: int = 3,
) -> IntakeManagerResult:
    if not _provider_ready(provider):
        return _fallback_result(
            raw_user_input=raw_user_input,
            onboarding_payload=onboarding_payload,
            resolved_state=resolved_state,
        )

    manager_rounds: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    repair_round_used = False
    guard_feedback: dict[str, Any] | None = None

    for round_index in range(max_rounds):
        user_payload = {
            "raw_user_input": raw_user_input,
            "resolved_state": _json_safe(resolved_state),
            "available_tools": list(available_tools),
            "tool_results": _json_safe(tool_results),
            "round_index": round_index,
            "constraints": dict(constraints or {}),
            "guard_feedback": guard_feedback,
        }
        payload, trace = await provider.complete_with_trace(
            system_prompt=SINGLE_MANAGER_SYSTEM_PROMPT,
            user_payload=user_payload,
            stage=MANAGER_LOOP_STAGE,
            max_tokens=900,
        )
        parsed = payload if isinstance(payload, dict) else {}
        manager_rounds.append(
            {
                "round_index": round_index,
                "stage": MANAGER_LOOP_STAGE,
                "decision": _json_safe(parsed),
                "trace": _json_safe(trace),
            }
        )
        manager_action = str(parsed.get("manager_action") or "").strip()
        if manager_action == "call_tools":
            calls = _tool_call_dicts(parsed.get("tool_calls") or [])
            if not calls:
                return _result_from_payload(
                    {"manager_action": "final", "final_action": "no_commit", "workflow_effect": "safe_failure"},
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    failure_family="tool_routing_gap",
                )
            if tool_executor is None:
                tool_results.append(
                    {
                        "failure_family": "tool_executor_missing",
                        "evidence": {},
                        "mutation_result": {},
                        "provenance": {},
                        "confidence": "none",
                    }
                )
                continue
            executed = await _maybe_await(
                tool_executor(
                    tool_calls=[dict(item) for item in calls],
                    raw_user_input=raw_user_input,
                    resolved_state=resolved_state,
                    tool_results=_json_safe(tool_results),
                )
            )
            if isinstance(executed, list):
                tool_results.extend(dict(item) for item in executed if isinstance(item, dict))
            else:
                tool_results.append({"failure_family": "tool_executor_contract_gap", "evidence": {}, "raw_result": _json_safe(executed)})
            continue

        if manager_action == "final":
            guard_outcome = {}
            if guard_checker is not None:
                guard_outcome = await _maybe_await(
                    guard_checker(
                        manager_payload=dict(parsed),
                        tool_results=_json_safe(tool_results),
                        resolved_state=resolved_state,
                    )
                )
                if not isinstance(guard_outcome, dict):
                    guard_outcome = {"ok": False, "failure_family": "guard_contract_gap"}
                if guard_outcome.get("ok") is False:
                    if guard_outcome.get("repair_request") and not repair_round_used and round_index + 1 < max_rounds:
                        repair_round_used = True
                        guard_feedback = dict(guard_outcome)
                        continue
                    return _result_from_payload(
                        {**parsed, "manager_action": "final", "final_action": "no_commit"},
                        manager_rounds=manager_rounds,
                        tool_results=tool_results,
                        guard_outcome=guard_outcome,
                        repair_round_used=repair_round_used,
                        failure_family=str(guard_outcome.get("failure_family") or "guard_blocked"),
                    )
            try:
                return _result_from_payload(
                    parsed,
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    guard_outcome=guard_outcome,
                    repair_round_used=repair_round_used,
                )
            except _ManagerFinalPayloadShapeError as exc:
                return _payload_shape_failure_result(
                    parsed,
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    guard_outcome=guard_outcome,
                    repair_round_used=repair_round_used,
                    field_error=exc,
                )

        return _result_from_payload(
            {"manager_action": "final", "final_action": "no_commit", "workflow_effect": "safe_failure"},
            manager_rounds=manager_rounds,
            tool_results=tool_results,
            failure_family="malformed_manager_action",
        )

    return _result_from_payload(
        {"manager_action": "final", "final_action": "no_commit", "workflow_effect": "safe_failure"},
        manager_rounds=manager_rounds,
        tool_results=tool_results,
        failure_family="max_rounds_exceeded",
    )


SINGLE_MANAGER_SYSTEM_PROMPT = (
    "You are the single manager agent for the intake runtime.\n"
    "Use a bounded ReAct loop. Return strict JSON.\n"
    "If more evidence is needed, return manager_action='call_tools' with tool_calls.\n"
    "If ready, return manager_action='final' with intent, target_attachment, final_action, workflow_effect, "
    "answer_contract, exactness, confidence, evidence_posture, repair_ack, uncertainty_posture, and "
    "evidence_honesty_posture.\n"
    "Tools only provide evidence or mutation results. Do not assume hidden state.\n"
    "Do not emit freeform internal rationale fields.\n"
)
