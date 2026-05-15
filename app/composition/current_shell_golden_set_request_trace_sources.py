from __future__ import annotations

from typing import Any


def trace_id(request_trace: dict[str, Any]) -> str | None:
    trace_meta = _dict(request_trace.get("trace_meta"))
    trace_refs = _dict(request_trace.get("trace_refs"))
    request = _dict(request_trace.get("request"))
    return (
        str(request_trace.get("request_id") or "")
        or str(trace_meta.get("request_id") or "")
        or str(trace_refs.get("request_id") or "")
        or str(request.get("request_id") or "")
        or None
    )


def manager_final_decision(request_trace: dict[str, Any]) -> dict[str, Any]:
    final_decision = _dict(request_trace.get("manager_final_decision"))
    if final_decision:
        return final_decision
    manager_decision = _dict(request_trace.get("manager_decision"))
    if manager_decision:
        return manager_decision
    execution_manager = _dict(request_trace.get("intake_execution_manager"))
    return _dict(execution_manager.get("final"))


def react_trace(request_trace: dict[str, Any]) -> dict[str, Any]:
    trace = _dict(request_trace.get("react_trace"))
    if trace:
        return trace
    final_decision = _dict(request_trace.get("manager_final_decision"))
    trace = _dict(_dict(final_decision.get("trace")).get("react_trace"))
    if trace:
        return trace
    manager_decision = _dict(request_trace.get("manager_decision"))
    trace = _dict(_dict(manager_decision.get("trace")).get("react_trace"))
    if trace:
        return trace
    execution_manager = _dict(request_trace.get("intake_execution_manager"))
    execution_final = _dict(execution_manager.get("final"))
    return _dict(_dict(execution_final.get("trace")).get("react_trace"))


def manager_provider(
    request_trace: dict[str, Any],
    trace: dict[str, Any],
    manager_final: dict[str, Any],
) -> dict[str, Any]:
    explicit = _dict(request_trace.get("manager_provider"))
    if explicit:
        return explicit
    first_observed_provider: dict[str, Any] = {}
    for pass_key in ("manager_pass_1", "manager_pass_final"):
        provider_trace = _dict(_dict(trace.get(pass_key)).get("provider_trace"))
        provider = provider_trace.get("provider") or provider_trace.get("provider_profile_id")
        live_llm_invoked = provider_trace.get("live_llm_invoked")
        if live_llm_invoked is None and (
            str(provider or "").strip() in {"builderspace"}
            or provider_trace.get("request_payload") is not None
            or provider_trace.get("response_payload") is not None
        ):
            live_llm_invoked = True
        observed = {
            "provider": provider,
            "semantic_owner": provider_trace.get("semantic_owner") or ("manager_llm" if live_llm_invoked is True else None),
            "semantic_source": provider_trace.get("semantic_source"),
            "live_llm_invoked": live_llm_invoked,
        }
        if provider_trace and not first_observed_provider:
            first_observed_provider = observed
        if provider or provider_trace.get("live_llm_invoked") is True:
            return observed
    if first_observed_provider:
        return first_observed_provider
    decision_trace = _dict(manager_final.get("trace"))
    if str(decision_trace.get("decision_source") or "").strip():
        return {
            "provider": decision_trace.get("decision_source"),
            "semantic_source": decision_trace.get("decision_source"),
            "live_llm_invoked": bool(manager_final.get("llm_used")),
        }
    return {}


def prompt_registry(trace: dict[str, Any], manager_final: dict[str, Any]) -> dict[str, Any]:
    registry = _dict(_dict(trace.get("manager_pass_1")).get("prompt_registry"))
    if registry:
        return registry
    return _dict(_dict(manager_final.get("trace")).get("prompt_registry"))


