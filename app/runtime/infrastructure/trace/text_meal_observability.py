from __future__ import annotations

from typing import Any

from app.shared.domain import (
    ConversationState,
    DecisionJournal,
    EvidenceJournal,
    TraceDiagnosis,
    TraceEnvelope,
    TraceMeta,
    TraceSpan,
)
from .trace_eval import evaluate_trace_contract


def compute_token_usage(llm_traces: list[dict[str, Any]]) -> dict[str, Any]:
    total_prompt_tokens = 0
    total_completion_tokens = 0
    for trace in llm_traces:
        usage = trace.get("usage", {}) or {}
        total_prompt_tokens += trace.get("prompt_tokens") or usage.get("prompt_tokens", 0) or 0
        total_completion_tokens += trace.get("completion_tokens") or usage.get("completion_tokens", 0) or 0
    return {
        "total_prompt_tokens": total_prompt_tokens,
        "total_completion_tokens": total_completion_tokens,
        "total_tokens": total_prompt_tokens + total_completion_tokens,
        "llm_call_count": len(llm_traces),
    }


def build_multi_turn_context(
    *,
    state: ConversationState,
    planner_intent: str,
    context_snapshot: str,
    retrieval_query_rewritten: bool,
    original_retrieval_query: str | None,
    effective_retrieval_query: str | None,
) -> dict[str, Any]:
    is_multi_turn = bool(
        state.latest_log_id
        and (planner_intent in ["clarification", "modification"] or state.pending_question)
    )
    state_source = "none"
    if state.latest_log_id:
        state_source = "meal_log"
    elif state.recent_messages:
        state_source = "message_buffer"
    state_consistency = "consistent"
    if state.pending_question and not state.latest_log_id:
        state_consistency = "ambiguous"
    elif state.latest_log_id and state.latest_log_status == "superseded":
        state_consistency = "stale"
    dynamic_context_pack = {
        "active_meal_summary": state.active_meal_summary.model_dump(mode="json"),
        "active_meal_state": state.active_meal_state.model_dump(mode="json"),
        "pending_followup_state": state.pending_followup_state.model_dump(mode="json"),
        "recent_relevant_turns": [msg.model_dump(mode="json") for msg in state.recent_relevant_turns],
        "retrieved_meal_records": [chunk.model_dump(mode="json") for chunk in state.retrieved_meal_records],
        "session_summary": state.session_summary.model_dump(mode="json"),
    }
    return {
        "is_multi_turn": is_multi_turn,
        "turn_intent": planner_intent,
        "latest_log_id": state.latest_log_id,
        "latest_log_title": state.latest_meal_title,
        "latest_log_status": state.latest_log_status,
        "latest_known_components": state.latest_components,
        "superseded_log_id": state.latest_log_id if is_multi_turn else None,
        "parent_log_id": state.latest_log_id if is_multi_turn else None,
        "active_parent_log_id": state.active_parent_log_id,
        "state_source": state_source,
        "pending_question_source_log_id": state.latest_log_id if state.pending_question else None,
        "state_consistency": state_consistency,
        "conversation_window_size": state.conversation_window_size,
        "conversation_archive_count": state.conversation_archive_count,
        "conversation_archive_hit_count": len(state.conversation_archive_hits),
        "conversation_digest": state.conversation_digest.model_dump(mode="json"),
        "conversation_hit_refs": [hit.message_id for hit in state.conversation_archive_hits],
        "planner_state_digest": state.planner_state_digest.model_dump(mode="json"),
        "active_meal_summary": state.active_meal_summary.model_dump(mode="json"),
        "active_meal_state": state.active_meal_state.model_dump(mode="json"),
        "pending_followup_state": state.pending_followup_state.model_dump(mode="json"),
        "session_summary": state.session_summary.model_dump(mode="json"),
        "recent_turn_summary": state.recent_turn_summary.model_dump(mode="json"),
        "recent_relevant_turns": [msg.model_dump(mode="json") for msg in state.recent_relevant_turns],
        "durable_memory_hits": [hit.model_dump(mode="json") for hit in state.durable_memory_hits],
        "boundary_clarification_open": state.boundary_clarification_open,
        "boundary_clarification_source_meal_id": state.boundary_clarification_source_meal_id,
        "retrieval_diagnostics": state.retrieval_diagnostics,
        "history_retrieval_router": (state.retrieval_diagnostics or {}).get("router_order", []),
        "dynamic_context_pack": dynamic_context_pack,
        "context_injection_snapshot": context_snapshot[:500] if context_snapshot else "",
        "message_buffer_length": len(state.recent_messages),
        "retrieval_query_rewritten": retrieval_query_rewritten,
        "original_retrieval_query": original_retrieval_query,
        "effective_retrieval_query": effective_retrieval_query if retrieval_query_rewritten else None,
        "resolved_query_origin": "planner" if retrieval_query_rewritten else "raw_or_local",
    }


