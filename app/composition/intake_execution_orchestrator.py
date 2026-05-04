"""Thin intake execution entrypoint.

Semantic ownership lives in the single-manager runtime, domain tools, execution
guard, persistence support, and deterministic sidecar builders.
"""

from __future__ import annotations

from dataclasses import replace
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.composition.intake_execution_response import build_intake_execution_response, finalized_budget_summary
from app.composition.manager_context_runtime import build_runtime_manager_context_packet_v1
from app.composition.request_runtime_context import load_request_runtime_context
from app.composition.intake_manager_tool_batch import (
    apply_final_action_to_payload,
    attach_correction_target_ref_to_payload,
    execute_manager_tool_calls,
    nutrition_tool_output,
    validate_manager_target_proposal,
)
from app.composition.state_resolver import resolve_intake_state
from app.composition.commit_boundary_preflight import run_commit_boundary_preflight
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
from app.intake.application.target_evidence_artifacts import TargetEvidenceArtifact
from app.intake.infrastructure.models import MealItemRecord
from app.nutrition.application.manager_policy_hints import nutrition_manager_policy_hints
from app.nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from app.nutrition.application.owner_lineage_trace import attach_owner_lineage_trace
from app.nutrition.application.web_extract_port import WebExtractPort
from app.nutrition.application.web_search_port import WebSearchPort
from app.runtime.application.manager_service import run_intake_manager
from app.shared.contracts.common import EstimateRequest
from app.shared.contracts.correction_operation import structured_payload_requests_remove_item
from app.shared.contracts.correction_target import validate_correction_target_ref
from app.shared.contracts.intake import EstimatePayload
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


def _remove_item_target_evidence_ready(*, manager_payload: dict[str, Any], correction_target: dict[str, Any]) -> bool:
    if str(manager_payload.get("final_action") or "") != "correction_applied":
        return False
    if not structured_payload_requests_remove_item(manager_payload):
        return False
    return validate_correction_target_ref(correction_target).get("resolved") is True


def _manager_result_target_proposals(manager_result: Any) -> list[tuple[str, dict[str, Any]]]:
    proposals: list[tuple[str, dict[str, Any]]] = []
    top_target = getattr(manager_result, "target_attachment", None)
    if isinstance(top_target, dict) and top_target:
        proposals.append(("manager_result.target_attachment", dict(top_target)))
    semantic_decision = getattr(manager_result, "semantic_decision", None)
    if isinstance(semantic_decision, dict):
        semantic_target = semantic_decision.get("target_attachment")
        if isinstance(semantic_target, dict) and semantic_target:
            proposals.append(("manager_result.semantic_decision.target_attachment", dict(semantic_target)))
    answer_contract = getattr(manager_result, "answer_contract", None)
    if isinstance(answer_contract, dict):
        answer_target = answer_contract.get("target_attachment")
        if isinstance(answer_target, dict) and answer_target:
            proposals.append(("manager_result.answer_contract.target_attachment", dict(answer_target)))
    return proposals


def _validate_final_manager_target_attachment(
    *,
    correction_target: dict[str, Any],
    manager_result: Any,
) -> dict[str, Any]:
    if str(getattr(manager_result, "final_action", "") or "") != "correction_applied":
        return dict(correction_target)
    if validate_correction_target_ref(correction_target).get("resolved") is True:
        return dict(correction_target)

    last_validation = dict(correction_target)
    for source, proposal in _manager_result_target_proposals(manager_result):
        resolved = validate_manager_target_proposal(
            correction_target=correction_target,
            proposal={**proposal, "target_proposal_source": source},
        )
        last_validation = resolved
        if validate_correction_target_ref(resolved).get("resolved") is True:
            return resolved
    return last_validation


def _remaining_item_totals_after_target_removal(
    db: Session,
    *,
    target_item_id: int | None,
) -> dict[str, Any]:
    if target_item_id is None:
        return {
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "remaining_item_names": [],
            "removed_item_name": None,
        }
    target_item = db.get(MealItemRecord, target_item_id)
    if target_item is None:
        return {
            "estimated_kcal": 0,
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "remaining_item_names": [],
            "removed_item_name": None,
        }
    old_items = db.execute(
        select(MealItemRecord)
        .where(MealItemRecord.meal_version_id == target_item.meal_version_id)
        .order_by(MealItemRecord.item_index.asc())
    ).scalars().all()
    remaining_items = [old_item for old_item in old_items if old_item.id != target_item.id]
    return {
        "estimated_kcal": sum(int(item.estimated_kcal or 0) for item in remaining_items),
        "protein_g": sum(int(item.protein_g or 0) for item in remaining_items),
        "carb_g": sum(int(item.carb_g or 0) for item in remaining_items),
        "fat_g": sum(int(item.fat_g or 0) for item in remaining_items),
        "remaining_item_names": [str(item.name or "") for item in remaining_items],
        "removed_item_name": str(target_item.name or ""),
    }


