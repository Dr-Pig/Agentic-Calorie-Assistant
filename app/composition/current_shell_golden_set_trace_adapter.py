from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_grader import (
    grade_golden_case_result,
    load_golden_set_manifest,
)


def build_golden_case_result_from_trace(
    case_id: str,
    trace_artifact: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Map explicit runtime trace fields into the Golden Set grader input.

    This adapter intentionally does not infer semantic outcomes from raw text.
    Workflow effect, mutation, target attachment, response meaning, and UI truth
    must be supplied by runtime/trace artifacts that the Manager and product
    services emitted.
    """

    golden_manifest = manifest or load_golden_set_manifest()
    return {
        "case_id": case_id,
        "fixture_decisions": _fixture_decisions(golden_manifest, trace_artifact),
        "trace_layers": _trace_layers(trace_artifact),
        "runtime": _copy_mapping(trace_artifact.get("runtime")),
        "ui": _copy_mapping(trace_artifact.get("ui")),
        "response": _copy_mapping(trace_artifact.get("response")),
        "latency": _latency(trace_artifact),
        "dogfood_trace": _dogfood_trace(trace_artifact),
        "generalization": _copy_mapping(trace_artifact.get("generalization")),
    }


def grade_golden_case_trace(
    case_id: str,
    trace_artifact: dict[str, Any],
    *,
    manifest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return grade_golden_case_result(
        build_golden_case_result_from_trace(case_id, trace_artifact, manifest=manifest),
        manifest=manifest,
    )


def _fixture_decisions(
    manifest: dict[str, Any],
    trace_artifact: dict[str, Any],
) -> dict[str, bool]:
    fixture_decisions = trace_artifact.get("fixture_decisions")
    if isinstance(fixture_decisions, dict):
        return {str(key): bool(value) for key, value in fixture_decisions.items()}

    fixture_policy = dict(manifest.get("fixture_policy") or {})
    return {
        "intent": bool(fixture_policy.get("fixtures_may_decide_intent")),
        "action": bool(fixture_policy.get("fixtures_may_decide_action")),
        "attach_target": bool(fixture_policy.get("fixtures_may_decide_attach_target")),
        "mutation_outcome": bool(fixture_policy.get("fixtures_may_decide_mutation_outcome")),
        "response_meaning": bool(fixture_policy.get("fixtures_may_decide_response_meaning")),
    }


def _trace_layers(trace_artifact: dict[str, Any]) -> dict[str, dict[str, bool]]:
    layers: dict[str, dict[str, bool]] = {}
    explicit_layers = trace_artifact.get("trace_layers")
    if isinstance(explicit_layers, dict):
        for layer_id, layer_value in explicit_layers.items():
            if isinstance(layer_value, dict):
                layers[str(layer_id)] = {"present": bool(layer_value.get("present"))}
            else:
                layers[str(layer_id)] = {"present": bool(layer_value)}

    present_layers = trace_artifact.get("trace_layers_present")
    if isinstance(present_layers, list):
        for layer_id in present_layers:
            layers[str(layer_id)] = {"present": True}

    react_trace = _copy_mapping(trace_artifact.get("react_trace"))
    structural_sources = {
        "provider_profile_and_prompt_versions": (
            trace_artifact.get("prompt_registry"),
            trace_artifact.get("provider_profile"),
            trace_artifact.get("provider_profile_and_prompt_versions"),
        ),
        "current_turn_context_packet": (
            trace_artifact.get("current_turn_context_packet"),
            trace_artifact.get("context_packet"),
        ),
        "manager_pass_1_decision": (
            react_trace.get("manager_pass_1"),
            trace_artifact.get("manager_pass_1_decision"),
        ),
        "requested_tools": (
            react_trace.get("requested_tools") if "requested_tools" in react_trace else None,
            trace_artifact.get("requested_tools"),
        ),
        "filtered_tool_plan": (trace_artifact.get("filtered_tool_plan"),),
        "executed_tools": (
            react_trace.get("executed_tools") if "executed_tools" in react_trace else None,
            trace_artifact.get("executed_tools"),
        ),
        "compact_packets": (
            trace_artifact.get("compact_packets"),
            trace_artifact.get("tool_packets"),
        ),
        "manager_pass_2_synthesis": (
            react_trace.get("manager_pass_final"),
            trace_artifact.get("manager_pass_2_synthesis"),
        ),
        "guard_result": (
            react_trace.get("guard_result"),
            trace_artifact.get("guard_result"),
        ),
        "mutation_result": (trace_artifact.get("mutation_result"),),
        "renderer_input_basis": (trace_artifact.get("renderer_input_basis"),),
        "final_response_basis": (trace_artifact.get("final_response_basis"),),
        "latency_cost_cache_usage": (
            trace_artifact.get("latency"),
            react_trace.get("total_latency_ms"),
            trace_artifact.get("token_usage"),
            trace_artifact.get("cache_usage"),
        ),
        "ui_event_trace": (
            trace_artifact.get("ui_event_trace"),
            trace_artifact.get("ui_events"),
        ),
        "feedback_linkage": (
            trace_artifact.get("feedback_linkage"),
            trace_artifact.get("feedback_id"),
            _copy_mapping(trace_artifact.get("dogfood_trace")).get("feedback_links_to_trace"),
        ),
    }

    for layer_id, values in structural_sources.items():
        if _any_present(values):
            layers[layer_id] = {"present": True}

    return layers


def _latency(trace_artifact: dict[str, Any]) -> dict[str, Any]:
    latency = _copy_mapping(trace_artifact.get("latency"))
    react_trace = _copy_mapping(trace_artifact.get("react_trace"))

    latency.setdefault("timeout_is_product_target", False)
    if "tool_calls" not in latency and "tool_call_count" in react_trace:
        latency["tool_calls"] = react_trace.get("tool_call_count")
    if "total_latency_ms" not in latency and "total_latency_ms" in react_trace:
        latency["total_latency_ms"] = react_trace.get("total_latency_ms")
    return latency


def _dogfood_trace(trace_artifact: dict[str, Any]) -> dict[str, Any]:
    dogfood_trace = _copy_mapping(trace_artifact.get("dogfood_trace"))
    if "trace_id" not in dogfood_trace:
        trace_id = trace_artifact.get("trace_id") or trace_artifact.get("request_id")
        if trace_id:
            dogfood_trace["trace_id"] = trace_id
    return dogfood_trace


def _copy_mapping(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}


def _any_present(values: tuple[Any, ...]) -> bool:
    for value in values:
        if value is False or value is None:
            continue
        return True
    return False


__all__ = [
    "build_golden_case_result_from_trace",
    "grade_golden_case_trace",
]