def _repairability_for_layer(failed_layer: str | None) -> str:
    if failed_layer in {"planner", "normalizer", "grounding", "repair_rescue"}:
        return "high"
    if failed_layer in {"risk_validator", "layer3_primary_llm"}:
        return "medium"
    return "low" if failed_layer else "none"


def _suggested_next_action(failed_layer: str | None) -> str:
    return {
        "planner": "inspect_planner_context_and_intent_routing",
        "normalizer": "inspect_normalizer_side_effects",
        "risk_validator": "inspect_required_checks_and_followup_policy",
        "layer3_primary_llm": "inspect_primary_prompt_and_uncertainty_modeling",
        "grounding": "inspect_retrieval_identity_and_evidence_handoff",
        "repair_rescue": "inspect_candidate_guard_and_retry_selection",
        None: "no_action_required",
    }[failed_layer]


def _build_span_timeline(
    *,
    llm_traces: list[dict[str, Any]],
    debug_steps: list[dict[str, Any]],
    trace_contract: dict[str, Any],
) -> list[dict[str, Any]]:
    spans: list[TraceSpan] = []
    for idx, trace in enumerate(llm_traces):
        span_id = str(trace.get("span_id") or f"span:{trace.get('stage', 'unknown')}:{trace.get('attempt_index', 1)}")
        spans.append(
            TraceSpan(
                span_id=span_id,
                parent_span_id=trace.get("parent_span_id"),
                stage=str(trace.get("stage") or "unknown"),
                status="error" if trace.get("error") else "ok",
                attempt_index=int(trace.get("attempt_index") or 1),
                trigger_reason=trace.get("trigger_reason"),
                duration_ms=trace.get("duration_ms"),
                input_ref=f"llm_traces[{idx}].request_payload",
                output_ref=f"llm_traces[{idx}].parsed_object",
                stage_input_summary=trace.get("stage_input_summary") or {},
                stage_output_summary=trace.get("stage_output_summary") or {},
                handoff_contract=trace.get("handoff_contract") or {},
            )
        )

    grounding_attempts = trace_contract.get("grounding_attempts", []) or []
    for index, attempt in enumerate(grounding_attempts, start=1):
        spans.append(
            TraceSpan(
                span_id=f"span:grounding:{attempt.get('kind', 'unknown')}:{index}",
                stage=f"grounding_{attempt.get('kind', 'unknown')}",
                status="ok",
                attempt_index=index,
                trigger_reason="evidence_lookup",
                input_ref="trace_contract.grounding_attempts",
                output_ref="trace_contract.grounding_summary",
                stage_input_summary={"query": attempt.get("query")},
                stage_output_summary={"hit_count": attempt.get("hit_count", 0), "used": attempt.get("used", False)},
                handoff_contract={"kind": attempt.get("kind")},
            )
        )

    enrichment_steps = [step for step in debug_steps if step.get("step") == "deterministic_enrichment"]
    for index, step in enumerate(enrichment_steps, start=1):
        spans.append(
            TraceSpan(
                span_id=f"span:deterministic_enrichment:{index}",
                stage="deterministic_enrichment",
                attempt_index=index,
                trigger_reason=step.get("stage_label"),
                input_ref="debug_steps",
                output_ref="payload.component_estimates",
                stage_input_summary={"stage_label": step.get("stage_label")},
                stage_output_summary={
                    "deterministic_applied": step.get("deterministic_applied", False),
                    "deterministic_hit": step.get("deterministic_hit", False),
                    "estimated_kcal": step.get("deterministic_estimated_kcal"),
                },
                handoff_contract={"estimate_mode": step.get("estimate_mode")},
            )
        )

    persistence = trace_contract.get("persistence_decision", {}) or {}
    if persistence:
        spans.append(
            TraceSpan(
                span_id="span:persistence_decision:1",
                stage="persistence_decision",
                attempt_index=1,
                trigger_reason=persistence.get("action"),
                input_ref="trace_contract.persistence_decision",
                output_ref="multi_turn_context",
                stage_input_summary={"planner_intent": persistence.get("planner_intent")},
                stage_output_summary={
                    "action": persistence.get("action"),
                    "status": persistence.get("status"),
                    "parent_log_id": persistence.get("parent_log_id"),
                },
                handoff_contract={"assistant_message_appended": persistence.get("assistant_message_appended", False)},
            )
        )

    return [span.model_dump(mode="json") for span in spans]


