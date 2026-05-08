from __future__ import annotations

from typing import Any, Awaitable, Callable

from app.runtime.agent.manager_provider_readiness import provider_ready
from app.runtime.agent.manager_context_payload import (
    manager_context_pack_payload as serialize_manager_context_pack,
    manager_context_packet_v1_trace_payload,
    manager_context_trace_payload,
    shadow_hypothesis_instruction,
)
from app.runtime.agent.manager_result_builder import (
    IntakeManagerResult,
    ManagerFinalPayloadShapeError,
    fallback_result,
    payload_shape_failure_result,
    result_from_payload,
)
from app.runtime.agent.manager_prompt_registry import build_manager_prompt_registry
from app.runtime.agent.manager_system_prompt import SINGLE_MANAGER_SYSTEM_PROMPT, single_manager_system_prompt_for_scope  # noqa: F401
from app.runtime.contracts.trace import MANAGER_LOOP_STAGE
from app.runtime.agent.manager_payload_utils import (
    compact_resolved_state_prompt_payload,
    json_safe,
    maybe_await,
    stable_available_tools,
    tool_call_dicts,
)
from app.runtime.agent.manager_prompted_provider import complete_manager_round_with_prompt_trace
from app.runtime.agent.manager_tool_scope import manager_scope_policy_payload, safe_failure_payload, tool_call_scope_boundary
from app.runtime.contracts.phase_a import CurrentTurnContextV1, HistoryExpansionPolicy, ManagerContextPack


ToolExecutor = Callable[..., Awaitable[list[dict[str, Any]]] | list[dict[str, Any]]]
GuardChecker = Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]
ManagerContextRefresher = Callable[..., Awaitable[dict[str, Any]] | dict[str, Any]]
def _with_phase_a_repair_trace(
    guard_outcome: dict[str, Any],
    *,
    repair_attempted: bool,
    repair_result: str,
) -> dict[str, Any]:
    updated = dict(guard_outcome)
    preflight = updated.get("phase_a_transition_guard_preflight")
    if isinstance(preflight, dict):
        updated["phase_a_transition_guard_preflight"] = {
            **preflight,
            "repair_attempted": repair_attempted,
            "repair_result": repair_result,
        }
    return updated


