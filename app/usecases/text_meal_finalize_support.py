from __future__ import annotations

from typing import Any

from ..application.answer_support import boundary_followup_question, evaluate_answer
from ..application.context_assembly import build_context_pack_trace
from ..observability.payload_builders import build_payload, build_trace_contract
from ..observability.text_meal_observability import build_multi_turn_context
from ..schemas import EvidenceResolutionTrace, EstimatePayload, MemoryTrace, ToolDecisionTrace
from ..application.followup_policy import annotate_cannot_estimate_abstain_policy
from .text_meal_response_support import finalize_response_payload
from .text_meal_trace_assembly import assemble_finalize_trace_bundle


def build_boundary_clarification_payload(
    *,
    request: Any,
    effective_request: Any,
    request_id: str,
    planner_result: Any,
    planner_enabled: bool,
    conversation_state: Any,
    context_str: str,
    boundary_trace: dict[str, Any],
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
    debug_steps: list[dict[str, Any]],
    llm_traces: list[dict[str, Any]],
    available_tools: list[str],
    evidence_guardrail_prompt: str,
) -> EstimatePayload:
    parsed = {
        "decision": "ASK_USER",
        "title": conversation_state.latest_meal_title or effective_request.text,
        "components": [],
        "protein_g": 0,
        "carb_g": 0,
        "fat_g": 0,
        "estimated_kcal": 0,
        "kcal_low": 0,
        "kcal_high": 0,
        "uncertainty_factors": ["meal_boundary_unresolved"],
        "followup_question": boundary_followup_question(),
        "route_family": "meal_boundary",
        "followup_policy_decision": "clarify_before_estimate",
        "missing_slots": ["meal_boundary"],
        "blocking_slots": ["meal_boundary"],
        "blockers": ["meal boundary unresolved"],
        "follow_up_needed": True,
        "follow_up_reasoning": "",
        "unresolved_info": ["meal_boundary"],
        "response_mode_hint": "clarify_first",
        "state_transition_hint": "draft_unresolved",
        "action_taken": "clarify_before_estimate",
        "tool_request": "none",
        "tool_request_reason": "",
        "answer_payload": {},
    }
    best_quality = evaluate_answer(parsed, risk_packet, meal_template)
    context_pack_trace = build_context_pack_trace(
        state=conversation_state,
        evidence_bundle={"candidates": [], "selected_titles": [], "source_classes": [], "conflict_count": 0, "selected_count": 0},
        available_tools=available_tools,
        evidence_guardrail_prompt=evidence_guardrail_prompt,
    ).model_dump(mode="json")
    tool_decision_trace = ToolDecisionTrace(
        available_tools=available_tools,
        candidate_tool_calls=[],
        executed_tool_calls=[],
    ).model_dump(mode="json")
    evidence_resolution_trace = EvidenceResolutionTrace().model_dump(mode="json")
    memory_trace = MemoryTrace(
        durable_memory_enabled=True,
        hits=[],
        write_candidates=[],
    ).model_dump(mode="json")
    multi_turn_context = build_multi_turn_context(
        state=conversation_state,
        planner_intent=planner_result.intent,
        context_snapshot=context_str,
        retrieval_query_rewritten=False,
        original_retrieval_query=None,
        effective_retrieval_query=None,
    )
    trace_contract = build_trace_contract(
        request=request,
        effective_request=effective_request,
        planner_result=planner_result,
        planner_enabled=planner_enabled,
        normalization={
            "raw_text": request.text,
            "normalized_text": effective_request.text,
            "normalizer_applied": False,
            "notes": [],
        },
        risk_packet=risk_packet,
        meal_template=meal_template,
        template_override_blocked=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        sources=[],
        used_search=False,
        search_query=None,
        current_parsed=parsed,
        best_parsed=parsed,
        best_source="boundary_clarification",
        quality_signals=best_quality,
        retry_triggered=False,
        retry_reason=None,
        context_pack_trace=context_pack_trace,
        tool_decision_trace=tool_decision_trace,
        boundary_trace=boundary_trace,
        judge_trace={},
        evidence_resolution_trace=evidence_resolution_trace,
        memory_trace=memory_trace,
    )
    return build_payload(
        effective_request,
        request_id=request_id,
        parsed=parsed,
        risk_packet=risk_packet,
        action_taken="clarify_before_estimate",
        route_target="clarify_user_private",
        route_reason="boundary_clarification",
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        retrieval_triggered=False,
        retrieval_query=None,
        retrieved_knowledge=[],
        quality_signals=best_quality,
        retry_triggered=False,
        retry_reason=None,
        best_answer_source="boundary_clarification",
        private_only=True,
        used_search=False,
        search_query=None,
        search_quality=None,
        sources=[],
        trace_contract=trace_contract,
        north_star_evaluation={"win_loss_neutral": "neutral"},
        multi_turn_context=multi_turn_context,
        token_usage={"total_prompt_tokens": 0, "total_completion_tokens": 0, "total_tokens": 0, "llm_call_count": len(llm_traces)},
        trace_meta={},
        span_timeline=[],
        decision_journal={},
        evidence_journal={},
        diagnosis={},
        context_pack_trace=context_pack_trace,
        tool_decision_trace=tool_decision_trace,
        boundary_trace=boundary_trace,
        judge_trace={},
        evidence_resolution_trace=evidence_resolution_trace,
        memory_trace=memory_trace,
    )


