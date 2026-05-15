"""Thin intake execution entrypoint.

Semantic ownership lives in the single-manager runtime, domain tools, execution
guard, persistence support, and deterministic sidecar builders.
"""

from __future__ import annotations

from dataclasses import replace
import time
from typing import Any

from sqlalchemy.orm import Session

from app.composition.intake_execution_response import build_intake_execution_response
from app.composition.intake_entry_handoff import execute_entry_handoff_seed
from app.composition.intake_commit_guard_repair import commit_boundary_guard_repair_outcome
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.composition.remove_item_target_evidence import (
    build_remove_item_target_evidence_artifact,
    remove_item_target_evidence_ready,
)
from app.composition.intake_manager_tool_batch import (
    apply_final_action_to_payload,
    attach_correction_target_ref_to_payload,
    execute_manager_tool_calls,
)
from app.composition.intake_execution_tool_outputs import build_refreshed_intake_tool_outputs
from app.composition.intake_manager_target_validation import validate_final_manager_target_attachment
from app.composition.manager_ask_followup_draft import build_manager_ask_followup_draft_artifact
from app.composition.state_resolver import resolve_intake_state
from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
from app.composition.user_provided_kcal_evidence import build_user_provided_kcal_evidence_seed
from app.intake.application.context_injection_policy import build_manager_context_pack
from app.intake.application.final_action_mutation_classifier import (
    PERSISTENCE_EFFECT_ACTIONS,
    classify_final_action_mutation,
)
from app.intake.application.history_expansion_manager_runtime import (
    PHASE_A_EXPAND_HISTORY_TOOL,
    activate_manager_triggered_history_expansion,
    manager_history_expansion_eligibility,
)
from app.composition.intake_execution_persistence import initial_state_mutation_summary, persist_intake_execution_artifact
from app.intake.application.intake_trace_tools import append_trace_event_tool, resolve_correction_target_tool
from app.intake.application.phase_a_runtime_context import prepare_phase_a_runtime_context
from app.nutrition.application.manager_policy_hints import nutrition_manager_policy_hints
from app.nutrition.application.owner_lineage_trace import attach_owner_lineage_trace
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.runtime.application.manager_service import run_intake_manager
from app.runtime.contracts.phase_a import CurrentTurnContextV1, HistoryExpansionPolicy, ManagerContextPack

_MANAGER_LOOP_GUARD_PERSISTENCE_ACTIONS = PERSISTENCE_EFFECT_ACTIONS - frozenset({"ask_followup"})

def _now_ms() -> int:
    return int(time.time() * 1000)

def _append_stage_timing(stage_timings: list[dict[str, Any]], stage: str, duration_ms: int) -> None:
    stage_timings.append({"stage": stage, "duration_ms": duration_ms})

def _manager_result_payload(manager_result: Any) -> dict[str, Any]:
    return {
        "final_action": str(getattr(manager_result, "final_action", "") or ""),
        "target_attachment": dict(getattr(manager_result, "target_attachment", {}) or {}),
        "answer_contract": dict(getattr(manager_result, "answer_contract", {}) or {}),
        "semantic_decision": dict(getattr(manager_result, "semantic_decision", {}) or {}),
    }

