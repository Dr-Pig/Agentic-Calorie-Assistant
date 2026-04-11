from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..agent.knowledge_packets import build_gate_packet, match_meal_template
from ..agent.nutrition_resolution_llm import augment_followup_metadata
from ..application.answer_support import (
    evaluate_answer as _evaluate_answer,
    final_best_answer_source as _final_best_answer_source,
)
from ..application.context_assembly import normalize_text as _normalize_text
from ..application.evidence_assembly import tool_availability as _tool_availability
from ..application.state_transition import canonical_meal_state_from_runtime as application_canonical_meal_state_from_runtime
from ..logging import now_iso
from ..observability.text_meal_observability import build_trace_envelope
from ..providers.builderspace_adapter import BuilderSpaceResponseError
from .text_meal_boundary_support import maybe_handle_boundary_clarification
from .text_meal_finalize_support import finalize_text_meal_payload
from .text_meal_nutrition_support import run_nutrition_resolution_loop
from .text_meal_planner_support import run_planner_orchestration
from .text_meal_runtime_support import prepare_initial_grounding, run_decision_stage
from .text_meal_stage_support import debug_step, trace_with_request_id
from .text_meal_trace_support import build_api_fallback_payload

PLANNER_MAX_TOKENS = 2048
PRIMARY_MAX_TOKENS = 8192
MAX_SELECTED_EVIDENCE_ITEMS = 5
MAX_DURABLE_MEMORY_HITS = 3

EVIDENCE_SOURCE_GUARDRAIL_PROMPT = """
Evidence hierarchy rules:
- Treat local exact truth as the strongest source when it is a high-confidence same-item match.
- Web search may only supplement the same item with official nutrition evidence. It may not replace, broaden, or downgrade a strong local exact truth hit.
- If search evidence conflicts with a strong local exact truth hit, keep the local exact truth and ignore the conflicting search value.
- Do not convert same-brand, same-category, or near-name search results into exact item truth.
- If identity is weak, stay conservative and prefer follow-up or uncertainty over forced exactness.
"""


@dataclass
class OrchestrationOutcome:
    payload: Any
    planner_result: Any