async def run_intake_manager(
    *,
    provider: Any,
    raw_user_input: str,
    resolved_state: Any,
    available_tools: tuple[str, ...] | list[str],
    current_turn_context: CurrentTurnContextV1 | None = None,
    manager_context_pack: ManagerContextPack | None = None,
    manager_context_packet_v1: dict[str, Any] | None = None,
    history_expansion_policy: HistoryExpansionPolicy | None = None,
    phase_a_shadow_hypothesis: dict[str, Any] | None = None,
    phase_a_history_expansion_enabled: bool = False,
    tool_executor: ToolExecutor | None = None,
    manager_context_refresher: ManagerContextRefresher | None = None,
    guard_checker: GuardChecker | None = None,
    onboarding_payload: dict[str, Any] | None = None,
    constraints: dict[str, Any] | None = None,
    manager_loop_scope: str | None = None,
    max_rounds: int = 3,
) -> IntakeManagerResult:
    prompt_registry = build_manager_prompt_registry(provider=provider, constraints=constraints)
    normalized_available_tools = stable_available_tools(available_tools)
    if not provider_ready(provider):
        return fallback_result(
            raw_user_input=raw_user_input,
            onboarding_payload=onboarding_payload,
            resolved_state=resolved_state,
            prompt_registry=prompt_registry,
        )

    manager_rounds: list[dict[str, Any]] = []
    tool_results: list[dict[str, Any]] = []
    repair_round_used = False
    guard_feedback: dict[str, Any] | None = None
    effective_history_expansion_policy = history_expansion_policy or HistoryExpansionPolicy()
    effective_manager_loop_scope = str(manager_loop_scope or _default_manager_loop_scope(normalized_available_tools))

    for round_index in range(max_rounds):
        effective_constraints = dict(constraints or {})
        effective_constraints.update(manager_loop_scope=effective_manager_loop_scope, available_tools=list(normalized_available_tools))
        if isinstance(guard_feedback, dict):
            effective_constraints["guard_feedback_failure_family"] = str(guard_feedback.get("failure_family") or "")
            effective_constraints["guard_feedback_repair_request"] = bool(guard_feedback.get("repair_request"))
        phase_a_surface_mode = (
            current_turn_context.current_interaction_event.surface_mode
            if current_turn_context is not None
            else None
        )
        manager_context_pack_payload = serialize_manager_context_pack(manager_context_pack)
        manager_context_trace = manager_context_trace_payload(
            current_turn_context=current_turn_context,
            manager_context_pack=manager_context_pack,
            manager_context_pack_payload=manager_context_pack_payload,
            history_expansion_policy=effective_history_expansion_policy,
            phase_a_history_expansion_enabled=phase_a_history_expansion_enabled,
            phase_a_shadow_hypothesis=phase_a_shadow_hypothesis,
        )
        manager_context_trace["manager_context_packet_v1"] = manager_context_packet_v1_trace_payload(manager_context_packet_v1)
        manager_context_trace["manager_loop_scope"] = effective_manager_loop_scope
        user_payload = {
            "raw_user_input": raw_user_input,
            "resolved_state": compact_resolved_state_prompt_payload(resolved_state),
            "resolved_state_role": "compatibility_legacy",
            "phase_a_current_turn_context": (
                current_turn_context.model_dump(mode="json")
                if current_turn_context is not None
                else None
            ),
            "phase_a_manager_context_pack": json_safe(manager_context_pack_payload),
            "manager_context_packet_v1": json_safe(manager_context_packet_v1),
            "phase_a_manager_context_pack_role": manager_context_trace["phase_a_manager_context_pack_role"],
            "phase_a_surface_mode": phase_a_surface_mode,
            "phase_a_context_pack_version": "v1" if manager_context_pack_payload is not None else None,
            "phase_a_history_expansion_policy": effective_history_expansion_policy.model_dump(mode="json"),
            "phase_a_history_expansion_enabled": phase_a_history_expansion_enabled,
            "phase_a_shadow_hypothesis": json_safe(phase_a_shadow_hypothesis),
            "phase_a_shadow_hypothesis_role": manager_context_trace["phase_a_shadow_hypothesis_role"],
            "phase_a_shadow_hypothesis_instruction": shadow_hypothesis_instruction(phase_a_shadow_hypothesis),
            "available_tools": list(normalized_available_tools),
            "tool_results": json_safe(tool_results),
            "round_index": round_index,
            "manager_loop_scope": effective_manager_loop_scope,
            "manager_scope_policy": manager_scope_policy_payload(effective_manager_loop_scope, normalized_available_tools),
            "constraints": effective_constraints,
            "manager_product_policy_hints": json_safe(effective_constraints.get("manager_product_policy_hints")),
            "guard_feedback": guard_feedback,
        }
        payload, trace, prompt_layer_contract = await complete_manager_round_with_prompt_trace(
            provider=provider,
            manager_loop_scope=effective_manager_loop_scope,
            user_payload=user_payload,
            stage=MANAGER_LOOP_STAGE,
            max_tokens=900,
        )
        parsed = payload if isinstance(payload, dict) else {}
        manager_rounds.append(
            {
                "round_index": round_index,
                "stage": MANAGER_LOOP_STAGE,
                "manager_loop_scope": effective_manager_loop_scope,
                "decision": json_safe(parsed),
                "trace": json_safe(trace),
                "phase_a_input": json_safe(manager_context_trace),
                "prompt_registry": json_safe(prompt_registry),
                "prompt_layer_contract": json_safe(prompt_layer_contract),
            }
        )
        manager_action = str(parsed.get("manager_action") or "").strip()
        if manager_action == "call_tools":
            calls = tool_call_dicts(parsed.get("tool_calls") or [])
            if not calls:
                return result_from_payload(
                    safe_failure_payload(),
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    prompt_registry=prompt_registry,
                    failure_family="tool_routing_gap",
                )
            boundary = tool_call_scope_boundary(
                payload=parsed,
                calls=calls,
                available_tools=normalized_available_tools,
                manager_loop_scope=effective_manager_loop_scope,
            )
            if boundary is not None:
                tool_results.append(dict(boundary["tool_result"]))
                return result_from_payload(
                    dict(boundary["payload"]),
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    prompt_registry=prompt_registry,
                    failure_family=boundary.get("failure_family"),
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
            if manager_context_refresher is not None:
                refresh = await maybe_await(
                    manager_context_refresher(
                        raw_user_input=raw_user_input,
                        resolved_state=resolved_state,
                        current_turn_context=current_turn_context,
                        manager_context_pack=manager_context_pack,
                        tool_calls=[dict(item) for item in calls],
                        tool_results=json_safe(tool_results),
                        phase_a_history_expansion_enabled=phase_a_history_expansion_enabled,
                    )
                )
                if isinstance(refresh, dict):
                    refreshed_context = refresh.get("current_turn_context")
                    if isinstance(refreshed_context, CurrentTurnContextV1):
                        current_turn_context = refreshed_context
                    refreshed_pack = refresh.get("manager_context_pack")
                    if isinstance(refreshed_pack, ManagerContextPack):
                        manager_context_pack = refreshed_pack
                    refreshed_packet = refresh.get("manager_context_packet_v1")
                    if isinstance(refreshed_packet, dict):
                        manager_context_packet_v1 = refreshed_packet
                    if "phase_a_history_expansion_enabled" in refresh:
                        phase_a_history_expansion_enabled = bool(refresh["phase_a_history_expansion_enabled"])
            guard_feedback = None
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
                        guard_feedback = _with_phase_a_repair_trace(
                            dict(guard_outcome),
                            repair_attempted=False,
                            repair_result="requested",
                        )
                        continue
                    guard_outcome = _with_phase_a_repair_trace(
                        dict(guard_outcome),
                        repair_attempted=repair_round_used,
                        repair_result="failed" if repair_round_used else "not_attempted",
                    )
                    return result_from_payload(
                        {**parsed, "manager_action": "final", "final_action": "no_commit"},
                        manager_rounds=manager_rounds,
                        tool_results=tool_results,
                        prompt_registry=prompt_registry,
                        guard_outcome=guard_outcome,
                        repair_round_used=repair_round_used,
                        failure_family=str(guard_outcome.get("failure_family") or "guard_blocked"),
                    )
                guard_outcome = _with_phase_a_repair_trace(
                    dict(guard_outcome),
                    repair_attempted=repair_round_used,
                    repair_result="passed_after_repair" if repair_round_used else "not_needed",
                )
            try:
                return result_from_payload(
                    parsed,
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    prompt_registry=prompt_registry,
                    guard_outcome=guard_outcome,
                    repair_round_used=repair_round_used,
                )
            except ManagerFinalPayloadShapeError as exc:
                return payload_shape_failure_result(
                    parsed,
                    manager_rounds=manager_rounds,
                    tool_results=tool_results,
                    prompt_registry=prompt_registry,
                    guard_outcome=guard_outcome,
                    repair_round_used=repair_round_used,
                    field_error=exc,
                )

        return result_from_payload(
            safe_failure_payload(),
            manager_rounds=manager_rounds,
            tool_results=tool_results,
            prompt_registry=prompt_registry,
            failure_family="malformed_manager_action",
        )

    return result_from_payload(
        safe_failure_payload(),
        manager_rounds=manager_rounds,
        tool_results=tool_results,
        prompt_registry=prompt_registry,
        failure_family="max_rounds_exceeded",
    )


def _default_manager_loop_scope(available_tools: tuple[str, ...]) -> str:
    tool_names = set(available_tools)
    if "body.record_observation" in tool_names:
        return "body_observation"
    if tool_names.intersection({"estimate_nutrition", "resolve_correction_target", "compare_against_budget"}):
        return "intake_execution"
    return "turn_entry_or_read_only"