def _build_decision_journal(
    *,
    trace_contract: dict[str, Any],
    best_answer_source: str | None,
    retry_triggered: bool,
) -> dict[str, Any]:
    planner_output = trace_contract.get("planner_output", {}) or {}
    return DecisionJournal(
        planner_intent=planner_output.get("intent"),
        route_family=trace_contract.get("route_family"),
        followup_policy_decision=trace_contract.get("followup_policy_decision"),
        followup_decision=trace_contract.get("followup_decision"),
        best_answer_source=best_answer_source,
        retry_triggered=retry_triggered,
        retry_reason=trace_contract.get("retry_reason"),
    ).model_dump(mode="json")


def _build_evidence_journal(
    *,
    trace_contract: dict[str, Any],
    best_answer_source: str | None,
) -> dict[str, Any]:
    grounding_summary = trace_contract.get("grounding_summary", {}) or {}
    attempts = trace_contract.get("grounding_attempts", []) or []
    local_hit_count = next((int(item.get("hit_count", 0)) for item in attempts if item.get("kind") == "local_retrieval"), 0)
    search_hit_count = next((int(item.get("hit_count", 0)) for item in attempts if item.get("kind") == "search"), 0)
    return EvidenceJournal(
        retrieval_query=next((item.get("query") for item in attempts if item.get("kind") == "local_retrieval"), None),
        local_hit_count=local_hit_count,
        search_query=next((item.get("query") for item in attempts if item.get("kind") == "search"), None),
        search_hit_count=search_hit_count,
        evidence_passed_to_llm=best_answer_source in {"with_local_knowledge", "with_search_evidence", "retry", "initial", "primary"},
        exact_truth_candidate={"present": bool(grounding_summary.get("exact_truth_present"))},
        grounding_contradiction=bool(trace_contract.get("grounding_contradiction")),
        match_confidence=trace_contract.get("match_confidence"),
        db_hit_type=trace_contract.get("db_hit_type"),
    ).model_dump(mode="json")


def _build_diagnosis(
    *,
    north_star_evaluation: dict[str, Any],
    trace_contract: dict[str, Any],
) -> dict[str, Any]:
    failed_layer = north_star_evaluation.get("failed_layer")
    repairability = _repairability_for_layer(failed_layer)
    trace_health = "degraded" if failed_layer else ("watch" if north_star_evaluation.get("win_loss_neutral") == "neutral" else "healthy")
    return TraceDiagnosis(
        failed_layer=failed_layer,
        why=north_star_evaluation.get("why") or "No regression signal detected.",
        repairability=repairability,
        suggested_next_action=_suggested_next_action(failed_layer),
        trace_health=trace_health,
    ).model_dump(mode="json")


def build_trace_envelope(
    *,
    request_id: str,
    user_id: str,
    timestamp: str,
    provider_name: str | None,
    schema_signature: str | None,
    source_page_version: str | None,
    trace_contract: dict[str, Any],
    llm_traces: list[dict[str, Any]],
    debug_steps: list[dict[str, Any]],
    quality_signals: dict[str, Any],
    best_answer_source: str | None,
    retry_triggered: bool,
    multi_turn_context: dict[str, Any],
) -> TraceEnvelope:
    token_usage = compute_token_usage(llm_traces)
    trace_contract["multi_turn_context"] = multi_turn_context
    trace_contract["token_usage"] = token_usage
    north_star_evaluation = evaluate_trace_contract(
        trace_contract,
        quality_signals,
        best_answer_source=best_answer_source,
        retry_triggered=retry_triggered,
    )
    diagnosis = _build_diagnosis(
        north_star_evaluation=north_star_evaluation,
        trace_contract=trace_contract,
    )
    return TraceEnvelope(
        trace_contract=trace_contract,
        multi_turn_context=multi_turn_context,
        token_usage=token_usage,
        north_star_evaluation=north_star_evaluation,
        trace_meta=TraceMeta(
            request_id=request_id,
            user_id=user_id,
            timestamp=timestamp,
            provider=provider_name,
            schema_signature=schema_signature,
            source_page_version=source_page_version,
        ).model_dump(mode="json"),
        span_timeline=_build_span_timeline(
            llm_traces=llm_traces,
            debug_steps=debug_steps,
            trace_contract=trace_contract,
        ),
        decision_journal=_build_decision_journal(
            trace_contract=trace_contract,
            best_answer_source=best_answer_source,
            retry_triggered=retry_triggered,
        ),
        evidence_journal=_build_evidence_journal(
            trace_contract=trace_contract,
            best_answer_source=best_answer_source,
        ),
        diagnosis=diagnosis,
        context_pack_trace=trace_contract.get("context_pack_trace", {}) or {},
        tool_decision_trace=trace_contract.get("tool_decision_trace", {}) or {},
        boundary_trace=trace_contract.get("boundary_trace", {}) or {},
        judge_trace=trace_contract.get("judge_trace", {}) or {},
        evidence_resolution_trace=trace_contract.get("evidence_resolution_trace", {}) or {},
        memory_trace=trace_contract.get("memory_trace", {}) or {},
    )
