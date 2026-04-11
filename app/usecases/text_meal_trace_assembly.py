from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .. import SCHEMA_SIGNATURE
from ..application.context_assembly import build_context_pack_trace
from ..observability.payload_builders import build_trace_contract
from ..observability.text_meal_observability import build_multi_turn_context
from ..schemas import EvidenceResolutionTrace, MemoryTrace, ToolCallRequest, ToolCallResult, ToolDecisionTrace


@dataclass
class FinalizeTraceBundle:
    trace_contract: dict[str, Any]
    trace_envelope: Any


def assemble_finalize_trace_bundle(
    *,
    request: Any,
    effective_request: Any,
    request_id: str,
    planner_result: Any,
    planner_enabled: bool,
    normalization: dict[str, Any],
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
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
    current_parsed: dict[str, Any],
    best_parsed: dict[str, Any],
    best_quality: dict[str, Any],
    best_source: str,
    used_search: bool,
    search_query: str | None,
    retry_triggered: bool,
    retry_reason: str | None,
    evidence_guardrail_prompt: str,
    build_evidence_bundle: Any,
    merge_evidence_items: Any,
    to_evidence_candidate: Any,
    source_class_for_item: Any,
    now_iso: Any,
    build_trace_envelope: Any,
    provider_name: str,
    max_selected_evidence_items: int,
    max_durable_memory_hits: int,
) -> FinalizeTraceBundle:
    selected_titles = [
        str(title).strip()
        for title in [
            *(item.get("title") for item in filtered_knowledge[:max_selected_evidence_items]),
            *(item.get("title") for item in sources[:max_selected_evidence_items]),
        ]
        if str(title or "").strip()
    ]
    evidence_bundle = build_evidence_bundle(
        merge_evidence_items(filtered_knowledge, sources),
        selected_titles=selected_titles,
    )
    executed_tool_names = {item["tool_name"] for item in executed_tool_calls}
    for candidate in candidate_tool_calls:
        if candidate["tool_name"] not in executed_tool_names:
            executed_tool_calls.append(
                {
                    "tool_name": candidate["tool_name"],
                    "status": "skipped" if candidate["tool_name"] != "search_official_nutrition" else ("not_needed" if not used_search else "skipped"),
                    "reason": "Tool remained available but was not needed in the final bounded runtime path.",
                }
            )
    context_pack_trace = build_context_pack_trace(
        state=conversation_state,
        evidence_bundle=evidence_bundle,
        available_tools=available_tools,
        evidence_guardrail_prompt=evidence_guardrail_prompt,
    ).model_dump(mode="json")
    tool_decision_trace = ToolDecisionTrace(
        available_tools=available_tools,
        candidate_tool_calls=[ToolCallRequest(**item) for item in candidate_tool_calls],
        executed_tool_calls=[ToolCallResult(**item) for item in executed_tool_calls],
    ).model_dump(mode="json")
    dropped_evidence = []
    for item in merge_evidence_items(filtered_knowledge, sources):
        if str(item.get("title") or "") not in selected_titles:
            dropped_evidence.append(to_evidence_candidate(item, selected=False, drop_reason="not_selected_for_final_answer"))
    evidence_resolution_trace = EvidenceResolutionTrace(
        local_exact_candidates=[to_evidence_candidate(item) for item in filtered_knowledge if item.get("evidence_role") == "exact_truth"],
        local_anchor_candidates=[to_evidence_candidate(item) for item in filtered_knowledge if item.get("evidence_role") == "ingredient_anchor"],
        search_candidates=[to_evidence_candidate(item) for item in sources if source_class_for_item(item) == "web_search_official"],
        doc_read_fragments=[to_evidence_candidate(item) for item in doc_read_fragments],
        final_kept_evidence=[
            to_evidence_candidate(item, selected=True)
            for item in merge_evidence_items(filtered_knowledge, sources)
            if str(item.get("title") or "") in selected_titles
        ],
        dropped_evidence=dropped_evidence,
    ).model_dump(mode="json")
    memory_trace = MemoryTrace(
        durable_memory_enabled=True,
        hits=[hit.model_dump(mode="json") for hit in conversation_state.durable_memory_hits[:max_durable_memory_hits]],
        write_candidates=[
            {
                "memory_type": "correction",
                "value": conversation_state.conversation_digest.last_explicit_correction,
                "trigger": "explicit_transcript_correction",
            }
        ] if conversation_state.conversation_digest.last_explicit_correction else [],
    ).model_dump(mode="json")
    memory_trace["pruned_due_to_budget"] = False
    multi_turn_context = build_multi_turn_context(
        state=conversation_state,
        planner_intent=planner_result.intent,
        context_snapshot=context_str,
        retrieval_query_rewritten=False,
        original_retrieval_query=retrieval_query,
        effective_retrieval_query=retrieval_query,
    )
    trace_contract = build_trace_contract(
        request=request,
        effective_request=effective_request,
        planner_result=planner_result,
        planner_enabled=planner_enabled,
        normalization=normalization,
        risk_packet=risk_packet,
        meal_template=meal_template,
        template_override_blocked=False,
        retrieval_query=retrieval_query,
        retrieved_knowledge=filtered_knowledge,
        sources=sources,
        used_search=used_search,
        search_query=search_query,
        current_parsed=current_parsed,
        best_parsed=best_parsed,
        best_source=best_source,
        quality_signals=best_quality,
        retry_triggered=retry_triggered,
        retry_reason=retry_reason,
        context_pack_trace=context_pack_trace,
        tool_decision_trace=tool_decision_trace,
        boundary_trace=boundary_trace,
        judge_trace=judge_trace,
        evidence_resolution_trace=evidence_resolution_trace,
        memory_trace=memory_trace,
    )
    trace_envelope = build_trace_envelope(
        request_id=request_id,
        user_id=getattr(request, "user_id", "anonymous"),
        timestamp=now_iso(),
        provider_name=provider_name,
        schema_signature=SCHEMA_SIGNATURE,
        source_page_version=None,
        trace_contract=trace_contract,
        llm_traces=llm_traces,
        debug_steps=debug_steps,
        quality_signals=best_quality,
        best_answer_source=best_source,
        retry_triggered=retry_triggered,
        multi_turn_context=multi_turn_context,
    )
    return FinalizeTraceBundle(trace_contract=trace_contract, trace_envelope=trace_envelope)
