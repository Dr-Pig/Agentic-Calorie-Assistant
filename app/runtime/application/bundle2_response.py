from __future__ import annotations

from dataclasses import asdict
from typing import Any

from ...budget.application.current_budget_answer import build_remaining_budget_answer_contract
from ...intake.application.boundary_output_honesty import enforce_intake_output_honesty
from ...intake.application.phase_a_boundary_projection import attach_boundary_projection, build_intake_boundary_projection
from ...intake.application.phase_c_mutation_projection import build_phase_c_trace
from ...intake.application.phase_c_same_truth_gate import build_phase_c_same_truth_gate
from ...intake.application.shadow_hypothesis_dialogue import apply_shadow_hypothesis_dialogue_cue
from ...intake.application import manager_tools as tools
from ...runtime.application.reply_renderer import render_bundle1_reply
from ...runtime.application.request_trace_artifacts import build_trace_refs, write_bundle2_request_trace_artifact
from ...runtime.application.sidecar_service import build_deterministic_sidecar
from .bundle2_tool_batch import evidence_summary, macro_summary


def finalized_budget_summary(*, budget_summary: dict[str, Any] | None, state_before: Any, state_after: Any) -> dict[str, Any]:
    current_before = getattr(state_before, "current_budget_view", None)
    current_after = getattr(state_after, "current_budget_view", None)
    return {
        "budget_kcal": int(getattr(current_after, "budget_kcal", 0) or 0),
        "consumed_kcal_before": int(getattr(current_before, "consumed_kcal", 0) or 0),
        "predicted_consumed_kcal_after": int(getattr(current_after, "consumed_kcal", 0) or 0),
        "predicted_remaining_kcal_after": int(getattr(current_after, "remaining_kcal", 0) or 0),
        "overshoot_detected": int(getattr(current_after, "remaining_kcal", 0) or 0) < 0,
        "overshoot_kcal": abs(min(int(getattr(current_after, "remaining_kcal", 0) or 0), 0)),
        "replaced_kcal_before": int((budget_summary or {}).get("replaced_kcal_before") or 0),
    }


def build_latency_tracking(*, manager_decision: Any, stage_timings: list[dict[str, Any]]) -> dict[str, Any]:
    total_duration = sum(int(stage.get("duration_ms", 0) or 0) for stage in stage_timings)
    slowest = max(stage_timings, key=lambda item: int(item.get("duration_ms", 0) or 0)) if stage_timings else {"stage": "none", "duration_ms": 0}
    return {
        "intent_type": manager_decision.intent_type,
        "tools_used": [(tc.get("tool_name") or tc.get("name", "unknown")) if isinstance(tc, dict) else str(tc) for tc in manager_decision.tool_calls],
        "total_duration_ms": total_duration,
        "slowest_step_ms": int(slowest.get("duration_ms", 0) or 0),
        "slowest_step_name": str(slowest.get("stage") or "none"),
        "stage_timings": stage_timings,
    }


