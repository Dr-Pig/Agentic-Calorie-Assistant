from __future__ import annotations


def failure_routes_for_blockers(blockers: list[str]) -> list[dict[str, str]]:
    routes: list[dict[str, str]] = []
    seen: set[tuple[str, str, str]] = set()
    for blocker in blockers:
        route = failure_route_for_blocker(str(blocker))
        key = (route["blocker"], route["repair_layer"], route["failure_family"])
        if key in seen:
            continue
        seen.add(key)
        routes.append(route)
    return routes


def failure_route_for_blocker(blocker: str) -> dict[str, str]:
    if blocker.startswith("trace_layers."):
        layer_id = blocker.removeprefix("trace_layers.").removesuffix("_missing")
        return _route(
            blocker,
            repair_layer=_repair_layer_for_trace_layer(layer_id),
            failure_family="missing_required_trace_layer",
        )
    if blocker.startswith("fixture_decisions.") or blocker.startswith("generalization."):
        return _route(blocker, repair_layer="eval_harness_fake_pass_guard", failure_family="fake_pass_guard")
    if blocker.startswith("ui."):
        return _route(blocker, repair_layer="L9_ui_same_truth", failure_family="ui_same_truth_mismatch")
    if blocker.startswith("dogfood_trace."):
        return _route(blocker, repair_layer="L9_ui_same_truth", failure_family="dogfood_trace_linkage")
    if blocker.startswith("response."):
        return _route(blocker, repair_layer="L8_response", failure_family="response_quality_or_honesty")
    if blocker.startswith("latency."):
        return _route(blocker, repair_layer="observability_latency_budget", failure_family="latency_or_call_budget")
    if blocker.startswith("runtime.target_attachment"):
        return _route(blocker, repair_layer="L3_manager_semantics", failure_family="target_attachment_mismatch")
    if blocker.startswith("runtime.workflow_effect") or blocker.startswith("runtime.final_action"):
        return _route(blocker, repair_layer="L3_manager_semantics", failure_family="workflow_effect_mismatch")
    if blocker.startswith("runtime.fallback_400") or blocker.startswith("runtime.pre_manager_estimability"):
        return _route(blocker, repair_layer="L5_evidence_packets", failure_family="evidence_truth_violation")
    if blocker.startswith("runtime.mutation") or blocker.startswith("runtime.canonical_commit"):
        return _route(blocker, repair_layer="L7_mutation_read_model", failure_family="mutation_read_model_mismatch")
    if blocker.startswith("runtime."):
        return _route(blocker, repair_layer="L6_validator_guard", failure_family="runtime_contract_mismatch")
    return _route(blocker, repair_layer="unclassified", failure_family="unclassified_golden_blocker")


def _repair_layer_for_trace_layer(layer_id: str) -> str:
    if layer_id == "provider_profile_and_prompt_versions":
        return "L1_prompt_architecture"
    if layer_id == "current_turn_context_packet":
        return "L2_context_packet"
    if layer_id == "manager_pass_1_decision":
        return "L3_manager_semantics"
    if layer_id in {"requested_tools", "filtered_tool_plan", "executed_tools"}:
        return "L4_tool_selection"
    if layer_id in {"compact_packets", "guard_result"}:
        return "L6_validator_guard"
    if layer_id in {"mutation_result", "renderer_input_basis"}:
        return "L7_mutation_read_model"
    if layer_id in {"manager_pass_2_synthesis", "final_response_basis"}:
        return "L8_response"
    if layer_id in {"ui_event_trace", "feedback_linkage"}:
        return "L9_ui_same_truth"
    if layer_id == "latency_cost_cache_usage":
        return "observability_latency_budget"
    return "unclassified"


def _route(blocker: str, *, repair_layer: str, failure_family: str) -> dict[str, str]:
    return {
        "blocker": blocker,
        "repair_layer": repair_layer,
        "failure_family": failure_family,
    }


__all__ = ["failure_route_for_blocker", "failure_routes_for_blockers"]