async def finalize_text_meal_payload(
    *,
    primary_llm: Any,
    request: Any,
    effective_request: Any,
    request_id: str,
    planner_result: Any,
    planner_enabled: bool,
    normalization: dict[str, Any],
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
    retrieval_triggered: bool,
    retrieval_query: str | None,
    filtered_knowledge: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    available_tools: list[str],
    candidate_tool_calls: list[dict[str, Any]],
    executed_tool_calls: list[dict[str, Any]],
    doc_read_fragments: list[dict[str, Any]],
    conversation_state: Any,
    context_str: str,
    boundary_trace: dict[str, Any],
    judge_trace: dict[str, Any],
    debug_steps: list[dict[str, Any]],
    llm_traces: list[dict[str, Any]],
    best_parsed: dict[str, Any],
    current_parsed: dict[str, Any],
    best_quality: dict[str, Any],
    best_private: bool,
    best_source: str,
    used_search: bool,
    search_query: str | None,
    search_quality: str | None,
    retry_triggered: bool,
    retry_reason: str | None,
    evidence_guardrail_prompt: str,
    build_evidence_bundle: Any,
    merge_evidence_items: Any,
    to_evidence_candidate: Any,
    source_class_for_item: Any,
    now_iso: Any,
    build_trace_envelope: Any,
    task_meal_link_result: Any,
    decision_result: Any,
    nutrition_result: Any,
    max_selected_evidence_items: int,
    max_durable_memory_hits: int,
    max_tokens: int,
    run_stage: Any,
) -> EstimatePayload:
    planner_requires_clarify = planner_result.meal_boundary == "boundary_clarification"
    normalized_best = {**dict(best_parsed), "follow_up_needed": bool(best_parsed.get("follow_up_needed"))}
    cannot_estimate_abstain = str(getattr(nutrition_result, "resolution_mode", "")) == "cannot_estimate_yet"
    if cannot_estimate_abstain:
        normalized_best = annotate_cannot_estimate_abstain_policy(normalized_best)
    requires_follow_up = (
        planner_requires_clarify
        or bool(normalized_best.get("follow_up_needed"))
        or str(normalized_best.get("action_taken") or "") == "clarify_before_estimate"
        or cannot_estimate_abstain
    )
    if requires_follow_up and planner_requires_clarify:
        normalized_best["followup_policy_decision"] = "clarify_before_estimate"
        normalized_best["blocking_slots"] = list(dict.fromkeys(list(normalized_best.get("blocking_slots", [])) + list(planner_result.planning_brief.clarification_targets)))
        normalized_best["missing_slots"] = list(dict.fromkeys(list(normalized_best.get("missing_slots", [])) + list(planner_result.planning_brief.clarification_targets)))
    action_taken = str(normalized_best.get("action_taken") or "clarify_before_estimate")
    route_target = "clarify_user_private" if requires_follow_up else "best_effort_answer"
    trace_bundle = assemble_finalize_trace_bundle(
        request=request,
        effective_request=effective_request,
        request_id=request_id,
        planner_result=planner_result,
        planner_enabled=planner_enabled,
        normalization=normalization,
        risk_packet=risk_packet,
        meal_template=meal_template,
        retrieval_query=retrieval_query,
        filtered_knowledge=filtered_knowledge,
        sources=sources,
        available_tools=available_tools,
        candidate_tool_calls=candidate_tool_calls,
        executed_tool_calls=executed_tool_calls,
        doc_read_fragments=doc_read_fragments,
        conversation_state=conversation_state,
        context_str=context_str,
        boundary_trace=boundary_trace,
        judge_trace=judge_trace,
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        current_parsed=current_parsed,
        best_parsed=normalized_best,
        best_quality=best_quality,
        best_source=best_source,
        used_search=used_search,
        search_query=search_query,
        retry_triggered=retry_triggered,
        retry_reason=retry_reason,
        evidence_guardrail_prompt=evidence_guardrail_prompt,
        build_evidence_bundle=build_evidence_bundle,
        merge_evidence_items=merge_evidence_items,
        to_evidence_candidate=to_evidence_candidate,
        source_class_for_item=source_class_for_item,
        now_iso=now_iso,
        build_trace_envelope=build_trace_envelope,
        provider_name=type(primary_llm).__name__,
        max_selected_evidence_items=max_selected_evidence_items,
        max_durable_memory_hits=max_durable_memory_hits,
    )
    payload = await finalize_response_payload(
        primary_llm=primary_llm,
        effective_request=effective_request,
        request_id=request_id,
        task_meal_link_result=task_meal_link_result,
        decision_result=decision_result,
        nutrition_result=nutrition_result,
        conversation_state=conversation_state,
        llm_traces=llm_traces,
        max_tokens=max_tokens,
        run_stage=run_stage,
        best_parsed=normalized_best,
        risk_packet=risk_packet,
        action_taken=action_taken,
        route_target=route_target,
        debug_steps=debug_steps,
        best_quality=best_quality,
        retry_triggered=retry_triggered,
        retry_reason=retry_reason,
        best_source=best_source,
        best_private=best_private,
        retrieval_triggered=retrieval_triggered,
        retrieval_query=retrieval_query,
        filtered_knowledge=filtered_knowledge,
        used_search=used_search,
        search_query=search_query,
        search_quality=search_quality,
        sources=sources,
        trace_envelope=trace_bundle.trace_envelope,
    )
    if cannot_estimate_abstain:
        payload.reply_text = "I can't estimate this safely yet. What exactly did you have?"
        payload.followup_question = "I can't estimate this safely yet. What exactly did you have?"
    if cannot_estimate_abstain:
        payload.trace_contract["canonical_write_decision"] = dict(normalized_best.get("canonical_write_decision") or {})
        payload.trace_contract["canonical_write_decision"].setdefault("mode", "abstain")
        payload.trace_contract["canonical_write_decision"].setdefault("can_write_canonical", False)
        payload.trace_contract["canonical_write_decision"].setdefault("reason", "cannot_estimate_yet")
        payload.trace_contract["abstain_lane"] = "cannot_estimate_yet"
        payload.route_target = "clarify_user_private"
        payload.route_reason = "cannot_estimate_abstain"
        payload.action_taken = "clarify_before_estimate"
        payload.follow_up_needed = True
    return payload
