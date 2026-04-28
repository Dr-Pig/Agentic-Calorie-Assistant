from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.runtime.agent.manager_result_support import (
    IntakeManagerResult,
    ManagerFinalPayloadShapeError,
    SINGLE_MANAGER_SYSTEM_PROMPT,
    fallback_result,
    payload_shape_failure_result,
    provider_ready,
    result_from_payload,
)
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.runtime.agent.manager_payload_utils import (
    json_safe,
    maybe_await,
    tool_call_dicts,
)


ToolExecutor = Callable[..., Awaitable[list[dict[str, Any]]] | list[dict[str, Any]]]
GuardChecker = Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]

# Contract marker kept here so prompt-governance tests still verify the
# semantic fields required by the single-manager final payload.
SINGLE_MANAGER_PROMPT_CONTRACT_MARKER = (
    "intent, target_attachment; "
    "exactness, confidence, evidence_posture, repair_ack"
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
    if not provider_ready(provider):
        return fallback_result(
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
            "resolved_state": json_safe(resolved_state),
            "available_tools": list(available_tools),
            "tool_results": json_safe(tool_results),
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
                "decision": json_safe(parsed),
                "trace": json_safe(trace),
            }
        )
        manager_action = str(parsed.get("manager_action") or "").strip()
        if manager_action == "call_tools":
            calls = tool_call_dicts(parsed.get("tool_calls") or [])
            if not calls:
                return result_from_payload(
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
            executed = await maybe_await(
                tool_executor(
                    tool_calls=[dict(item) for item in calls],
                    raw_user_input=raw_user_input,
                    resolved_state=resolved_state,
                    tool_results=json_safe(tool_results),
                )
            )
            if isinstance(executed, list):
                tool_results.extend(dict(item) for item in executed if isinstance(item, dict))
            else:
                tool_results.append({"failure_family": "tool_executor_contract_gap", "evidence": {}, "raw_result": json_safe(executed)})
            continue

        if manager_action == "final":
            guard_outcome = {}
            if guard_checker is not None:
                guard_outcome = await maybe_await(
                    guard_checker(
                        manager_payload=dict(parsed),
                        tool_results=json_safe(tool_results),
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
                    return result_from_payload(
                        {**parsed, "manager_action": "final", "final_action": "no_commit"},
                        manager_rounds=manager_rounds,
                        tool_results=tool_results,
                        guard_outcome=guard_outcome,
                        repair_round_used=repair_round_used,
                        failure_family=str(guard_outcome.get("failure_family") or "guard_blocked"),
                    )
            try:
                return result_from_payload(
                    parsed,
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    guard_outcome=guard_outcome,
                    repair_round_used=repair_round_used,
                )
            except ManagerFinalPayloadShapeError as exc:
                return payload_shape_failure_result(
                    parsed,
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    guard_outcome=guard_outcome,
                    repair_round_used=repair_round_used,
                    field_error=exc,
                )

        return result_from_payload(
            {"manager_action": "final", "final_action": "no_commit", "workflow_effect": "safe_failure"},
            manager_rounds=manager_rounds,
            tool_results=tool_results,
            failure_family="malformed_manager_action",
        )

    return result_from_payload(
        {"manager_action": "final", "final_action": "no_commit", "workflow_effect": "safe_failure"},
        manager_rounds=manager_rounds,
        tool_results=tool_results,
        failure_family="max_rounds_exceeded",
    )
