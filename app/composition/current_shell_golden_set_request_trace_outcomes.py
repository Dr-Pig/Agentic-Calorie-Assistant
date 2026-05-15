from __future__ import annotations

from typing import Any

from app.composition.current_shell_golden_set_nutrition_projection import (
    approved_nutrition_evidence_present as _approved_nutrition_evidence_present,
    component_basis_present,
    first_nutrition_trace_contract,
    generic_range_evidence_present,
    macro_visible,
    nutrition_packet_present,
    visible_range_or_basis_present,
)
from app.composition.current_shell_golden_set_request_trace_sources import trace_id
from app.composition.current_shell_golden_set_version_projection import (
    ledger_delta_trace_present,
    old_version_not_counted,
    old_version_superseded,
)


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
        if "pending_followup_saved" not in runtime and phase_c_mutation.get("draft_status") == "saved":
            runtime["pending_followup_saved"] = True
    superseded = old_version_superseded(phase_c_mutation, state_delta)
    if "old_version_superseded" not in runtime and superseded is not None:
        runtime["old_version_superseded"] = superseded
    if "ledger_delta_trace_required" not in runtime and superseded is True:
        runtime["ledger_delta_trace_required"] = ledger_delta_trace_present(phase_c_mutation, state_delta)
    if "pending_followup_saved" not in runtime and "draft_saved" in state_delta:
        runtime["pending_followup_saved"] = bool(state_delta.get("draft_saved"))
    if "assumed_slot_question_required" not in runtime and _followup_question(manager_final):
        runtime["assumed_slot_question_required"] = True
    component_basis = component_basis_present(request_trace)
    if "component_basis_required" not in runtime and component_basis is not None:
        runtime["component_basis_required"] = component_basis
    if "component_estimate_required" not in runtime and component_basis is not None:
        runtime["component_estimate_required"] = component_basis
    nutrition_trace = first_nutrition_trace_contract(request_trace, manager_final)
    if nutrition_trace:
        for field in ("source_basis", "macro_visibility_status", "optional_refinement_allowed"):
            if (
                field == "macro_visibility_status"
                and runtime.get(field) == "hidden"
                and nutrition_trace.get(field) is not None
            ):
                runtime[field] = nutrition_trace.get(field)
            elif field not in runtime and nutrition_trace.get(field) is not None:
                runtime[field] = nutrition_trace.get(field)
        if generic_range_evidence_present(nutrition_trace):
            runtime.setdefault("uncertainty_basis_required", True)
            runtime.setdefault("fake_exactness_allowed", False)
    if "fallback_400_allowed" not in runtime and nutrition_packet_present(request_trace, manager_final):
        runtime["fallback_400_allowed"] = False
    if "pre_manager_estimability_shortcut_allowed" not in runtime:
        pre_manager_shortcut = _pre_manager_guard_feedback_present(request_trace)
        if pre_manager_shortcut is not None:
            runtime["pre_manager_estimability_shortcut_allowed"] = pre_manager_shortcut
    _attach_blocking_composition_clarification_outcome(
        runtime=runtime,
        manager_final=manager_final,
        manager_decision=manager_decision,
        workflow_effect=workflow_effect,
        final_action=final_action,
    )
    _attach_implausible_kcal_conflict_outcome(
        runtime=runtime,
        manager_final=manager_final,
        manager_decision=manager_decision,
        workflow_effect=workflow_effect,
        final_action=final_action,
        mutation_allowed=mutation_allowed,
    )
    return runtime


def ui_from_request_trace(request_trace: dict[str, Any], state_delta: dict[str, Any]) -> dict[str, Any]:
    ui = _dict(request_trace.get("ui"))
    if "today_consumed_updates" not in ui and "ledger_updated" in state_delta:
        ui["today_consumed_updates"] = bool(state_delta.get("ledger_updated"))
    if "frontend_nutrition_math_allowed" not in ui:
        ui["frontend_nutrition_math_allowed"] = False
    if "pending_question_visible" not in ui and "draft_saved" in state_delta:
        ui["pending_question_visible"] = bool(state_delta.get("draft_saved"))
    if "meal_level_basis_visible" not in ui:
        basis_visible = _meal_level_basis_visible(request_trace)
        if basis_visible is not None:
            ui["meal_level_basis_visible"] = basis_visible
    if "meal_components_visible" not in ui:
        components_visible = _meal_level_basis_visible(request_trace)
        if components_visible is not None:
            ui["meal_components_visible"] = components_visible
    if "macro_visible" not in ui:
        visible_macro = macro_visible(request_trace)
        if visible_macro is not None:
            ui["macro_visible"] = visible_macro
    if "range_or_basis_visible" not in ui and generic_range_evidence_present(
        first_nutrition_trace_contract(request_trace, {})
    ):
        ui["range_or_basis_visible"] = visible_range_or_basis_present(request_trace)
    if "old_version_not_counted" not in ui:
        not_counted = old_version_not_counted(request_trace, state_delta)
        if not_counted is not None:
            ui["old_version_not_counted"] = not_counted
    return ui


