from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_request_trace_sources import trace_id


def runtime_from_request_trace(
    *,
    request_trace: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    phase_c_trace: dict[str, Any],
    state_delta: dict[str, Any],
) -> dict[str, Any]:
    runtime = _dict(request_trace.get("runtime"))
    workflow_effect = (
        manager_final.get("workflow_effect")
        or manager_decision.get("workflow_effect")
        or _dict(request_trace.get("general_chat_result")).get("workflow_effect")
    )
    if workflow_effect is not None:
        runtime.setdefault("workflow_effect", workflow_effect)
    mutation_allowed = _mutation_allowed_from_trace(phase_c_trace, state_delta)
    if "mutation_allowed" not in runtime and mutation_allowed is not None:
        runtime["mutation_allowed"] = mutation_allowed
    final_action = manager_final.get("final_action") or manager_decision.get("final_action")
    if final_action is not None:
        runtime.setdefault("final_action", final_action)
    _attach_manager_semantics(runtime, manager_final, manager_decision)
    phase_c_mutation = _dict(phase_c_trace.get("mutation_outcome"))
    if phase_c_mutation:
        runtime.setdefault("canonical_commit_status", phase_c_mutation.get("canonical_commit_status"))
        runtime.setdefault("ledger_mutation_status", phase_c_mutation.get("ledger_mutation_status"))
        runtime.setdefault("meal_version_delta", phase_c_mutation.get("meal_version_delta"))
        runtime.setdefault("macro_visibility_status", phase_c_mutation.get("macro_visibility_status"))
    return runtime


def ui_from_request_trace(request_trace: dict[str, Any], state_delta: dict[str, Any]) -> dict[str, Any]:
    ui = _dict(request_trace.get("ui"))
    if "today_consumed_updates" not in ui and "ledger_updated" in state_delta:
        ui["today_consumed_updates"] = bool(state_delta.get("ledger_updated"))
    if "frontend_nutrition_math_allowed" not in ui:
        ui["frontend_nutrition_math_allowed"] = False
    if "pending_question_visible" not in ui and "draft_saved" in state_delta:
        ui["pending_question_visible"] = bool(state_delta.get("draft_saved"))
    return ui


def response_from_request_trace(request_trace: dict[str, Any]) -> dict[str, Any]:
    explicit = _dict(request_trace.get("response"))
    if explicit:
        return explicit
    response_grade = _dict(request_trace.get("response_grade"))
    if response_grade:
        return response_grade
    return _dict(_dict(request_trace.get("sidecar_output")).get("response"))


def latency_from_request_trace(request_trace: dict[str, Any], react_trace: dict[str, Any]) -> dict[str, Any]:
    latency_tracking = _dict(request_trace.get("latency_tracking"))
    latency = _dict(request_trace.get("latency"))
    latency.setdefault("timeout_is_product_target", False)
    if "total_latency_ms" not in latency and latency_tracking.get("total_duration_ms") is not None:
        latency["total_latency_ms"] = latency_tracking.get("total_duration_ms")
    if "tool_calls" not in latency and react_trace.get("tool_call_count") is not None:
        latency["tool_calls"] = react_trace.get("tool_call_count")
    if "llm_calls" not in latency and react_trace.get("manager_pass_count") is not None:
        latency["llm_calls"] = react_trace.get("manager_pass_count")
    if "stage_timings" not in latency and latency_tracking.get("stage_timings") is not None:
        latency["stage_timings"] = latency_tracking.get("stage_timings")
    if "latency_attribution" not in latency and latency_tracking.get("latency_attribution") is not None:
        latency["latency_attribution"] = latency_tracking.get("latency_attribution")
    return latency


def dogfood_trace_from_request_trace(request_trace: dict[str, Any]) -> dict[str, Any]:
    trace = _dict(request_trace.get("dogfood_trace"))
    trace_refs = _dict(request_trace.get("trace_refs"))
    resolved_trace_id = trace_id(request_trace)
    if resolved_trace_id:
        trace.setdefault("trace_id", resolved_trace_id)
    if trace_refs.get("request_id"):
        trace.setdefault("request_id", trace_refs.get("request_id"))
    feedback = _dict(request_trace.get("feedback_linkage"))
    if feedback:
        trace.setdefault("feedback_linkage", feedback)
        if feedback.get("feedback_links_to_trace") is not None:
            trace.setdefault("feedback_links_to_trace", bool(feedback.get("feedback_links_to_trace")))
    return trace


def _attach_manager_semantics(
    runtime: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
) -> None:
    target_attachment = _dict(manager_final.get("target_attachment")) or _dict(manager_decision.get("target_attachment"))
    if target_attachment:
        runtime.setdefault("target_attachment", target_attachment)
    semantic_decision = _dict(manager_final.get("semantic_decision")) or _dict(manager_decision.get("semantic_decision"))
    if not semantic_decision:
        return
    if semantic_decision.get("target_attachment") is not None:
        runtime.setdefault("target_attachment", semantic_decision.get("target_attachment"))
    if semantic_decision.get("current_turn_intent") is not None:
        runtime.setdefault("current_turn_intent", semantic_decision.get("current_turn_intent"))


def _mutation_allowed_from_trace(
    phase_c_trace: dict[str, Any],
    state_delta: dict[str, Any],
) -> bool | None:
    if "canonical_commit" in state_delta:
        return bool(state_delta.get("canonical_commit"))
    commit_status = str(_dict(phase_c_trace.get("mutation_outcome")).get("canonical_commit_status") or "")
    if commit_status == "committed":
        return True
    if commit_status in {"not_committed", "not_available"}:
        return False
    return None


def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}