def _build_remove_item_target_evidence_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    request_id: str,
    correction_target: dict[str, Any],
    manager_semantic_decision: dict[str, Any],
) -> TargetEvidenceArtifact:
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("TargetEvidenceRemovalProvider", (), {"readiness": lambda self: {"configured": False}})(),
    )
    target_validation = validate_correction_target_ref(correction_target)
    canonical_name = str(target_validation.get("canonical_name") or correction_target.get("canonical_name") or "").strip()
    remaining_totals = _remaining_item_totals_after_target_removal(
        db,
        target_item_id=target_validation.get("meal_item_id"),
    )
    payload = EstimatePayload(
        request_id=request_id,
        meal_title=f"remove {canonical_name}".strip() or "remove item",
        estimated_kcal=int(remaining_totals["estimated_kcal"]),
        protein_g=int(remaining_totals["protein_g"]),
        carb_g=int(remaining_totals["carb_g"]),
        fat_g=int(remaining_totals["fat_g"]),
        source_decision="ready",
        answer_mode="direct_answer",
        action_taken="correction_applied",
        route_target="direct_answer",
        reply_text="Removed the selected item.",
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "correction_operation": "remove_item",
            "correction_operation_source": "manager_structured_decision",
            "correction_target_ref": {
                "meal_thread_id": target_validation.get("meal_thread_id"),
                "meal_item_id": target_validation.get("meal_item_id"),
                "canonical_name": canonical_name,
            },
            "canonical_remaining_item_totals": remaining_totals,
            "target_evidence_contract": {
                "evidence_type": "target_evidence",
                "source": "resolve_correction_target",
                "nutrition_evidence_required": False,
                "nutrition_evidence_present": False,
                "target_evidence_is_nutrition_evidence": False,
                "kcal_source": "canonical_remaining_items",
                "placeholder_kcal_used": False,
                "manager_semantic_decision": dict(manager_semantic_decision or {}),
            },
        },
    )
    return TargetEvidenceArtifact(request=request, runtime_context=runtime_context, payload=payload)


def _manager_ask_followup_question(manager_result: Any) -> str:
    answer_contract = dict(getattr(manager_result, "answer_contract", {}) or {})
    semantic_decision = dict(getattr(manager_result, "semantic_decision", {}) or {})
    return str(
        answer_contract.get("followup_question")
        or semantic_decision.get("followup_question")
        or ""
    ).strip()


def _manager_ask_followup_support_ready(manager_result: Any) -> bool:
    if str(getattr(manager_result, "manager_action", "") or "") != "final":
        return False
    if str(getattr(manager_result, "final_action", "") or "") != "ask_followup":
        return False
    semantic_decision = dict(getattr(manager_result, "semantic_decision", {}) or {})
    semantic_final_action = str(semantic_decision.get("final_action_candidate") or "")
    semantic_workflow = str(semantic_decision.get("workflow_effect") or "")
    if semantic_final_action and semantic_final_action != "ask_followup":
        return False
    if semantic_workflow and semantic_workflow != "ask_followup":
        return False
    if str(semantic_decision.get("mutation_intent_candidate") or "no_mutation") not in {"", "no_mutation"}:
        return False
    return bool(_manager_ask_followup_question(manager_result))