def response_from_request_trace(request_trace: dict[str, Any]) -> dict[str, Any]:
    explicit = _dict(request_trace.get("response"))
    if explicit:
        return _with_visible_response_text(explicit, request_trace)
    response_grade = _dict(request_trace.get("response_grade"))
    if response_grade:
        return _with_visible_response_text(response_grade, request_trace)
    sidecar_response = _dict(_dict(request_trace.get("sidecar_output")).get("response"))
    return _with_visible_response_text(sidecar_response, request_trace)


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
    elif resolved_trace_id:
        trace.setdefault("feedback_links_to_trace", True)
    return trace


def approved_nutrition_evidence_present(request_trace: dict[str, Any], manager_final: dict[str, Any]) -> bool:
    return _approved_nutrition_evidence_present(request_trace, manager_final)


def _attach_blocking_composition_clarification_outcome(
    *,
    runtime: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    workflow_effect: Any,
    final_action: Any,
) -> None:
    if str(final_action or workflow_effect or "") != "ask_followup":
        return
    semantic_decision = _dict(manager_final.get("semantic_decision")) or _dict(
        manager_decision.get("semantic_decision")
    )
    if str(semantic_decision.get("mutation_intent_candidate") or "") != "no_mutation":
        return
    estimation_posture = str(semantic_decision.get("estimation_posture") or "")
    followup_posture = str(semantic_decision.get("followup_posture") or "")
    if "composition_unknown" not in estimation_posture and "blocking_composition" not in followup_posture:
        return
    if not _followup_question(manager_final):
        return
    runtime.setdefault("estimate_allowed", False)
    runtime.setdefault("one_bundled_question_required", True)


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


def _attach_implausible_kcal_conflict_outcome(
    *,
    runtime: dict[str, Any],
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
    workflow_effect: Any,
    final_action: Any,
    mutation_allowed: bool | None,
) -> None:
    if not _manager_named_food_kcal_conflict(manager_final, manager_decision):
        return
    if mutation_allowed is not False:
        return
    if str(final_action or workflow_effect or "") != "ask_followup":
        return
    runtime.setdefault("silent_accept_implausible_kcal_allowed", False)
    runtime.setdefault("override_with_system_estimate_allowed", False)


def _manager_named_food_kcal_conflict(
    manager_final: dict[str, Any],
    manager_decision: dict[str, Any],
) -> bool:
    semantic_decision = _dict(manager_final.get("semantic_decision")) or _dict(
        manager_decision.get("semantic_decision")
    )
    source = str(semantic_decision.get("source") or manager_final.get("source") or "")
    return source == "named_food_user_kcal_conflict"


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


def _followup_question(manager_final: dict[str, Any]) -> str:
    answer_contract = _dict(manager_final.get("answer_contract"))
    semantic_decision = _dict(manager_final.get("semantic_decision"))
    return str(answer_contract.get("followup_question") or semantic_decision.get("followup_question") or "").strip()


def _meal_level_basis_visible(request_trace: dict[str, Any]) -> bool | None:
    basis = _dict(request_trace.get("renderer_input_basis"))
    state_after = _dict(basis.get("state_after")) or _dict(request_trace.get("state_after"))
    active_meal = _dict(state_after.get("active_meal"))
    candidates = _list(active_meal.get("item_candidates"))
    if candidates:
        return True
    return None

def _with_visible_response_text(response: dict[str, Any], request_trace: dict[str, Any]) -> dict[str, Any]:
    visible_text = _visible_response_text(request_trace)
    if visible_text:
        response.setdefault("assistant_message", visible_text)
    return response

def _visible_response_text(request_trace: dict[str, Any]) -> str:
    renderer_output = _dict(request_trace.get("renderer_output"))
    text = str(renderer_output.get("assistant_message") or renderer_output.get("message") or "").strip()
    if text:
        return text
    manager_final = _dict(request_trace.get("manager_final_decision"))
    answer_contract = _dict(manager_final.get("answer_contract"))
    return str(
        answer_contract.get("reply_text")
        or answer_contract.get("text")
        or manager_final.get("response_summary")
        or ""
    ).strip()

def _pre_manager_guard_feedback_present(request_trace: dict[str, Any]) -> bool | None:
    react_trace = _dict(request_trace.get("react_trace"))
    manager_pass_1 = _dict(react_trace.get("manager_pass_1"))
    if not manager_pass_1:
        return None
    return bool(manager_pass_1.get("guard_feedback_input"))

def _dict(value: Any) -> dict[str, Any]:
    return dict(value) if isinstance(value, dict) else {}

def _list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, list) else []