async def process_intake_execution_turn(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    allow_search: bool,
    manager_provider: Any | None = None,
    provider: Any | None = None,
    search_port: WebSearchPort | None = None,
    extract_port: WebExtractPort | None = None,
    state_before: Any,
    manager_decision: Any,
    request_id: str,
    stage_timings: list[dict[str, Any]],
    current_turn_context: CurrentTurnContextV1 | None = None,
    manager_context_pack: ManagerContextPack | None = None,
    manager_context_packet_v1: dict[str, Any] | None = None,
    phase_a_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    active_manager_provider = manager_provider or provider
    state_mutation_summary = initial_state_mutation_summary()
    correction_target = resolve_correction_target_tool(resolved_state=state_before)
    phase_a_runtime = prepare_phase_a_runtime_context(
        raw_user_input=raw_user_input,
        resolved_state=state_before,
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        phase_a_trace=phase_a_trace,
    )
    current_turn_context = phase_a_runtime.current_turn_context
    manager_context_pack = phase_a_runtime.manager_context_pack
    phase_a_trace = phase_a_runtime.phase_a_trace
    latest_attachment_decision = phase_a_runtime.attachment_decision
    latest_transition_guard_result = phase_a_runtime.transition_guard_result
    shadow_runtime = phase_a_runtime.shadow_runtime
    if manager_context_packet_v1 is None:
        manager_context_packet_v1 = build_runtime_manager_context_packet_v1(
            db=db,
            current_turn_context=current_turn_context,
            user_external_id=user_external_id,
            local_date=local_date,
            session_id=request_id, exclude_trace_id=request_id,
        )
    if current_turn_context is None or latest_attachment_decision is None or latest_transition_guard_result is None:
        raise ValueError("Phase A runtime context is required for intake execution.")
    manager_history_eligibility = manager_history_expansion_eligibility(
        current_turn_context=current_turn_context,
        attachment_decision=latest_attachment_decision,
        transition_guard_result=latest_transition_guard_result,
    )
    phase_a_history_expansion_enabled = manager_history_eligibility.eligible
    manager_triggered_history_attempted = False
    manager_triggered_history_trace: dict[str, Any] | None = None
    tool_state: dict[str, Any] = {
        "correction_target": correction_target,
        "nutrition_artifact": None,
        "budget_summary": None,
    }
    user_kcal_seed = build_user_provided_kcal_evidence_seed(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        state_before=state_before,
        correction_target=tool_state["correction_target"],
        manager_decision=manager_decision,
    )
    if user_kcal_seed.nutrition_artifact is not None:
        tool_state["nutrition_artifact"] = user_kcal_seed.nutrition_artifact
        tool_state["budget_summary"] = user_kcal_seed.budget_summary

    def record_timing(stage: str, duration_ms: int) -> None:
        _append_stage_timing(stage_timings, stage, duration_ms)

    async def tool_executor(**kwargs: Any) -> list[dict[str, Any]]:
        nonlocal current_turn_context
        nonlocal latest_attachment_decision
        nonlocal latest_transition_guard_result
        nonlocal manager_context_pack
        nonlocal manager_context_packet_v1
        nonlocal phase_a_history_expansion_enabled
        nonlocal manager_triggered_history_attempted
        nonlocal manager_triggered_history_trace
        stage_start = _now_ms()
        tool_calls = list(kwargs.get("tool_calls") or [])
        history_tool_call = next(
            (
                call
                for call in tool_calls
                if str(call.get("name") or call.get("tool_name") or "").strip() == PHASE_A_EXPAND_HISTORY_TOOL
            ),
            None,
        )
        if history_tool_call is not None:
            if manager_triggered_history_attempted:
                result = {
                    "tool_name": PHASE_A_EXPAND_HISTORY_TOOL,
                    "evidence": {},
                    "mutation_result": {},
                    "provenance": {"phase_a_owner": "intake/application", "primary_truth": "structured_candidates"},
                    "confidence": "none",
                    "failure_family": "phase_a_history_expansion_budget_exhausted",
                }
            else:
                manager_triggered_history_attempted = True
                expansion = activate_manager_triggered_history_expansion(
                    current_turn_context=current_turn_context,
                    resolved_state=state_before,
                    pre_attachment_decision=latest_attachment_decision,
                    pre_transition_guard_result=latest_transition_guard_result,
                    manager_tool_arguments=dict(history_tool_call.get("arguments") or {}),
                )
                current_turn_context = expansion.enriched_current_turn_context
                latest_attachment_decision = expansion.post_attachment_decision
                latest_transition_guard_result = expansion.post_transition_guard_result
                manager_context_pack = build_manager_context_pack(current_turn_context=current_turn_context)
                manager_context_packet_v1 = build_runtime_manager_context_packet_v1(
                    db=db,
                    current_turn_context=current_turn_context,
                    user_external_id=user_external_id,
                    local_date=local_date,
                    session_id=request_id, exclude_trace_id=request_id,
                )
                phase_a_history_expansion_enabled = False
                manager_triggered_history_trace = expansion.trace_payload()
                result = expansion.tool_result()
            record_timing("phase_a_history_expansion", _now_ms() - stage_start)
            append_trace_event_tool(
                request_id=request_id,
                stage="phase_a_expand_history",
                status="ok",
                summary={"tool_results": [result]},
            )
            return [result]
        results = await execute_manager_tool_calls(
            db=db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            request_id=request_id,
            local_date=local_date,
            allow_search=allow_search,
            manager_provider=active_manager_provider,
            provider=provider,
            search_port=search_port,
            extract_port=extract_port,
            state_before=state_before,
            correction_target=tool_state["correction_target"],
            tool_calls=tool_calls,
            tool_state=tool_state,
        )
        record_timing("tool_batch", _now_ms() - stage_start)
        append_trace_event_tool(
            request_id=request_id,
            stage="v2_tool_batch",
            status="ok",
            summary={"tool_results": results},
        )
        return results

    async def manager_context_refresher(**_: Any) -> dict[str, Any]:
        return {
            "current_turn_context": current_turn_context,
            "manager_context_pack": manager_context_pack,
            "manager_context_packet_v1": manager_context_packet_v1,
            "phase_a_history_expansion_enabled": phase_a_history_expansion_enabled,
        }

    async def guard_checker(**kwargs: Any) -> dict[str, Any]:
        manager_payload = dict(kwargs.get("manager_payload") or {})
        final_action = str(manager_payload.get("final_action") or "")
        transition_preflight = classify_final_action_mutation(
            manager_payload=manager_payload,
            transition_guard_result=latest_transition_guard_result,
            persistence_effect_actions=_MANAGER_LOOP_GUARD_PERSISTENCE_ACTIONS,
        )
        preflight_trace = transition_preflight.trace_payload()
        if transition_preflight.blocked:
            return {
                "ok": False,
                "repair_request": True,
                "failure_family": transition_preflight.failure_family,
                "phase_a_transition_guard_preflight": preflight_trace,
            }
        artifact = tool_state.get("nutrition_artifact")
        payload = getattr(artifact, "payload", None) if artifact is not None else None
        if final_action in {"commit", "correction_applied", "overshoot_note"} and payload is None:
            if remove_item_target_evidence_ready(
                manager_payload=manager_payload,
                correction_target=dict(tool_state.get("correction_target") or {}),
            ):
                return {"ok": True, "phase_a_transition_guard_preflight": preflight_trace}
            return {
                "ok": False,
                "repair_request": True,
                "failure_family": "commit_without_evidence",
                "phase_a_transition_guard_preflight": preflight_trace,
            }
        repair_outcome = commit_boundary_guard_repair_outcome(
            payload=payload,
            final_action=final_action,
            active_body_plan_present=bool(getattr(state_before, "onboarding_ready", False)),
            correction_target=tool_state["correction_target"],
            manager_semantic_decision=dict(manager_payload.get("semantic_decision") or {}),
            transition_preflight_trace=preflight_trace,
        )
        if repair_outcome is not None:
            return repair_outcome
        return {"ok": True, "phase_a_transition_guard_preflight": preflight_trace}

    entry_handoff_seed = await execute_entry_handoff_seed(
        manager_decision=manager_decision,
        tool_executor=tool_executor,
        raw_user_input=raw_user_input,
        resolved_state=state_before,
        now_ms=_now_ms,
        record_timing=record_timing,
    )

    stage_start = _now_ms()
    manager_result = await run_intake_manager(
        provider=active_manager_provider,
        raw_user_input=raw_user_input,
        resolved_state=state_before,
        available_tools=(
            "resolve_correction_target",
            "estimate_nutrition",
            "compare_against_budget",
            *([PHASE_A_EXPAND_HISTORY_TOOL] if phase_a_history_expansion_enabled else []),
        ),
        current_turn_context=current_turn_context,
        manager_context_pack=manager_context_pack,
        manager_context_packet_v1=manager_context_packet_v1,
        history_expansion_policy=HistoryExpansionPolicy(),
        phase_a_shadow_hypothesis=shadow_runtime.manager_payload if shadow_runtime is not None else None,
        phase_a_history_expansion_enabled=phase_a_history_expansion_enabled,
        tool_executor=tool_executor,
        manager_context_refresher=manager_context_refresher,
        guard_checker=guard_checker,
        initial_tool_results=[*user_kcal_seed.tool_results, *entry_handoff_seed["tool_results"]],
        initial_manager_rounds=entry_handoff_seed["manager_rounds"],
        constraints={
            "request_id": request_id,
            "manager_product_policy_hints": nutrition_manager_policy_hints(),
        },
        max_rounds=3,
    )
    record_timing("manager_loop", _now_ms() - stage_start)
    append_trace_event_tool(
        request_id=request_id,
        stage="v2_manager_loop",
        status="ok",
        summary={
            "manager_rounds": [dict(item) for item in manager_result.manager_rounds],
            "final_action": manager_result.final_action,
            "workflow_effect": manager_result.workflow_effect,
            "request_failure_family": manager_result.request_failure_family,
        },
    )
    tool_state["correction_target"] = validate_final_manager_target_attachment(
        correction_target=dict(tool_state.get("correction_target") or {}),
        manager_result=manager_result,
    )

    nutrition_artifact = tool_state.get("nutrition_artifact")
    budget_summary = tool_state.get("budget_summary")
    payload = getattr(nutrition_artifact, "payload", None) if nutrition_artifact is not None else None
    if payload is None and remove_item_target_evidence_ready(
        manager_payload=_manager_result_payload(manager_result),
        correction_target=dict(tool_state.get("correction_target") or {}),
    ):
        nutrition_artifact = build_remove_item_target_evidence_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date,
            request_id=request_id,
            correction_target=dict(tool_state.get("correction_target") or {}),
            manager_semantic_decision=dict(getattr(manager_result, "semantic_decision", {}) or {}),
        )
        tool_state["nutrition_artifact"] = nutrition_artifact
        payload = nutrition_artifact.payload
    manager_followup_artifact = build_manager_ask_followup_draft_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        request_id=request_id,
        manager_result=manager_result,
    )
    if manager_followup_artifact is not None:
        nutrition_artifact = manager_followup_artifact
        tool_state["nutrition_artifact"] = nutrition_artifact
        payload = nutrition_artifact.payload
    apply_final_action_to_payload(
        payload=payload,
        raw_user_input=raw_user_input,
        final_action=manager_result.final_action,
        manager_answer_contract=dict(getattr(manager_result, "answer_contract", {}) or {}),
        manager_semantic_decision=dict(getattr(manager_result, "semantic_decision", {}) or {}),
    )
    attach_correction_target_ref_to_payload(
        payload=payload,
        correction_target=dict(tool_state.get("correction_target") or {}),
        source="manager_target_attachment_validated",
    )
    commit_boundary_preflight = run_commit_boundary_preflight(
        payload=payload,
        manager_final_action=manager_result.final_action,
        active_body_plan_present=bool(getattr(state_before, "onboarding_ready", False)),
        correction_target=tool_state["correction_target"],
        manager_semantic_decision=dict(getattr(manager_result, "semantic_decision", {}) or {}),
    )
    attach_owner_lineage_trace(
        payload=payload,
        manager_semantic_decision=dict(getattr(manager_result, "semantic_decision", {}) or {}),
        manager_final_action=manager_result.final_action,
    )
    phase_a_trace = dict(phase_a_trace or {})
    if manager_triggered_history_trace is not None:
        phase_a_trace["manager_triggered_history_expansion"] = manager_triggered_history_trace
    commit_boundary_trace_payload = commit_boundary_preflight.trace_payload()
    guard_blocked_commit_preflight = dict(
        dict(getattr(manager_result, "guard_outcome", {}) or {}).get("phase_a_commit_boundary_preflight") or {}
    )
    if manager_result.request_failure_family and guard_blocked_commit_preflight.get("blocked") is True:
        commit_boundary_trace_payload = guard_blocked_commit_preflight
    phase_a_trace["phase_a_commit_boundary_preflight"] = commit_boundary_trace_payload
    if commit_boundary_preflight.blocked:
        manager_trace = dict(getattr(manager_result, "trace", {}) or {})
        manager_trace["phase_a_commit_boundary_preflight"] = commit_boundary_preflight.trace_payload()
        manager_result = replace(
            manager_result,
            final_action="no_commit",
            workflow_effect="safe_failure",
            request_failure_family=commit_boundary_preflight.failure_family or "phase_a_commit_boundary_blocked",
            guard_outcome={
                **dict(getattr(manager_result, "guard_outcome", {}) or {}),
                "phase_a_commit_boundary_preflight": commit_boundary_preflight.trace_payload(),
            },
            trace=manager_trace,
        )

    persistence_result = None
    guard_blocked_for_side_effects = bool(manager_result.request_failure_family) and manager_result.final_action == "no_commit"
    persistence_allowed = not commit_boundary_preflight.blocked and not (
        guard_blocked_for_side_effects
    )
    if persistence_allowed:
        persistence_result = persist_intake_execution_artifact(
            db,
            nutrition_artifact=nutrition_artifact,
            final_action=manager_result.final_action,
            manager_semantic_decision=dict(getattr(manager_result, "semantic_decision", {}) or {}),
            request_id=request_id,
            record_timing=record_timing,
            now_ms=_now_ms,
            state_mutation_summary=state_mutation_summary,
        )

    stage_start = _now_ms()
    state_after = resolve_intake_state(db, user_external_id=user_external_id, local_date=local_date, exclude_trace_id=request_id)
    record_timing("state_after_resolution", _now_ms() - stage_start)
    tool_outputs, budget_summary = build_refreshed_intake_tool_outputs(
        raw_user_input=raw_user_input,
        nutrition_artifact=nutrition_artifact,
        correction_target=tool_state["correction_target"],
        budget_summary=budget_summary,
        manager_tool_results=manager_result.tool_results,
        state_mutation_summary=state_mutation_summary,
        commit_boundary_blocked=commit_boundary_preflight.blocked,
        guard_blocked_for_side_effects=guard_blocked_for_side_effects,
        state_before=state_before,
        state_after=state_after,
    )

    return build_intake_execution_response(
        db,
        request_id=request_id,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        allow_search=allow_search,
        state_before=state_before,
        state_after=state_after,
        manager_decision=manager_decision,
        manager_result=manager_result,
        nutrition_artifact=nutrition_artifact,
        persistence_result=persistence_result,
        budget_summary=budget_summary,
        tool_outputs=tool_outputs,
        state_mutation_summary=state_mutation_summary,
        stage_timings=stage_timings,
        phase_a_trace=phase_a_trace,
    )