def _build_manager_ask_followup_draft_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    request_id: str,
    manager_result: Any,
) -> EstimatedNutritionArtifact | None:
    if not _manager_ask_followup_support_ready(manager_result):
        return None

    followup_question = _manager_ask_followup_question(manager_result)
    answer_contract = dict(getattr(manager_result, "answer_contract", {}) or {})
    semantic_decision = dict(getattr(manager_result, "semantic_decision", {}) or {})
    request = EstimateRequest(text=raw_user_input, allow_search=False, user_id=user_external_id)
    runtime_context = load_request_runtime_context(
        request=request,
        db=db,
        provider=type("ManagerAskFollowupDraftProvider", (), {"readiness": lambda self: {"configured": False}})(),
    )
    meal_title = str(
        semantic_decision.get("meal_title")
        or answer_contract.get("meal_title")
        or raw_user_input
        or "pending meal"
    ).strip()
    payload = EstimatePayload(
        request_id=request_id,
        meal_title=meal_title or "pending meal",
        estimated_kcal=0,
        source_decision="ask_user",
        answer_mode=None,
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        followup_question=followup_question,
        follow_up_needed=True,
        follow_up_reasoning="manager_final_ask_followup",
        reply_text=str(answer_contract.get("reply_text") or followup_question),
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "response_mode_hint": "clarify_first",
            "followup_question": followup_question,
            "missing_slots": ["composition_details"],
            "blocking_slots": ["composition_details"],
            "unresolved_info": ["composition_details"],
            "route_family": "component_driven_meal",
            "canonical_write_decision": {
                "can_write_canonical": False,
                "source": "manager_ask_followup_draft",
            },
            "manager_ask_followup_draft_contract": {
                "source": "manager_structured_final_action",
                "manager_final_action": "ask_followup",
                "nutrition_evidence_required": False,
                "deterministic_role": "persist_manager_owned_pending_followup_only",
                "raw_text_semantic_inference": False,
                "manager_semantic_decision": semantic_decision,
            },
        },
        quality_signals={"estimate_mode": "ask_followup_only"},
    )
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)


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
            session_id=request_id,
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
                    session_id=request_id,
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
            if _remove_item_target_evidence_ready(
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
        return {"ok": True, "phase_a_transition_guard_preflight": preflight_trace}

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
    tool_state["correction_target"] = _validate_final_manager_target_attachment(
        correction_target=dict(tool_state.get("correction_target") or {}),
        manager_result=manager_result,
    )

    nutrition_artifact = tool_state.get("nutrition_artifact")
    budget_summary = tool_state.get("budget_summary")
    payload = getattr(nutrition_artifact, "payload", None) if nutrition_artifact is not None else None
    if payload is None and _remove_item_target_evidence_ready(
        manager_payload=_manager_result_payload(manager_result),
        correction_target=dict(tool_state.get("correction_target") or {}),
    ):
        nutrition_artifact = _build_remove_item_target_evidence_artifact(
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
    if payload is None:
        nutrition_artifact = _build_manager_ask_followup_draft_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date,
            request_id=request_id,
            manager_result=manager_result,
        )
        if nutrition_artifact is not None:
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
    phase_a_trace["phase_a_commit_boundary_preflight"] = commit_boundary_preflight.trace_payload()
    if commit_boundary_preflight.blocked:
        manager_trace = dict(getattr(manager_result, "trace", {}) or {})
        manager_trace["phase_a_commit_boundary_preflight"] = commit_boundary_preflight.trace_payload()
        manager_result = replace(
            manager_result,
            final_action="no_commit",
            workflow_effect="safe_failure",
            request_failure_family="phase_a_commit_boundary_blocked",
            guard_outcome={
                **dict(getattr(manager_result, "guard_outcome", {}) or {}),
                "phase_a_commit_boundary_preflight": commit_boundary_preflight.trace_payload(),
            },
            trace=manager_trace,
        )

    persistence_result = None
    if not commit_boundary_preflight.blocked:
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

    state_after = resolve_intake_state(
        db,
        user_external_id=user_external_id,
        local_date=local_date,
    )
    refreshed_tool_results = [dict(item) for item in manager_result.tool_results]
    if nutrition_artifact is not None:
        refreshed_nutrition_output = nutrition_tool_output(
            raw_user_input=raw_user_input,
            nutrition_artifact=nutrition_artifact,
            correction_target=tool_state["correction_target"],
            budget_summary=budget_summary,
        )
        for index, item in enumerate(refreshed_tool_results):
            if str(item.get("tool_name") or "").strip() == "estimate_nutrition":
                refreshed_tool_results[index] = refreshed_nutrition_output
                break
    tool_outputs = {"tool_results": refreshed_tool_results}
    if state_mutation_summary.get("canonical_commit") and budget_summary is not None:
        budget_summary = finalized_budget_summary(
            budget_summary=budget_summary,
            state_before=state_before,
            state_after=state_after,
        )
        tool_outputs["budget_summary"] = budget_summary

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