async def execute_text_meal_orchestration(
    *,
    request: Any,
    request_id: str,
    runtime_context: Any,
    search_adapter: Any | None,
    db: Any,
    run_stage: Any,
    pass_envelope: Any,
    build_evidence_bundle: Any,
    merge_evidence_items: Any,
    source_class_for_item: Any,
    to_evidence_candidate: Any,
) -> OrchestrationOutcome:
    debug_steps: list[dict[str, Any]] = []
    llm_traces: list[dict[str, Any]] = []

    planner_outcome = await run_planner_orchestration(
        request=request,
        request_id=request_id,
        conversation_state=runtime_context.conversation_state,
        latest_log=runtime_context.latest_log,
        context_str=runtime_context.context_str,
        planner_llm=runtime_context.planner_llm,
        normalize_text=_normalize_text,
        pass_envelope=pass_envelope,
        run_stage=run_stage,
        llm_traces=llm_traces,
        debug_steps=debug_steps,
    )
    planner_result = planner_outcome.planner_result
    task_meal_link_result = planner_outcome.task_meal_link_result
    planner_enabled = planner_outcome.planner_enabled
    effective_request = planner_outcome.effective_request
    boundary_trace = planner_outcome.boundary_trace
    normalization = planner_outcome.normalization
    risk_packet = build_gate_packet(effective_request.text)

    if planner_result.planning_brief.risk_focus:
        risk_packet = {**risk_packet, "planner_risk_focus": planner_result.planning_brief.risk_focus}
    debug_steps.append(debug_step(request_id, step="risk_gate", risk_packet=risk_packet))

    meal_template = match_meal_template(effective_request.text, risk_packet)
    debug_steps.append(
        debug_step(
            request_id,
            step="meal_template_match",
            matched=bool(meal_template),
            template_id=meal_template.get("template_id") if meal_template else None,
            template_title=meal_template.get("title") if meal_template else None,
        )
    )

    boundary_payload = maybe_handle_boundary_clarification(
        task_meal_link_result=task_meal_link_result,
        request=request,
        effective_request=effective_request,
        request_id=request_id,
        planner_result=planner_result,
        planner_enabled=planner_enabled,
        conversation_state=runtime_context.conversation_state,
        context_str=runtime_context.context_str,
        boundary_trace=boundary_trace,
        risk_packet=risk_packet,
        meal_template=meal_template,
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        available_tools=_tool_availability(request, search_adapter=search_adapter),
        evidence_guardrail_prompt=EVIDENCE_SOURCE_GUARDRAIL_PROMPT,
        db=db,
        user=runtime_context.user,
        latest_log=runtime_context.latest_log,
        incoming_user_message_id=runtime_context.incoming_user_message_id,
    )
    if boundary_payload is not None:
        return OrchestrationOutcome(payload=boundary_payload, planner_result=planner_result)

    canonical_meal_state = application_canonical_meal_state_from_runtime(
        latest_log=runtime_context.latest_log,
        state=runtime_context.conversation_state,
        normalize_text=_normalize_text,
    )

    try:
        grounding_state = prepare_initial_grounding(
            effective_user_input=effective_request.text,
            planner_result=planner_result,
            request=request,
            search_adapter=search_adapter,
            max_selected_evidence_items=MAX_SELECTED_EVIDENCE_ITEMS,
        )
        retrieval_triggered = grounding_state.retrieval_triggered
        retrieval_query = grounding_state.retrieval_query
        available_tools = grounding_state.available_tools
        candidate_tool_calls = grounding_state.candidate_tool_calls
        executed_tool_calls = grounding_state.executed_tool_calls
        doc_read_fragments = grounding_state.doc_read_fragments
        filtered_knowledge = list(grounding_state.filtered_knowledge)
        normalized_evidence = list(grounding_state.normalized_evidence)
        partial_grounding = dict(grounding_state.partial_grounding)
        local_exact_truth_present = grounding_state.local_exact_truth_present

        if retrieval_triggered:
            debug_steps.append(
                debug_step(
                    request_id,
                    step="local_retrieval",
                    retrieval_query=retrieval_query,
                    result_count=len(grounding_state.retrieved_knowledge),
                )
            )

        decision_outcome = await run_decision_stage(
            primary_llm=runtime_context.primary_llm,
            request_id=request_id,
            effective_user_input=effective_request.text,
            canonical_meal_state=canonical_meal_state,
            task_meal_link_result=task_meal_link_result,
            planner_result=planner_result,
            filtered_knowledge=filtered_knowledge,
            available_tools=available_tools,
            local_exact_truth_present=local_exact_truth_present,
            request=request,
            search_adapter=search_adapter,
            executed_tool_calls=executed_tool_calls,
            normalized_evidence=normalized_evidence,
            partial_grounding=partial_grounding,
            run_stage=run_stage,
            llm_traces=llm_traces,
            debug_steps=debug_steps,
            planner_max_tokens=PLANNER_MAX_TOKENS,
        )
        decision_result = decision_outcome.decision_result
        selected_evidence_for_primary = decision_outcome.selected_evidence_for_primary
        normalized_evidence = decision_outcome.normalized_evidence
        partial_grounding = decision_outcome.partial_grounding
        sources = decision_outcome.sources
        used_search = decision_outcome.used_search
        search_query = decision_outcome.search_query
        search_quality = decision_outcome.search_quality

        planner_result = planner_result.model_copy(
            update={
                "meal_boundary": (
                    "continue_active_meal"
                    if task_meal_link_result.meal_link_action == "attach_to_existing_meal"
                    else "boundary_clarification"
                    if task_meal_link_result.meal_link_action == "boundary_ambiguous"
                    else "start_new_meal"
                )
            }
        )

        nutrition_outcome = await run_nutrition_resolution_loop(
            primary_llm=runtime_context.primary_llm,
            request_id=request_id,
            effective_user_input=effective_request.text,
            request=request,
            planner_result=planner_result,
            task_meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            canonical_meal_state=canonical_meal_state,
            risk_packet=risk_packet,
            meal_template=meal_template,
            available_tools=available_tools,
            latest_log=runtime_context.latest_log,
            active_meal_context_allowed=task_meal_link_result.meal_link_action == "attach_to_existing_meal",
            local_exact_truth_present=local_exact_truth_present,
            retrieval_query=retrieval_query,
            selected_evidence_for_primary=selected_evidence_for_primary,
            normalized_evidence=normalized_evidence,
            partial_grounding=partial_grounding,
            sources=sources,
            used_search=used_search,
            search_query=search_query,
            search_quality=search_quality,
            llm_traces=llm_traces,
            debug_steps=debug_steps,
            executed_tool_calls=executed_tool_calls,
            run_stage=run_stage,
            search_adapter=search_adapter,
            primary_max_tokens=PRIMARY_MAX_TOKENS,
        )
        current_parsed = nutrition_outcome.current_parsed
        nutrition_result = nutrition_outcome.nutrition_result
        used_search = nutrition_outcome.used_search
        search_query = nutrition_outcome.search_query
        search_quality = nutrition_outcome.search_quality
        sources = nutrition_outcome.sources
        current_private = nutrition_outcome.current_private

        best_quality = _evaluate_answer(current_parsed, risk_packet, None)
        best_quality["invalid_zero_kcal_candidate"] = current_parsed["estimated_kcal"] <= 0
        best_parsed = augment_followup_metadata(current_parsed)
        best_source = _final_best_answer_source("primary", best_parsed)

        payload = await finalize_text_meal_payload(
            primary_llm=runtime_context.primary_llm,
            request=request,
            effective_request=effective_request,
            request_id=request_id,
            planner_result=planner_result,
            planner_enabled=planner_enabled,
            normalization=normalization,
            risk_packet=risk_packet,
            meal_template=meal_template,
            retrieval_triggered=retrieval_triggered,
            retrieval_query=retrieval_query,
            filtered_knowledge=filtered_knowledge,
            sources=sources,
            available_tools=available_tools,
            candidate_tool_calls=candidate_tool_calls,
            executed_tool_calls=executed_tool_calls,
            doc_read_fragments=doc_read_fragments,
            conversation_state=runtime_context.conversation_state,
            context_str=runtime_context.context_str,
            boundary_trace=boundary_trace,
            judge_trace={},
            debug_steps=debug_steps,
            llm_traces=llm_traces,
            best_parsed=best_parsed,
            current_parsed=current_parsed,
            best_quality=best_quality,
            best_private=current_private,
            best_source=best_source,
            used_search=used_search,
            search_query=search_query,
            search_quality=search_quality,
            retry_triggered=False,
            retry_reason=None,
            evidence_guardrail_prompt=EVIDENCE_SOURCE_GUARDRAIL_PROMPT,
            build_evidence_bundle=build_evidence_bundle,
            merge_evidence_items=merge_evidence_items,
            to_evidence_candidate=to_evidence_candidate,
            source_class_for_item=source_class_for_item,
            now_iso=now_iso,
            build_trace_envelope=build_trace_envelope,
            task_meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            nutrition_result=nutrition_result,
            max_selected_evidence_items=MAX_SELECTED_EVIDENCE_ITEMS,
            max_durable_memory_hits=MAX_DURABLE_MEMORY_HITS,
            max_tokens=PRIMARY_MAX_TOKENS,
            run_stage=run_stage,
        )
        return OrchestrationOutcome(payload=payload, planner_result=planner_result)
    except BuilderSpaceResponseError as exc:
        llm_traces.append(trace_with_request_id(exc.trace, request_id))
        fallback_payload = build_api_fallback_payload(
            effective_request=effective_request,
            request_id=request_id,
            request_text=request.text,
            risk_packet=risk_packet,
            debug_steps=debug_steps,
            llm_traces=llm_traces,
        )
        return OrchestrationOutcome(payload=fallback_payload, planner_result=planner_result)
