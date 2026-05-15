from __future__ import annotations

from typing import Any

from app.composition.current_shell_target_ambiguity_projection import attach_target_ambiguity_validation
from app.composition.current_shell_remaining_query_projection import (
    attach_remaining_query_runtime,
    attach_remaining_query_ui,
)

from app.composition.current_shell_golden_set_answer_query_projection import (
    attach_answer_query_no_mutation_outcome,
    state_delta_has_no_meal_change,
)
from app.composition.current_shell_body_observation_projection import (
    attach_body_observation_runtime_projection,
    attach_body_observation_ui_projection,
    body_observation_recorded,
)
from app.composition.current_shell_golden_set_kcal_conflict_projection import (
    attach_implausible_kcal_conflict_outcome,
)
from app.composition.current_shell_golden_set_latency_projection import manager_provider_round_count
from app.composition.current_shell_golden_set_meal_basis_projection import meal_level_basis_visible
from app.composition.current_shell_golden_set_correction_projection import (
    attach_removed_version_projection,
)
from app.composition.current_shell_golden_set_nutrition_projection import (
    approved_nutrition_evidence_present as _approved_nutrition_evidence_present,
    component_basis_present,
    first_nutrition_trace_contract,
    generic_range_evidence_present,
    macro_visible,
    nutrition_packet_present,
    visible_range_or_basis_present,
)
from app.composition.current_shell_golden_set_version_projection import (
    ledger_delta_trace_present,
    old_version_not_counted,
    old_version_superseded,
)
from app.composition.current_shell_golden_set_websearch_projection import (
    attach_websearch_runtime_projection,
    attach_websearch_ui_projection,
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
    if "runtime_mutation_allowed" not in runtime and mutation_allowed is not None:
        runtime["runtime_mutation_allowed"] = mutation_allowed
    final_action = manager_final.get("final_action") or manager_decision.get("final_action")
    if final_action is not None:
        runtime.setdefault("final_action", final_action)
    _attach_manager_semantics(runtime, manager_final, manager_decision)
    attach_body_observation_runtime_projection(
        runtime,
        request_trace=request_trace,
        state_delta=state_delta,
    )
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
    attach_removed_version_projection(
        runtime,
        request_trace=request_trace,
        state_delta=state_delta,
        manager_final=manager_final,
        manager_decision=manager_decision,
        phase_c_mutation=phase_c_mutation,
    )
    if "ledger_recomputed" not in runtime and "ledger_updated" in state_delta:
        runtime["ledger_recomputed"] = bool(state_delta.get("ledger_updated"))
    if "ledger_delta_trace_required" not in runtime and superseded is True:
        runtime["ledger_delta_trace_required"] = ledger_delta_trace_present(phase_c_mutation, state_delta)
    if "pending_followup_saved" not in runtime and "draft_saved" in state_delta:
        runtime["pending_followup_saved"] = bool(state_delta.get("draft_saved"))
    attach_answer_query_no_mutation_outcome(
        runtime=runtime,
        manager_final=manager_final,
        manager_decision=manager_decision,
        state_delta=state_delta,
    )
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
            runtime.setdefault("use_generic_or_fooddb_anchor_first", True)
            runtime.setdefault("fooddb_anchor_bypass_allowed", False)
        if _manager_owned_optional_drink_refinement(manager_final, nutrition_trace):
            runtime.setdefault("optional_tea_refinement_allowed", True)
        attach_websearch_runtime_projection(runtime, nutrition_trace)
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
    attach_implausible_kcal_conflict_outcome(
        runtime=runtime,
        manager_final=manager_final,
        manager_decision=manager_decision,
        workflow_effect=workflow_effect,
        final_action=final_action,
        mutation_allowed=mutation_allowed,
    )
    attach_target_ambiguity_validation(runtime, request_trace, manager_final)
    attach_remaining_query_runtime(
        runtime,
        request_trace=request_trace,
        manager_final=manager_final,
        manager_decision=manager_decision,
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
        basis_visible = meal_level_basis_visible(request_trace)
        if basis_visible is not None:
            ui["meal_level_basis_visible"] = basis_visible
    if "meal_components_visible" not in ui:
        components_visible = meal_level_basis_visible(request_trace)
        if components_visible is not None:
            ui["meal_components_visible"] = components_visible
    if "macro_visible" not in ui:
        visible_macro = macro_visible(request_trace)
        if visible_macro is not None:
            ui["macro_visible"] = visible_macro
    if "range_or_basis_visible" not in ui and generic_range_evidence_present(
        first_nutrition_trace_contract(request_trace, _dict(request_trace.get("manager_final_decision")))
    ):
        ui["range_or_basis_visible"] = visible_range_or_basis_present(request_trace)
    attach_websearch_ui_projection(ui, request_trace)
    if "old_version_not_counted" not in ui:
        not_counted = old_version_not_counted(request_trace, state_delta)
        if not_counted is not None:
            ui["old_version_not_counted"] = not_counted
            ui.setdefault("removed_item_not_counted", not_counted)
    if "existing_meal_unchanged" not in ui and state_delta_has_no_meal_change(state_delta):
        ui["existing_meal_unchanged"] = True
    attach_body_observation_ui_projection(ui, request_trace=request_trace, state_delta=state_delta)
    attach_remaining_query_ui(ui, request_trace=request_trace)
    return ui


def latency_from_request_trace(request_trace: dict[str, Any], react_trace: dict[str, Any]) -> dict[str, Any]:
    latency_tracking = _dict(request_trace.get("latency_tracking"))
    latency = _dict(request_trace.get("latency"))
    latency.setdefault("timeout_is_product_target", False)
    if "total_latency_ms" not in latency and latency_tracking.get("total_duration_ms") is not None:
        latency["total_latency_ms"] = latency_tracking.get("total_duration_ms")
    if "tool_calls" not in latency and react_trace.get("tool_call_count") is not None:
        latency["tool_calls"] = react_trace.get("tool_call_count")
    if "llm_calls" not in latency:
        provider_round_count = manager_provider_round_count(react_trace)
        if provider_round_count is not None:
            latency["llm_calls"] = provider_round_count
        elif react_trace.get("manager_pass_count") is not None:
            latency["llm_calls"] = react_trace.get("manager_pass_count")
    if "stage_timings" not in latency and latency_tracking.get("stage_timings") is not None:
        latency["stage_timings"] = latency_tracking.get("stage_timings")
    if "latency_attribution" not in latency and latency_tracking.get("latency_attribution") is not None:
        latency["latency_attribution"] = latency_tracking.get("latency_attribution")
    return latency


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


def _mutation_allowed_from_trace(
    phase_c_trace: dict[str, Any],
    state_delta: dict[str, Any],
) -> bool | None:
    if body_observation_recorded({}, state_delta):
        return True
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


def _manager_owned_optional_drink_refinement(
    manager_final: dict[str, Any],
    nutrition_trace: dict[str, Any],
) -> bool:
    if nutrition_trace.get("optional_refinement_allowed") is not True:
        return False
    if not _followup_question(manager_final):
        return False
    semantic_decision = _dict(manager_final.get("semantic_decision"))
    if str(semantic_decision.get("followup_posture") or "") != "refinement_optional":
        return False
    targets = [str(item) for item in nutrition_trace.get("optional_refinement_targets") or []]
    return any("茶" in item for item in targets)


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