def provider_profile(trace: dict[str, Any], manager_final: dict[str, Any]) -> dict[str, Any]:
    provider_trace = _dict(_dict(trace.get("manager_pass_1")).get("provider_trace"))
    profile = _dict(provider_trace.get("provider_profile"))
    if profile:
        return profile
    if provider_trace.get("provider_profile_id"):
        return {"provider_profile_id": provider_trace.get("provider_profile_id")}
    decision_trace = _dict(manager_final.get("trace"))
    profile = _dict(decision_trace.get("provider_profile"))
    if profile:
        return profile
    profile_id = decision_trace.get("provider_profile_id")
    return {"provider_profile_id": profile_id} if profile_id else {}


def current_turn_context_packet(
    phase_a_trace: dict[str, Any],
    request_trace: dict[str, Any],
    trace: dict[str, Any],
) -> dict[str, Any]:
    for value in (
        request_trace.get("current_turn_context_packet"),
        request_trace.get("manager_context_packet_v1"),
        phase_a_trace.get("manager_context_packet_v1"),
        phase_a_trace.get("current_turn_context"),
    ):
        payload = _dict(value)
        if payload:
            return payload
    phase_a_input = _dict(_dict(trace.get("manager_pass_1")).get("phase_a_input"))
    return _dict(phase_a_input.get("manager_context_packet_v1"))


def requested_tools(
    request_trace: dict[str, Any],
    trace: dict[str, Any],
    manager_decision: dict[str, Any],
) -> list[Any]:
    if isinstance(trace.get("requested_tools"), list):
        return _list(trace.get("requested_tools"))
    if isinstance(manager_decision.get("tool_calls"), list):
        return _list(manager_decision.get("tool_calls"))
    return _list(request_trace.get("tool_plan"))


def filtered_tool_plan(request_trace: dict[str, Any]) -> dict[str, Any]:
    explicit = _dict(request_trace.get("filtered_tool_plan"))
    if explicit:
        return explicit
    plan = _list(request_trace.get("tool_plan"))
    return {"allowed_tools": plan} if plan else {}


def executed_tools(request_trace: dict[str, Any], trace: dict[str, Any]) -> list[Any]:
    if isinstance(trace.get("executed_tools"), list):
        return _list(trace.get("executed_tools"))
    tool_outputs = _dict(request_trace.get("tool_outputs"))
    executed: list[Any] = []
    for result in _list(tool_outputs.get("tool_results")):
        name = _dict(result).get("tool_name") or _dict(result).get("name")
        if name:
            executed.append(name)
    return executed


def compact_packets(request_trace: dict[str, Any]) -> list[Any]:
    explicit = _list(request_trace.get("compact_packets"))
    if explicit:
        return explicit
    return _list(_dict(request_trace.get("tool_outputs")).get("tool_results"))


def guard_result(trace: dict[str, Any], manager_final: dict[str, Any]) -> dict[str, Any]:
    guard = _dict(trace.get("guard_result"))
    if guard:
        return guard
    return _dict(_dict(manager_final.get("trace")).get("guard_outcome"))


def mutation_result(phase_c_trace: dict[str, Any], state_delta: dict[str, Any]) -> dict[str, Any]:
    mutation = _dict(phase_c_trace.get("mutation_outcome"))
    if mutation:
        return mutation
    return {"state_delta": state_delta} if state_delta else {}


def renderer_input_basis(request_trace: dict[str, Any]) -> dict[str, Any]:
    explicit = _dict(request_trace.get("renderer_input_basis"))
    if explicit:
        return explicit
    basis: dict[str, Any] = {}
    for key in ("state_after", "sidecar_output", "remaining_budget", "phase_c_trace"):
        value = _dict(request_trace.get(key))
        if value:
            basis[key] = value
    return basis


def final_response_basis(
    *,
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    renderer_output: dict[str, Any],
) -> dict[str, Any]:
    basis: dict[str, Any] = {}
    answer_contract = _dict(manager_final.get("answer_contract")) or _dict(manager_decision.get("answer_contract"))
    semantic_decision = _dict(manager_final.get("semantic_decision")) or _dict(manager_decision.get("semantic_decision"))
    if answer_contract:
        basis["answer_contract"] = answer_contract
    if semantic_decision:
        basis["semantic_decision"] = semantic_decision
    if renderer_output:
        basis["renderer_output"] = renderer_output
    return basis


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