def build_bundle2_response(
    db: Any,
    *,
    request_id: str,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    allow_search: bool,
    state_before: Any,
    state_after: Any,
    manager_decision: Any,
    manager_result: Any,
    nutrition_artifact: Any | None,
    persistence_result: Any | None,
    budget_summary: dict[str, Any] | None,
    tool_outputs: dict[str, Any],
    state_mutation_summary: dict[str, Any],
    stage_timings: list[dict[str, Any]],
    phase_a_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    remaining_budget_contract = build_remaining_budget_answer_contract(db, user_id=state_after.user_id, local_date=local_date)
    payload = getattr(nutrition_artifact, "payload", None) if nutrition_artifact is not None else None
    if payload is not None:
        phase_a_trace = attach_boundary_projection(
            phase_a_trace,
            build_intake_boundary_projection(
                payload=payload,
                persistence_result=persistence_result,
                active_body_plan_present=bool(getattr(state_before, "onboarding_ready", False)),
            ),
        )
    assistant_message = render_bundle1_reply(
        intent_type=manager_decision.intent_type,
        onboarding_result=None,
        remaining_budget=remaining_budget_contract,
        active_body_plan_view=state_after.active_body_plan_view,
        nutrition_payload=payload,
        persistence_result=persistence_result,
        manager_final_action=manager_result.final_action if manager_result is not None else None,
        budget_summary=budget_summary,
    )
    trace_summary = {
        "request_id": request_id,
        "manager_intent": manager_decision.intent_type,
        "tool_calls": list(manager_decision.tool_calls),
        "llm_used": manager_decision.llm_used,
    }
    overshoot_summary = {
        "budget_kcal": int((budget_summary or {}).get("budget_kcal", 0) or 0),
        "consumed_kcal_before": int((budget_summary or {}).get("consumed_kcal_before", 0) or 0),
        "predicted_consumed_kcal_after": int((budget_summary or {}).get("predicted_consumed_kcal_after", 0) or 0),
        "predicted_remaining_kcal_after": int((budget_summary or {}).get("predicted_remaining_kcal_after", 0) or 0),
        "overshoot_detected": bool((budget_summary or {}).get("overshoot_detected")),
        "overshoot_kcal": int((budget_summary or {}).get("overshoot_kcal", 0) or 0),
    }
    sidecar = build_deterministic_sidecar(
        active_body_plan_view=state_after.active_body_plan_view,
        current_budget_view=state_after.current_budget_view,
        state_mutation_summary=state_mutation_summary,
        trace_summary=trace_summary,
        overshoot_summary=overshoot_summary,
        macro_summary=macro_summary(payload),
        evidence_summary=evidence_summary(raw_user_input=raw_user_input, payload=payload),
    )
    output_honesty = enforce_intake_output_honesty(
        assistant_message=assistant_message,
        state_delta=state_mutation_summary,
        sidecar=sidecar,
        phase_a_trace=phase_a_trace,
        manager_final_action=manager_result.final_action if manager_result is not None else None,
        persistence_result=persistence_result,
    )
    assistant_message = output_honesty.assistant_message
    state_mutation_summary = output_honesty.state_delta
    sidecar = output_honesty.sidecar
    phase_a_trace = output_honesty.phase_a_trace
    shadow_dialogue = apply_shadow_hypothesis_dialogue_cue(
        assistant_message=assistant_message,
        phase_a_trace=phase_a_trace,
    )
    assistant_message = shadow_dialogue.assistant_message
    phase_a_trace = shadow_dialogue.phase_a_trace
    phase_c_trace = build_phase_c_trace(
        persistence_result=persistence_result,
        state_delta=state_mutation_summary,
        sidecar=sidecar,
        phase_a_trace=phase_a_trace,
        budget_summary=budget_summary,
    )
    same_truth_gate = build_phase_c_same_truth_gate(
        phase_c_trace=phase_c_trace,
        persistence_result=persistence_result,
        state_delta=state_mutation_summary,
        sidecar=sidecar,
        state_after=state_after,
        budget_summary=budget_summary,
    )
    phase_c_trace = dict(phase_c_trace)
    phase_c_trace["same_truth_closure_gate"] = same_truth_gate
    hard_fail_conditions = []
    if same_truth_gate.get("status") == "hard_fail" and same_truth_gate.get("failure_family"):
        hard_fail_conditions.append(str(same_truth_gate["failure_family"]))
    tools.append_trace_event_tool(
        request_id=request_id,
        stage="v2_renderer_sidecar",
        status="ok",
        summary={"assistant_message": assistant_message, "state_delta": state_mutation_summary},
    )
    latency_tracking = build_latency_tracking(manager_decision=manager_decision, stage_timings=stage_timings)
    write_bundle2_request_trace_artifact(
        request_id=request_id,
        user_external_id=user_external_id,
        local_date=local_date,
        raw_user_input=raw_user_input,
        allow_search=allow_search,
        state_before=state_before,
        manager_round_1={"manager_rounds": [dict(item) for item in manager_result.manager_rounds]},
        injected_context_summary=state_before.injected_context,
        tool_plan=list(manager_result.tool_calls),
        tool_outputs=tool_outputs,
        manager_final_decision=manager_result,
        state_after=state_after,
        assistant_message=assistant_message,
        sidecar=sidecar,
        state_delta=state_mutation_summary,
        phase_a_trace=phase_a_trace,
        phase_c_trace=phase_c_trace,
        latency_tracking=latency_tracking,
    )
    return {
        "request_id": request_id,
        "assistant_message": assistant_message,
        "manager_decision": {
            "intent_type": manager_decision.intent_type,
            "workflow_effect": manager_decision.workflow_effect,
            "response_summary": manager_decision.response_summary,
            "pending_followup": manager_decision.pending_followup,
            "tool_calls": list(manager_decision.tool_calls),
            "llm_used": manager_decision.llm_used,
            "trace": manager_decision.trace,
        },
        "bundle2_manager": {
            "manager_rounds": [dict(item) for item in manager_result.manager_rounds],
            "final": {"final_action": manager_result.final_action, "workflow_effect": manager_result.workflow_effect},
            "persistence_result": persistence_result,
        },
        "remaining_budget": asdict(remaining_budget_contract) if remaining_budget_contract else {},
        "state_after": state_after,
        "state_delta": state_mutation_summary,
        "sidecar": sidecar,
        "phase_c_trace": phase_c_trace,
        "audit": build_trace_refs(request_id=request_id),
        "hard_fail_conditions": hard_fail_conditions,
        "shadow_mode": True,
        "latency_tracking": latency_tracking,
    }
