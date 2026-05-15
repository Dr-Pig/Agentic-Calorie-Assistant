from __future__ import annotations

import re
from typing import Any

from app.composition.current_shell_golden_set_request_trace_outcomes import (
    approved_nutrition_evidence_present,
    dogfood_trace_from_request_trace,
    latency_from_request_trace,
    response_from_request_trace,
    runtime_from_request_trace,
    ui_from_request_trace,
)
from app.composition.current_shell_golden_set_request_trace_sources import (
    compact_packets,
    current_turn_context_packet,
    executed_tools,
    filtered_tool_plan,
    final_response_basis,
    guard_result,
    manager_final_decision,
    manager_provider,
    mutation_result,
    prompt_registry,
    provider_profile,
    react_trace,
    requested_tools,
    renderer_input_basis,
    trace_id,
)


def build_golden_case_trace_from_request_trace(
    case_id: str,
    request_trace: dict[str, Any],
    *,
    case_assertions: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Project a real request trace into the Golden Set trace input shape.

    The adapter never infers intent, target attachment, mutation legality, or
    response meaning from raw user text. Missing structured runtime evidence is
    intentionally left missing so the Golden Set replay blocks the case.
    """

    assertions = _dict(case_assertions)
    runtime_assertions = _dict(assertions.get("runtime"))
    ui_assertions = _dict(assertions.get("ui"))
    response_assertions = _dict(assertions.get("response"))
    dogfood_assertions = _dict(assertions.get("dogfood_trace"))
    generalization_assertions = _dict(assertions.get("generalization"))

    manager_final = manager_final_decision(request_trace)
    manager_decision = _dict(request_trace.get("manager_decision"))
    trace = react_trace(request_trace)
    phase_a_trace = _dict(request_trace.get("phase_a_trace"))
    phase_c_trace = _dict(request_trace.get("phase_c_trace"))
    state_delta = _dict(request_trace.get("state_delta"))
    renderer_output = _dict(request_trace.get("renderer_output"))

    runtime = {
        **runtime_from_request_trace(
            request_trace=request_trace,
            manager_final=manager_final,
            manager_decision=manager_decision,
            phase_c_trace=phase_c_trace,
            state_delta=state_delta,
        ),
        **runtime_assertions,
    }
    response = {**response_from_request_trace(request_trace), **response_assertions}
    if (
        runtime.get("fallback_400_allowed") is False
        and _contains_visible_kcal_claim(renderer_output)
        and not approved_nutrition_evidence_present(request_trace, manager_final)
    ):
        response["invented_nutrition_fact"] = True
    _attach_visible_response_quality_flags(
        response=response,
        runtime=runtime,
        state_delta=state_delta,
    )

    return {
        "case_id": case_id,
        "trace_id": trace_id(request_trace),
        "manager_provider": manager_provider(request_trace, trace, manager_final),
        "prompt_registry": prompt_registry(trace, manager_final),
        "provider_profile": provider_profile(trace, manager_final),
        "current_turn_context_packet": current_turn_context_packet(
            phase_a_trace, request_trace, trace
        ),
        "react_trace": trace,
        "requested_tools": requested_tools(request_trace, trace, manager_decision),
        "filtered_tool_plan": filtered_tool_plan(request_trace),
        "executed_tools": executed_tools(request_trace, trace),
        "compact_packets": compact_packets(request_trace),
        "guard_result": guard_result(trace, manager_final),
        "mutation_result": mutation_result(phase_c_trace, state_delta),
        "renderer_input_basis": renderer_input_basis(request_trace),
        "final_response_basis": final_response_basis(
            manager_final=manager_final,
            manager_decision=manager_decision,
            renderer_output=renderer_output,
        ),
        "runtime": runtime,
        "ui": {**ui_from_request_trace(request_trace, state_delta), **ui_assertions},
        "response": response,
        "latency": latency_from_request_trace(request_trace, trace),
        "dogfood_trace": {
            **dogfood_trace_from_request_trace(request_trace),
            **dogfood_assertions,
        },
        "generalization": generalization_assertions,
    }


def build_golden_trace_artifact_from_request_traces(
    case_traces: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "artifact_type": "current_shell_self_use_golden_set_trace_artifact",
        "claim_scope": "real_request_trace_projection",
        "live_invoked_by_replay": False,
        "readiness_claimed": False,
        "product_readiness_claimed": False,
        "private_self_use_approved": False,
        "whole_product_mvp_claimed": False,
        "runner_inferred_semantics": False,
        "semantic_keyword_oracle_used": False,
        "cases": list(case_traces),
    }


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _contains_visible_kcal_claim(renderer_output: dict[str, Any]) -> bool:
    text = str(renderer_output.get("assistant_message") or renderer_output.get("coach_message") or "")
    return bool(re.search(r"\d+\s*(?:kcal|cal|卡|大卡)", text, flags=re.IGNORECASE))


def _attach_visible_response_quality_flags(
    *,
    response: dict[str, Any],
    runtime: dict[str, Any],
    state_delta: dict[str, Any],
) -> None:
    text = str(
        response.get("assistant_message")
        or response.get("visible_text")
        or response.get("reply_text")
        or ""
    )
    if not text:
        return
    lowered = text.lower()
    internal_phrase_present = any(
        phrase in lowered
        for phrase in (
            "not a saved change",
            "tentative reference",
            "meal thread",
            "provider",
            "trace",
        )
    )
    if internal_phrase_present:
        response["internal_debug_words_present"] = True
    committed = (
        state_delta.get("canonical_commit") is True
        or runtime.get("canonical_commit_status") == "committed"
        or runtime.get("mutation_allowed") is True
    )
    if committed and ("not a saved change" in lowered or "not saved" in lowered):
        response["state_contradiction"] = True
    if response.get("zh_tw_primary") is None and internal_phrase_present:
        response["zh_tw_primary"] = False


__all__ = [
    "build_golden_case_trace_from_request_trace",
    "build_golden_trace_artifact_from_request_traces",
]
