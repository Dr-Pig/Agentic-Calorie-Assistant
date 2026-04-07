from __future__ import annotations

from typing import Any

from .. import SCHEMA_SIGNATURE
from ..agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from ..agent.decision_llm import DECISION_PROMPT, fallback_decision_result, normalize_decision_result
from ..agent.final_response_llm import run_four_pass_final_response
from ..agent.knowledge_packets import build_gate_packet, match_meal_template, resolve_exact_item, resolve_ingredient_anchors
from ..agent.nutrition_resolution_llm import (
    NUTRITION_RESOLUTION_PROMPT,
    augment_followup_metadata,
    normalize_structured_answer as _normalize_structured_answer,
    nutrition_result_from_primary,
)
from ..agent.task_meal_link_llm import (
    TASK_MEAL_LINK_PROMPT,
    fallback_task_meal_link_result,
    normalize_task_meal_link_result,
)
from ..application.answer_support import (
    boundary_followup_question as _boundary_followup_question,
    evaluate_answer as _evaluate_answer,
    final_best_answer_source as _final_best_answer_source,
    is_private_only_case as _is_private_only_case,
    meal_template_context as _meal_template_context,
)
from ..application.context_assembly import (
    build_boundary_features as application_build_boundary_features,
    build_context_pack_trace as _build_context_pack_trace,
    build_decision_payload,
    build_nutrition_resolution_payload,
    build_task_meal_link_payload,
    calibration_context as _calibration_context,
    knowledge_context as _knowledge_context,
    normalize_text as _normalize_text,
    normalize_user_input_for_estimation as _normalize_user_input_for_estimation,
    normalized_input_from_debug_steps as _normalized_input_from_debug_steps,
    render_conversation_state_prompt,
    risk_context as _risk_context,
)
from ..application.evidence_assembly import (
    build_evidence_bundle as _build_evidence_bundle,
    build_partial_grounding_packet,
    build_tool_candidate_requests as _build_tool_candidate_requests,
    build_tool_result as _build_tool_result,
    compose_decision_lookup_query,
    execute_primary_tool_request,
    infer_expected_components,
    merge_evidence_items as _merge_evidence_items,
    normalize_tool_evidence,
    pre_rank_evidence_items as _pre_rank_evidence_items,
    retrieval_query_is_usable as _retrieval_query_is_usable,
    source_class_for_item as _source_class_for_item,
    summarize_selected_evidence,
    tool_availability as _tool_availability,
    to_evidence_candidate as _to_evidence_candidate,
)
from ..application.nutrition_invariants import apply_nutrition_invariant_guards
from ..application.pass_runner import run_pass
from ..application.planner import (
    ensure_planning_brief_model as application_ensure_planning_brief_model,
    fallback_planner_result as application_fallback_planner_result,
    planner_enabled as application_planner_enabled,
)
from ..application.state_transition import (
    active_meal_context_allowed as _active_meal_context_allowed,
    build_boundary_trace as application_build_boundary_trace,
    canonical_meal_state_from_runtime as application_canonical_meal_state_from_runtime,
)
from ..domain import ConversationState
from ..infrastructure.conversation_state_loader import load_conversation_state
from ..infrastructure.meal_log_persistence import persist_text_meal_result
from ..logging import append_audit_event, now_iso, write_request_trace_artifact
from ..observability.payload_builders import (
    build_payload as _build_payload,
    build_trace_contract as _build_trace_contract,
    unicode_escape as _unicode_escape,
)
from ..observability.text_meal_observability import build_multi_turn_context, build_trace_envelope
from ..providers.builderspace_adapter import BuilderSpaceResponseError
from ..schemas import (
    AuditEvent,
    EstimatePayload,
    EstimateRequest,
    EvidenceResolutionTrace,
    MemoryTrace,
    NutritionResolutionResult,
    PassExecutionEnvelope,
    ToolCallRequest,
    ToolCallResult,
    ToolDecisionTrace,
)

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

def _trace_with_request_id(trace: dict[str, Any], request_id: str) -> dict[str, Any]:


    return {"request_id": request_id, **(trace or {})}


def _debug_step(request_id: str, **payload: Any) -> dict[str, Any]:


    return {"request_id": request_id, **payload}


async def _run_text_stage(


    provider: Any,


    *,


    stage: str,


    system_prompt: str,


    user_payload: dict[str, Any],


    max_tokens: int,


    attempt_index: int | None = None,


    trigger_reason: str | None = None,


    handoff_contract: dict[str, Any] | None = None,


) -> tuple[dict[str, Any], dict[str, Any]]:


    raw, trace = await provider.complete_with_trace(
        system_prompt=system_prompt,
        user_payload=user_payload,
        stage=stage,
        max_tokens=max_tokens,
    )
    merged_trace = trace or {}
    if attempt_index is not None:
        merged_trace = {"attempt_index": attempt_index, **merged_trace}
    if trigger_reason:
        merged_trace = {"trigger_reason": trigger_reason, **merged_trace}
    if handoff_contract:
        merged_trace = {"handoff_contract": handoff_contract, **merged_trace}
    return raw or {}, merged_trace


def _pass_envelope(*, status: str, payload: dict[str, Any] | None = None, fallback_used: bool = False, error: str | None = None) -> PassExecutionEnvelope:
    return PassExecutionEnvelope(
        status=status,  # type: ignore[arg-type]
        payload=payload or {},
        fallback_used=fallback_used,
        error=error,
    )



async def run_text_meal_canary(
    request: EstimateRequest,
    *,
    provider: Any,
    planner_provider: Any | None = None,
    primary_provider: Any | None = None,
    request_id: str,
    search_adapter: Any | None = None,
    db: Session | None = None,
) -> EstimatePayload:
    debug_steps: list[dict[str, Any]] = []
    llm_traces: list[dict[str, Any]] = []
    thin_sanitized_input = _normalize_text(request.text)
    incoming_user_message_id: int | None = None

    user = None
    latest_log = None
    conversation_state = ConversationState(user_id=request.user_id)
    if db:
        loaded_context = load_conversation_state(db, user_id=request.user_id, incoming_user_text=request.text)
        user = loaded_context.user
        latest_log = loaded_context.latest_log
        conversation_state = loaded_context.state
        if loaded_context.recent_messages and loaded_context.recent_messages[-1].role == "user":
            incoming_user_message_id = loaded_context.recent_messages[-1].id

    context_str = ""
    if conversation_state:
        context_str = render_conversation_state_prompt(conversation_state)
    planner_llm = planner_provider or provider
    primary_llm = primary_provider or provider

    planner_result = application_fallback_planner_result(
        request.text,
        normalize_text=_normalize_text,
        normalize_user_input_for_estimation=_normalize_user_input_for_estimation,
    )
    planner_result = planner_result.model_copy(
        update={"planning_brief": application_ensure_planning_brief_model(planner_result.planning_brief)}
    )
    planner_enabled = application_planner_enabled()
    planner_mode = "disabled"
    boundary_features = application_build_boundary_features(state=conversation_state, latest_log=latest_log)
    meal_log_summaries = [chunk.model_dump(mode="json") for chunk in conversation_state.retrieved_meal_records[:5]]
    fallback_task_link = fallback_task_meal_link_result(
        user_input=request.text,
        planner_result=planner_result,
        latest_log=latest_log,
    )
    task_meal_link_result = fallback_task_link
    task_meal_link_envelope = _pass_envelope(status="failed", payload=fallback_task_link.model_dump(mode="json"), fallback_used=True)

    if planner_enabled:
        planner_mode = "fallback"
        task_meal_link_payload = build_task_meal_link_payload(
            user_input=request.text,
            state=conversation_state,
            meal_log_summaries=meal_log_summaries,
            boundary_features=boundary_features,
        )
        task_meal_link_result, task_meal_link_envelope = await run_pass(
            provider=planner_llm,
            stage="task_meal_link_pass",
            system_prompt=TASK_MEAL_LINK_PROMPT + "\n\n[CONTEXT]\n" + context_str,
            user_payload=task_meal_link_payload,
            max_tokens=PLANNER_MAX_TOKENS,
            fallback_result=fallback_task_link,
            normalize=lambda raw, fallback: normalize_task_meal_link_result(raw, fallback=fallback, state=conversation_state),
            dump=lambda result: result.model_dump(mode="json"),
            run_stage=_run_text_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="task_meal_link",
            handoff_contract={
                "context_snapshot_present": bool(context_str),
                "recent_message_count": len(conversation_state.recent_messages),
                "conversation_archive_hit_count": len(conversation_state.conversation_archive_hits),
                "planner_state_digest_present": bool(conversation_state.planner_state_digest),
            },
            required_fields=["intent", "meal_link_action", "target_meal_id", "clarification_blocking"],
            required_fields_source="normalized",
            nullable_required_fields=["target_meal_id"],
        )
        if task_meal_link_envelope.status == "success":
            planner_mode = "llm"
        else:
            debug_steps.append(
                _debug_step(
                    request_id,
                    step="planner_pass",
                    planner_mode="fallback",
                    planner_error=task_meal_link_envelope.error,
                )
            )
    else:
        debug_steps.append(
            _debug_step(
                request_id,
                step="planner_pass",
                planner_mode="disabled",
                planner_reason="feature_flag_off",
            )
        )

    planner_result = planner_result.model_copy(
        update={
            "intent": "food_estimation" if task_meal_link_result.intent == "food_estimation" else task_meal_link_result.intent,
            "meal_boundary": (
                "continue_active_meal"
                if task_meal_link_result.meal_link_action == "attach_to_existing_meal"
                else "boundary_clarification"
                if task_meal_link_result.meal_link_action == "boundary_ambiguous"
                else "start_new_meal"
            ),
            "active_meal_reference": task_meal_link_result.target_meal_id,
            "boundary_confidence": task_meal_link_result.link_confidence,
            "resolved_query": task_meal_link_result.normalized_user_input or request.text,
            "normalized_user_input": task_meal_link_result.normalized_user_input or request.text,
        }
    )
    effective_request = EstimateRequest(text=task_meal_link_result.normalized_user_input or planner_result.normalized_user_input, allow_search=request.allow_search)
    active_meal_context_allowed = _active_meal_context_allowed(planner_result)
    boundary_trace = application_build_boundary_trace(
        planner_result=planner_result,
        state=conversation_state,
        active_meal_context_allowed=active_meal_context_allowed,
        confidence_signals={},
        downgrade_reasons=[],
    )


    normalization = (


        _normalize_user_input_for_estimation(request.text)


        if planner_result.route_hints.get("planner_source") == "fallback_normalizer"


        else {


            "raw_text": request.text,


            "normalized_text": effective_request.text,


            "normalizer_applied": False,


            "notes": [],


        }


    )


    debug_steps.append(


        _debug_step(


            request_id,


            step="planner_pass",


            planner_mode=planner_mode,


            raw_user_input=request.text,


            thin_sanitized_input=thin_sanitized_input,


            intent=planner_result.intent,
            meal_boundary=planner_result.meal_boundary,
            active_meal_reference=planner_result.active_meal_reference,
            boundary_confidence=planner_result.boundary_confidence,
                planner_self_reported_boundary_confidence=planner_result.boundary_confidence,


            normalized_user_input=effective_request.text,


input_signals=planner_result.input_signals,


            missing_info=planner_result.missing_info,


            route_hints=planner_result.route_hints,


            planning_brief=planner_result.planning_brief.model_dump(mode="json"),


        )


    )


    risk_packet = build_gate_packet(effective_request.text)


    if planner_result.planning_brief.risk_focus:


        risk_packet = {**risk_packet, "planner_risk_focus": planner_result.planning_brief.risk_focus}


    debug_steps.append(_debug_step(request_id, step="risk_gate", risk_packet=risk_packet))


    meal_template = match_meal_template(effective_request.text, risk_packet)


    debug_steps.append(


        _debug_step(


            request_id,


            step="meal_template_match",


            matched=bool(meal_template),


            template_id=meal_template.get("template_id") if meal_template else None,


            template_title=meal_template.get("title") if meal_template else None,


        )


    )


    template_context = _meal_template_context(meal_template)

    if task_meal_link_result.meal_link_action == "boundary_ambiguous" and task_meal_link_result.clarification_blocking:
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
            "followup_question": _boundary_followup_question(),
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
        best_quality = _evaluate_answer(parsed, risk_packet, meal_template)
        available_tools = _tool_availability(request, search_adapter=search_adapter)
        context_pack_trace = _build_context_pack_trace(
            state=conversation_state,
            evidence_bundle=_build_evidence_bundle([], selected_titles=[]),
            available_tools=available_tools,
            evidence_guardrail_prompt=EVIDENCE_SOURCE_GUARDRAIL_PROMPT,
        ).model_dump(mode="json")
        tool_decision_trace = ToolDecisionTrace(
            available_tools=available_tools,
            candidate_tool_calls=[],
            executed_tool_calls=[],
        ).model_dump(mode="json")
        boundary_only_judge_trace = {}
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
        trace_contract = _build_trace_contract(
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
            judge_trace=boundary_only_judge_trace,
            evidence_resolution_trace=evidence_resolution_trace,
            memory_trace=memory_trace,
        )
        payload = _build_payload(
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
            judge_trace=boundary_only_judge_trace,
            evidence_resolution_trace=evidence_resolution_trace,
            memory_trace=memory_trace,
        )
        if db and user:
            persistence_decision = persist_text_meal_result(
                db,
                user=user,
                latest_log=latest_log,
                planner_intent=planner_result.intent,
                payload=payload,
                raw_input=request.text,
                request_id=request_id,
                incoming_user_message_id=incoming_user_message_id,
            )
            payload.trace_contract["persistence_decision"] = persistence_decision
            payload.boundary_trace["boundary_resolution_state"] = "open"
        return payload

    canonical_meal_state = application_canonical_meal_state_from_runtime(
        latest_log=latest_log,
        state=conversation_state,
        normalize_text=_normalize_text,
    )

    try:


        # Knowledge Retrieval (Grounding)


        retrieved_knowledge: list[dict[str, Any]] = []


        retrieval_triggered = False


        retrieval_query = planner_result.resolved_query.strip() or (planner_result.input_signals.get("foods", [effective_request.text])[0] if planner_result.input_signals.get("foods") else effective_request.text)

        # Multi-turn retrieval rewrite: 
        # DEPRECATED: Appending meal_title often adds noise (e.g. brand names) that pollute vector search results.
        # The planner_result.normalized_user_input (effective_request.text) already contains the full context.
        retrieval_query_rewritten = False
        original_retrieval_query = retrieval_query
        available_tools = _tool_availability(request, search_adapter=search_adapter)
        candidate_tool_calls = _build_tool_candidate_requests(
            query=retrieval_query,
            decision_tool_plan="none",
        )
        executed_tool_calls: list[dict[str, Any]] = []
        doc_read_fragments: list[dict[str, Any]] = []


        if planner_result.planning_brief.evidence_strategy != "clarify_before_grounding" and _retrieval_query_is_usable(retrieval_query):


            retrieval_triggered = True


            exact_candidates = resolve_exact_item(retrieval_query, limit=4)
            fallback_component_list = infer_expected_components(
                user_input=effective_request.text,
                planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
            )
            anchor_component_list = list(
                dict.fromkeys((planner_result.input_signals.get("foods") or []) or fallback_component_list or [effective_request.text])
            )
            anchor_candidates = resolve_ingredient_anchors(
                anchor_component_list,
                portion_hints=planner_result.input_signals.get("portion_clues", []),
                limit=max(6, len(anchor_component_list)),
            )
            retrieved_knowledge = _merge_evidence_items(exact_candidates, anchor_candidates)
            executed_tool_calls.append(
                _build_tool_result(
                    tool_name="resolve_exact_item",
                    status="executed",
                    reason="Local exact-item resolver executed for bounded candidate retrieval.",
                    result_count=len(exact_candidates),
                    quality="high" if any(item.get("identity_confidence") == "high" for item in exact_candidates) else ("medium" if exact_candidates else "low"),
                )
            )
            executed_tool_calls.append(
                _build_tool_result(
                    tool_name="resolve_ingredient_anchors",
                    status="executed",
                    reason="Ingredient anchor resolver executed for bounded candidate retrieval.",
                    result_count=len(anchor_candidates),
                    quality="medium" if anchor_candidates else "low",
                )
            )


            debug_steps.append(_debug_step(request_id, step="local_retrieval", retrieval_query=retrieval_query, result_count=len(retrieved_knowledge)))



        filtered_knowledge = list(retrieved_knowledge)
        ranked_local_candidates = _pre_rank_evidence_items(filtered_knowledge, query=retrieval_query, limit=5)
        judge_trace = {}
        filtered_knowledge = ranked_local_candidates[:MAX_SELECTED_EVIDENCE_ITEMS]
        local_exact_truth_present = any(str(item.get("evidence_role") or "") == "exact_truth" for item in filtered_knowledge)
        dropped_evidence_summary = [
            _to_evidence_candidate(item, selected=False, drop_reason="not_selected_for_primary")
            for item in ranked_local_candidates
            if str(item.get("title") or "").strip() not in {str(sel.get("title") or "").strip() for sel in filtered_knowledge}
        ]
        normalized_evidence = normalize_tool_evidence(
            filtered_knowledge,
            source_type="local_retrieval",
            query=retrieval_query,
            limit=MAX_SELECTED_EVIDENCE_ITEMS,
        )
        partial_grounding = build_partial_grounding_packet(
            user_input=effective_request.text,
            planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
            selected_evidence=filtered_knowledge,
        )
        fallback_decision = fallback_decision_result(meal_link_result=task_meal_link_result)
        decision_result = fallback_decision
        decision_envelope = _pass_envelope(status="failed", payload=fallback_decision.model_dump(mode="json"), fallback_used=True)
        decision_payload = build_decision_payload(
            user_input=effective_request.text,
            meal_state=canonical_meal_state,
            meal_link_result=task_meal_link_result,
            selected_evidence_summary=summarize_selected_evidence(filtered_knowledge),
            available_tools=available_tools,
            planning_brief=planner_result.planning_brief,
        )
        decision_result, decision_envelope = await run_pass(
            provider=primary_llm,
            stage="decision_pass",
            system_prompt=DECISION_PROMPT,
            user_payload=decision_payload,
            max_tokens=PLANNER_MAX_TOKENS,
            fallback_result=fallback_decision,
            normalize=lambda raw, fallback: normalize_decision_result(raw, fallback=fallback),
            dump=lambda result: result.model_dump(mode="json"),
            run_stage=_run_text_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="decision_pass",
            handoff_contract={
                "meal_link_action": task_meal_link_result.meal_link_action,
                "target_meal_id": task_meal_link_result.target_meal_id,
                "selected_evidence_count": len(filtered_knowledge),
            },
            required_fields=["next_action", "tool_plan", "clarify_is_blocking", "can_proceed_without_clarify"],
            required_fields_source="normalized",
            nullable_required_fields=["clarify_priority"],
        )
        if decision_envelope.status != "success":
            debug_steps.append(_debug_step(request_id, step="decision_pass", error=decision_envelope.error))

        sources: list[dict[str, Any]] = []
        used_search = False
        search_query, search_quality = None, None
        current_parsed: dict[str, Any] = {}
        current_private = False
        selected_evidence_for_primary = filtered_knowledge
        nutrition_result: NutritionResolutionResult | None = None
        active_meal_context_allowed = task_meal_link_result.meal_link_action == "attach_to_existing_meal"
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

        if (
            decision_result.next_action == "run_tool_lookup"
            and decision_result.tool_plan != "none"
            and not (
                local_exact_truth_present
                and decision_result.tool_plan in {"search_official_nutrition", "read_official_doc_fragment"}
            )
        ):
            decision_tool_query = str(getattr(decision_result, "tool_query_override", "") or "").strip() or compose_decision_lookup_query(
                current_user_input=effective_request.text,
                meal_title=canonical_meal_state.meal_title if canonical_meal_state else None,
                meal_link_action=task_meal_link_result.meal_link_action,
                resolved_query=planner_result.resolved_query,
                retrieval_query=retrieval_query,
            )
            tool_evidence, search_sources, search_query, search_quality = await execute_primary_tool_request(
                tool_request=decision_result.tool_plan,
                tool_reason="Decision pass requested tool lookup before nutrition resolution.",
                retrieval_query=decision_tool_query,
                resolved_query=decision_tool_query,
                planner_result=planner_result,
                request=request,
                search_adapter=search_adapter,
                executed_tool_calls=executed_tool_calls,
                build_tool_result=_build_tool_result,
            )
            if search_sources:
                used_search = True
                sources = _merge_evidence_items(sources, search_sources)
            if tool_evidence:
                selected_evidence_for_primary = _merge_evidence_items(selected_evidence_for_primary, tool_evidence)
                normalized_evidence = [
                    *normalized_evidence,
                    *normalize_tool_evidence(tool_evidence, source_type=decision_result.tool_plan, query=search_query or decision_tool_query),
                ]
                partial_grounding = build_partial_grounding_packet(
                    user_input=effective_request.text,
                    planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
                    selected_evidence=selected_evidence_for_primary,
                )
            debug_steps.append(
                _debug_step(
                    request_id,
                    step="decision_tool_lookup",
                    tool_plan=decision_result.tool_plan,
                    query=decision_tool_query,
                    tool_hit_count=len(tool_evidence),
                    search_hit_count=len(search_sources),
                )
            )

        if (
            decision_result.next_action == "run_nutrition_resolution"
            and not local_exact_truth_present
            and bool(partial_grounding.get("search_recommended"))
            and search_adapter is not None
            and request.allow_search
        ):
            partial_grounding_query = str(partial_grounding.get("suggested_search_query") or "").strip() or retrieval_query
            tool_evidence, search_sources, search_query, search_quality = await execute_primary_tool_request(
                tool_request="search_official_nutrition",
                tool_reason="Partial grounding indicated missing high-importance components before nutrition resolution.",
                retrieval_query=partial_grounding_query,
                resolved_query=partial_grounding_query,
                planner_result=planner_result,
                request=request,
                search_adapter=search_adapter,
                executed_tool_calls=executed_tool_calls,
                build_tool_result=_build_tool_result,
            )
            if search_sources:
                used_search = True
                sources = _merge_evidence_items(sources, search_sources)
            if tool_evidence:
                selected_evidence_for_primary = _merge_evidence_items(selected_evidence_for_primary, tool_evidence)
                normalized_evidence = [
                    *normalized_evidence,
                    *normalize_tool_evidence(
                        tool_evidence,
                        source_type="search_official_nutrition",
                        query=search_query or partial_grounding_query,
                    ),
                ]
                partial_grounding = build_partial_grounding_packet(
                    user_input=effective_request.text,
                    planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
                    selected_evidence=selected_evidence_for_primary,
                )
            debug_steps.append(
                _debug_step(
                    request_id,
                    step="partial_grounding_search",
                    query=partial_grounding_query,
                    tool_hit_count=len(tool_evidence),
                    search_hit_count=len(search_sources),
                )
            )

        if decision_result.next_action == "run_clarify" and not decision_result.can_proceed_without_clarify:
            current_parsed = {
                "action_taken": "clarify_before_estimate",
                "confidence": "low",
                "exactness": "unknown",
                "tool_request": "none",
                "tool_request_reason": "",
                "title": str(canonical_meal_state.meal_title if canonical_meal_state else effective_request.text),
                "components": [],
                "protein_g": 0,
                "carb_g": 0,
                "fat_g": 0,
                "estimated_kcal": 0,
                "uncertainty_factors": list(decision_result.unresolved_info or ["meal_boundary"]),
                "follow_up_needed": True,
                "follow_up_reasoning": "Decision pass marked clarification as blocking.",
                "unresolved_info": list(decision_result.unresolved_info or ["meal_boundary"]),
                "response_mode_hint": "clarify_first",
                "state_transition_hint": "draft_unresolved",
                "answer_payload": {},
            }
            nutrition_result = NutritionResolutionResult(
                resolution_mode="cannot_estimate_yet",
                resolution_basis="component_model",
                confidence="low",
                exactness="unknown",
                answer_payload={},
                unresolved_info=current_parsed["unresolved_info"],
                state_transition_hint="draft_unresolved",
            )

        for round_index in range(2):
            if (
                nutrition_result is not None
                and nutrition_result.resolution_mode == "cannot_estimate_yet"
                and str(current_parsed.get("action_taken") or "") != "request_tool"
            ):
                break
            evidence_context = _knowledge_context(selected_evidence_for_primary)
            _cal_packet_id = suggest_calibration_packet(effective_request.text)
            calibration_packet = get_meal_calibration(_cal_packet_id) if _cal_packet_id else None
            nutrition_payload = build_nutrition_resolution_payload(
                meal_state=canonical_meal_state,
                meal_link_result=task_meal_link_result,
                decision_result=decision_result,
                normalized_evidence=normalized_evidence,
                calibration_packet=calibration_packet,
                user_input=effective_request.text,
                partial_grounding=partial_grounding,
            )
            nutrition_payload["user_input"] = effective_request.text
            nutrition_payload["available_tools"] = available_tools
            nutrition_payload["risk_packet"] = risk_packet
            selected_evidence_summary = summarize_selected_evidence(selected_evidence_for_primary)
            if nutrition_payload.get("generic_drink_packaged_refs"):
                selected_evidence_summary = [
                    item
                    for item in selected_evidence_summary
                    if not (
                        str(item.get("evidence_role") or "") == "exact_truth"
                        and str(item.get("source_class") or "") == "exact_item_db"
                    )
                ]
            nutrition_payload["selected_evidence_summary"] = selected_evidence_summary
            nutrition_payload["active_meal_context_allowed"] = active_meal_context_allowed
            nutrition_payload["old_components"] = (
                list(getattr(latest_log, "components_json", None) or [])
                if latest_log is not None and active_meal_context_allowed
                else []
            )
            fallback_primary_parsed = augment_followup_metadata(
                _normalize_structured_answer(
                    None,
                    user_text=effective_request.text,
                    risk_packet=risk_packet,
                    meal_template=meal_template,
                )
            )
            current_parsed, nutrition_envelope = await run_pass(
                provider=primary_llm,
                stage="nutrition_resolution_pass_initial" if round_index == 0 else "nutrition_resolution_pass_tool_round_2",
                system_prompt=NUTRITION_RESOLUTION_PROMPT + "\n\n[EVIDENCE_CONTEXT]\n" + evidence_context + "\n\n[CALIBRATION_CONTEXT]\n" + _calibration_context(calibration_packet) + "\n\n[RISK_CONTEXT]\n" + _risk_context(risk_packet),
                user_payload=nutrition_payload,
                max_tokens=PRIMARY_MAX_TOKENS,
                fallback_result=fallback_primary_parsed,
                normalize=lambda raw, fallback: augment_followup_metadata(
                    _normalize_structured_answer(
                        raw,
                        user_text=effective_request.text,
                        risk_packet=risk_packet,
                        meal_template=meal_template,
                    )
                ),
                dump=lambda result: dict(result),
                run_stage=_run_text_stage,
                request_id=request_id,
                llm_traces=llm_traces,
                trigger_reason="nutrition_resolution" if round_index == 0 else "nutrition_tool_iteration",
                handoff_contract={
                    "meal_link_action": task_meal_link_result.meal_link_action,
                    "decision_next_action": decision_result.next_action,
                    "evidence_count": len(selected_evidence_for_primary),
                    "normalized_evidence_count": len(normalized_evidence),
                },
                required_fields=["action_taken", "response_mode_hint"],
                required_fields_source="normalized",
            )
            if nutrition_envelope.status != "success":
                debug_steps.append(
                    _debug_step(
                        request_id,
                        step="nutrition_resolution_pass",
                        stage="nutrition_resolution_pass_initial" if round_index == 0 else "nutrition_resolution_pass_tool_round_2",
                        status=nutrition_envelope.status,
                        error=nutrition_envelope.error,
                    )
                )
            nutrition_result = nutrition_result_from_primary(
                {
                    **current_parsed,
                    "answer_payload": {
                        **dict(current_parsed.get("answer_payload") or {}),
                        "title": dict(current_parsed.get("answer_payload") or {}).get("title") or current_parsed.get("title"),
                        "components": dict(current_parsed.get("answer_payload") or {}).get("components") or current_parsed.get("components", []),
                        "estimated_kcal": dict(current_parsed.get("answer_payload") or {}).get("estimated_kcal", current_parsed.get("estimated_kcal", 0)),
                        "protein_g": dict(current_parsed.get("answer_payload") or {}).get("protein_g", current_parsed.get("protein_g", 0)),
                        "carb_g": dict(current_parsed.get("answer_payload") or {}).get("carb_g", current_parsed.get("carb_g", 0)),
                        "fat_g": dict(current_parsed.get("answer_payload") or {}).get("fat_g", current_parsed.get("fat_g", 0)),
                        "uncertainty_factors": dict(current_parsed.get("answer_payload") or {}).get("uncertainty_factors", current_parsed.get("uncertainty_factors", [])),
                        "base_estimated_kcal": dict(current_parsed.get("answer_payload") or {}).get("base_estimated_kcal", current_parsed.get("base_estimated_kcal")),
                        "base_protein_g": dict(current_parsed.get("answer_payload") or {}).get("base_protein_g", current_parsed.get("base_protein_g")),
                        "base_carb_g": dict(current_parsed.get("answer_payload") or {}).get("base_carb_g", current_parsed.get("base_carb_g")),
                        "base_fat_g": dict(current_parsed.get("answer_payload") or {}).get("base_fat_g", current_parsed.get("base_fat_g")),
                        "portion_multiplier": dict(current_parsed.get("answer_payload") or {}).get("portion_multiplier", current_parsed.get("portion_multiplier", 1.0)),
                        "portion_reason": dict(current_parsed.get("answer_payload") or {}).get("portion_reason", current_parsed.get("portion_reason", "")),
                        "items": dict(current_parsed.get("answer_payload") or {}).get("items", []),
                    },
                }
            )
            nutrition_result, nutrition_guard_meta = apply_nutrition_invariant_guards(
                result=nutrition_result,
                normalized_evidence=normalized_evidence,
            )
            current_parsed["answer_payload"] = dict(nutrition_result.answer_payload or {})
            current_parsed["title"] = nutrition_result.answer_payload.get("title") or current_parsed.get("title")
            current_parsed["estimated_kcal"] = int(nutrition_result.answer_payload.get("estimated_kcal") or 0)
            current_parsed["protein_g"] = int(nutrition_result.answer_payload.get("protein_g") or 0)
            current_parsed["carb_g"] = int(nutrition_result.answer_payload.get("carb_g") or 0)
            current_parsed["fat_g"] = int(nutrition_result.answer_payload.get("fat_g") or 0)
            current_parsed["unresolved_info"] = list(nutrition_result.unresolved_info or [])
            current_parsed["state_transition_hint"] = nutrition_result.state_transition_hint
            debug_steps.append(_debug_step(request_id, step="nutrition_invariant_guard", **nutrition_guard_meta))
            current_private = _is_private_only_case(current_parsed, risk_packet, effective_request.text)

            if current_parsed.get("action_taken") != "request_tool":
                break

            requested_tool = str(current_parsed.get("tool_request") or "none")
            if local_exact_truth_present and requested_tool in {"search_official_nutrition", "read_official_doc_fragment"}:
                current_parsed["tool_request"] = "none"
                requested_tool = "none"
            if requested_tool == "none":
                # No tool requested ??break and let final_response handle routing
                break

            # Execute the tool (up to 2 rounds: round 0 and round 1)
            # The loop limit range(2) naturally ends after round 1, so we don't need
            # to break on round_index >= 1 here ??execute first, then let loop end naturally.
            tool_evidence, search_sources, search_query, search_quality = await execute_primary_tool_request(
                tool_request=requested_tool,
                tool_reason=str(current_parsed.get("tool_request_reason") or ""),
                retrieval_query=retrieval_query,
                resolved_query=planner_result.resolved_query,
                planner_result=planner_result,
                request=request,
                search_adapter=search_adapter,
                executed_tool_calls=executed_tool_calls,
                build_tool_result=_build_tool_result,
            )
            if search_sources:
                used_search = True
                sources = _merge_evidence_items(sources, search_sources)
            if not tool_evidence:
                # Tool returned no evidence ??do not override LLM's action.
                # Let the loop break and allow final_response to handle routing.
                break

            selected_evidence_for_primary = _merge_evidence_items(selected_evidence_for_primary, tool_evidence)
            normalized_evidence = [
                *normalized_evidence,
                *normalize_tool_evidence(tool_evidence, source_type=requested_tool, query=search_query or retrieval_query),
            ]
            partial_grounding = build_partial_grounding_packet(
                user_input=effective_request.text,
                planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
                selected_evidence=selected_evidence_for_primary,
            )

        quality = _evaluate_answer(current_parsed, risk_packet, None)
        quality["invalid_zero_kcal_candidate"] = current_parsed["estimated_kcal"] <= 0

        best_source = "primary"
        best_parsed = current_parsed
        best_quality = quality
        best_private = current_private
        quality = _evaluate_answer(current_parsed, risk_packet, None)


        quality["invalid_zero_kcal_candidate"] = current_parsed["estimated_kcal"] <= 0


        best_source = "primary"
        best_parsed = current_parsed
        best_quality = quality
        best_private = current_private





        # Retry disabled for LLM-first debugging. Preserve the primary output path
        # instead of letting a second pass reshape follow-up or semantic intent.
        retry_triggered, retry_reason = False, None





        best_parsed = augment_followup_metadata(best_parsed)
        planner_requires_clarify = planner_result.meal_boundary == "boundary_clarification"


        


        # Quality Rescue (Safety Net)


        # --- ????????手?????圈 ---
        # ??? failure_family ?????仿????頦??蝞??蝛??憌?LLM-first ?賤??Prompt ??????
        pass





        requires_follow_up = (
            planner_requires_clarify
            or bool(best_parsed.get("follow_up_needed"))
            or str(best_parsed.get("action_taken") or "") == "clarify_before_estimate"
        )
        if requires_follow_up:
            if planner_requires_clarify:
                best_parsed = dict(best_parsed)
                best_parsed["followup_policy_decision"] = "clarify_before_estimate"
                best_parsed["blocking_slots"] = list(
                    dict.fromkeys(
                        list(best_parsed.get("blocking_slots", []))
                        + list(planner_result.planning_brief.clarification_targets)
                    )
                )
                best_parsed["missing_slots"] = list(
                    dict.fromkeys(
                        list(best_parsed.get("missing_slots", []))
                        + list(planner_result.planning_brief.clarification_targets)
                    )
                )
                best_parsed = augment_followup_metadata(best_parsed)
            # Never override LLM's action_taken ??let it flow to final_response.
            # requires_follow_up determines routing; action_taken is LLM's semantic decision.
        action_taken = str(best_parsed.get("action_taken") or "clarify_before_estimate")


        route_target = "clarify_user_private" if requires_follow_up else "best_effort_answer"


        final_best_source = _final_best_answer_source(best_source, best_parsed)
        selected_titles = [
            str(title).strip()
            for title in [
                *(item.get("title") for item in filtered_knowledge[:MAX_SELECTED_EVIDENCE_ITEMS]),
                *(item.get("title") for item in sources[:MAX_SELECTED_EVIDENCE_ITEMS]),
            ]
            if str(title or "").strip()
        ]
        evidence_bundle = _build_evidence_bundle(
            _merge_evidence_items(filtered_knowledge, sources),
            selected_titles=selected_titles,
        )
        candidate_tool_calls = _build_tool_candidate_requests(
            query=retrieval_query,
            decision_tool_plan=decision_result.tool_plan,
        )
        executed_tool_names = {item["tool_name"] for item in executed_tool_calls}
        for candidate in candidate_tool_calls:
            if candidate["tool_name"] not in executed_tool_names:
                executed_tool_calls.append(
                    _build_tool_result(
                        tool_name=candidate["tool_name"],
                        status="skipped" if candidate["tool_name"] != "search_official_nutrition" else ("not_needed" if not used_search else "skipped"),
                        reason="Tool remained available but was not needed in the final bounded runtime path.",
                    )
                )
        context_pack_trace = _build_context_pack_trace(
            state=conversation_state,
            evidence_bundle=evidence_bundle,
            available_tools=available_tools,
            evidence_guardrail_prompt=EVIDENCE_SOURCE_GUARDRAIL_PROMPT,
        ).model_dump(mode="json")
        tool_decision_trace = ToolDecisionTrace(
            available_tools=available_tools,
            candidate_tool_calls=[ToolCallRequest(**item) for item in candidate_tool_calls],
            executed_tool_calls=[ToolCallResult(**item) for item in executed_tool_calls],
        ).model_dump(mode="json")
        dropped_evidence = []
        for item in _merge_evidence_items(filtered_knowledge, sources):
            if str(item.get("title") or "") not in selected_titles:
                dropped_evidence.append(_to_evidence_candidate(item, selected=False, drop_reason="not_selected_for_final_answer"))
        evidence_resolution_trace = EvidenceResolutionTrace(
            local_exact_candidates=[_to_evidence_candidate(item) for item in filtered_knowledge if item.get("evidence_role") == "exact_truth"],
            local_anchor_candidates=[_to_evidence_candidate(item) for item in filtered_knowledge if item.get("evidence_role") == "ingredient_anchor"],
            search_candidates=[_to_evidence_candidate(item) for item in sources if _source_class_for_item(item) == "web_search_official"],
            doc_read_fragments=[_to_evidence_candidate(item) for item in doc_read_fragments],
            final_kept_evidence=[_to_evidence_candidate(item, selected=True) for item in _merge_evidence_items(filtered_knowledge, sources) if str(item.get("title") or "") in selected_titles],
            dropped_evidence=dropped_evidence,
        ).model_dump(mode="json")
        durable_memory_pruned = False
        memory_trace = MemoryTrace(
            durable_memory_enabled=True,
            hits=[
                hit.model_dump(mode="json")
                for hit in conversation_state.durable_memory_hits[:MAX_DURABLE_MEMORY_HITS]
            ] if not durable_memory_pruned else [],
            write_candidates=[
                {
                    "memory_type": "correction",
                    "value": conversation_state.conversation_digest.last_explicit_correction,
                    "trigger": "explicit_transcript_correction",
                }
            ] if conversation_state.conversation_digest.last_explicit_correction else [],
        ).model_dump(mode="json")
        memory_trace["pruned_due_to_budget"] = durable_memory_pruned





        multi_turn_context = build_multi_turn_context(
            state=conversation_state,
            planner_intent=planner_result.intent,
            context_snapshot=context_str,
            retrieval_query_rewritten=retrieval_query_rewritten,
            original_retrieval_query=original_retrieval_query,
            effective_retrieval_query=retrieval_query,
        )

        trace_contract = _build_trace_contract(


            request=request, effective_request=effective_request, planner_result=planner_result,


            planner_enabled=planner_enabled, normalization=normalization, risk_packet=risk_packet,


            meal_template=meal_template, template_override_blocked=False,


            retrieval_query=retrieval_query, retrieved_knowledge=filtered_knowledge,


            sources=sources, used_search=used_search, search_query=search_query,


            current_parsed=current_parsed, best_parsed=best_parsed, best_source=final_best_source,


            quality_signals=best_quality, retry_triggered=retry_triggered, retry_reason=retry_reason,




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
            provider_name=type(provider).__name__,
            schema_signature=SCHEMA_SIGNATURE,
            source_page_version=None,
            trace_contract=trace_contract,
            llm_traces=llm_traces,
            debug_steps=debug_steps,
            quality_signals=best_quality,
            best_answer_source=final_best_source,
            retry_triggered=retry_triggered,
            multi_turn_context=multi_turn_context,
        )
        final_response_result = await run_four_pass_final_response(
            provider=primary_llm,
            request_id=request_id,
            user_input=effective_request.text,
            task_meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            nutrition_result=nutrition_result or nutrition_result_from_primary(
                {
                    "action_taken": action_taken,
                    "confidence": best_parsed.get("confidence") or "low",
                    "exactness": best_parsed.get("exactness") or best_parsed.get("estimate_mode") or "unknown",
                    "unresolved_info": best_parsed.get("unresolved_info", []) or best_parsed.get("missing_slots", []) or best_parsed.get("blocking_slots", []),
                    "state_transition_hint": best_parsed.get("state_transition_hint"),
                    "answer_payload": {
                        "title": best_parsed.get("title"),
                        "components": best_parsed.get("components", []),
                        "estimated_kcal": best_parsed.get("estimated_kcal", 0),
                        "protein_g": best_parsed.get("protein_g", 0),
                        "carb_g": best_parsed.get("carb_g", 0),
                        "fat_g": best_parsed.get("fat_g", 0),
                        "uncertainty_factors": best_parsed.get("uncertainty_factors", []),
                        "base_estimated_kcal": best_parsed.get("base_estimated_kcal"),
                        "base_protein_g": best_parsed.get("base_protein_g"),
                        "base_carb_g": best_parsed.get("base_carb_g"),
                        "base_fat_g": best_parsed.get("base_fat_g"),
                        "portion_multiplier": best_parsed.get("portion_multiplier", 1.0),
                        "portion_reason": best_parsed.get("portion_reason", ""),
                    },
                }
            ),
            active_meal_summary=conversation_state.active_meal_summary.model_dump(mode="json"),
            llm_traces=llm_traces,
            max_tokens=PRIMARY_MAX_TOKENS,
            run_stage=_run_text_stage,
        )
        reply_text = final_response_result.reply_text
        if final_response_result.asked_follow_up:
            best_parsed = dict(best_parsed)
            best_parsed["follow_up_needed"] = True
            if not str(best_parsed.get("followup_question") or "").strip():
                best_parsed["followup_question"] = reply_text
        else:
            text_lower = str(effective_request.text or "").lower()
            modifier_rich_generic_drink = any(token in text_lower for token in ["半糖", "微糖", "少糖", "無糖", "去冰", "少冰"])
            if modifier_rich_generic_drink and str(best_parsed.get("action_taken") or "") != "clarify_before_estimate":
                best_parsed = dict(best_parsed)
                best_parsed["follow_up_needed"] = False
                best_parsed["followup_question"] = ""
        payload = _build_payload(
            effective_request, request_id=request_id, parsed=best_parsed, risk_packet=risk_packet,
            action_taken=action_taken, route_target=route_target, route_reason="unified_grounding",
            debug_steps=debug_steps, llm_traces=llm_traces, retrieval_triggered=retrieval_triggered,
            retrieval_query=retrieval_query, retrieved_knowledge=filtered_knowledge,
            quality_signals=best_quality, retry_triggered=retry_triggered, retry_reason=retry_reason,
            best_answer_source=final_best_source, private_only=best_private, used_search=used_search,
            search_query=search_query, search_quality=search_quality, sources=sources,
            reply_text=reply_text,
            trace_contract=trace_envelope.trace_contract,
            north_star_evaluation=trace_envelope.north_star_evaluation,
            multi_turn_context=trace_envelope.multi_turn_context,
            token_usage=trace_envelope.token_usage,
            trace_meta=trace_envelope.trace_meta,
            span_timeline=trace_envelope.span_timeline,
            decision_journal=trace_envelope.decision_journal,
            evidence_journal=trace_envelope.evidence_journal,
            diagnosis=trace_envelope.diagnosis,
            context_pack_trace=trace_envelope.context_pack_trace,
            tool_decision_trace=trace_envelope.tool_decision_trace,
            boundary_trace=trace_envelope.boundary_trace,
            judge_trace=trace_envelope.judge_trace,
            evidence_resolution_trace=trace_envelope.evidence_resolution_trace,
            memory_trace=trace_envelope.memory_trace,
        )


        if db and user:
            persistence_decision = persist_text_meal_result(
                db,
                user=user,
                latest_log=latest_log,
                planner_intent=planner_result.intent,
                payload=payload,
                raw_input=request.text,
                request_id=request_id,
                incoming_user_message_id=incoming_user_message_id,
            )
            payload.trace_contract["persistence_decision"] = persistence_decision
            if conversation_state.boundary_clarification_open and planner_result.meal_boundary != "boundary_clarification":
                payload.boundary_trace["boundary_resolution_state"] = "resolved"
                payload.boundary_trace["resolution_meal_id"] = persistence_decision.get("linked_meal_log_id")
            elif planner_result.meal_boundary == "boundary_clarification":
                payload.boundary_trace["boundary_resolution_state"] = "open"
            payload.span_timeline.append(
                {
                    "span_id": "span:persistence_decision:1",
                    "parent_span_id": None,
                    "stage": "persistence_decision",
                    "status": "ok",
                    "attempt_index": 1,
                    "trigger_reason": persistence_decision.get("action"),
                    "duration_ms": None,
                    "input_ref": "trace_contract.persistence_decision",
                    "output_ref": "multi_turn_context",
                    "stage_input_summary": {"planner_intent": persistence_decision.get("planner_intent")},
                    "stage_output_summary": {
                        "action": persistence_decision.get("action"),
                        "status": persistence_decision.get("status"),
                        "parent_log_id": persistence_decision.get("parent_log_id"),
                    },
                    "handoff_contract": {"assistant_message_appended": persistence_decision.get("assistant_message_appended", False)},
                }
            )

        return payload


    except BuilderSpaceResponseError as exc:


        llm_traces.append(_trace_with_request_id(exc.trace, request_id))


        parsed = {
            "decision": "ASK_USER",
            "title": effective_request.text,
            "components": [],
            "protein_g": 0,
            "carb_g": 0,
            "fat_g": 0,
            "estimated_kcal": 0,
            "uncertainty_factors": ["insufficient meal detail"],
            "followup_question": "Please share the food details and portion size so I can estimate it more reliably.",
            "follow_up_needed": True,
            "follow_up_reasoning": "",
            "unresolved_info": ["meal_description", "portion_size"],
            "response_mode_hint": "clarify_first",
            "state_transition_hint": "draft_unresolved",
            "action_taken": "clarify_before_estimate",
            "tool_request": "none",
            "tool_request_reason": "",
            "answer_payload": {},
        }


        return _build_payload(effective_request, request_id=request_id, parsed=parsed, risk_packet=risk_packet, action_taken="api_fallback", route_target="best_effort_answer", route_reason="api_error", debug_steps=debug_steps, llm_traces=llm_traces, quality_signals=_evaluate_answer(parsed, risk_packet, None), private_only=True)








def record_success(


    request: EstimateRequest,


    payload: EstimatePayload,


    *,


    source_page_version: str | None = None,


    normalized_user_input: str | None = None,


) -> None:


    raw_user_input = _normalize_text(request.text)


    normalized_input = _normalize_text(


        normalized_user_input


        or _normalized_input_from_debug_steps(payload.debug_steps)


        or _normalize_user_input_for_estimation(request.text)["normalized_text"]


    )


    event = AuditEvent(


        request_id=payload.request_id,


        timestamp=now_iso(),


        text=request.text,


        raw_user_input=raw_user_input,


        normalized_user_input=normalized_input,


        user_input_unicode_escape=_unicode_escape(request.text),


        source_page_version=source_page_version,


        allow_search=request.allow_search,


        status="ok",


        route_target=payload.route_target,


        action_taken=payload.action_taken,


        debug_steps=payload.debug_steps,


        llm_traces=payload.llm_traces,


        payload=payload.model_dump(mode="json"),


    )


    payload.trace_meta["source_page_version"] = source_page_version


    trace_path = write_request_trace_artifact(


        payload.request_id,


        {
            "request_id": payload.request_id,
            "timestamp": now_iso(),
            "request": {
                "user_id": getattr(request, 'user_id', 'anonymous'),
                "text": request.text,
                "allow_search": request.allow_search,
            },
            "raw_user_input": request.text,
            "normalized_user_input": normalized_input,
            "source_page_version": source_page_version,
            "trace_meta": payload.trace_meta or {},
            "span_timeline": payload.span_timeline or [],
            "decision_journal": payload.decision_journal or {},
            "evidence_journal": payload.evidence_journal or {},
            "diagnosis": payload.diagnosis or {},
            "multi_turn_context": payload.multi_turn_context or {},
            "token_usage": getattr(payload, 'token_usage', {}) or {},
            "north_star_evaluation": payload.north_star_evaluation or {},
            "planner_result": (payload.trace_contract or {}).get("planner_output", {}),
            "trace_contract": payload.trace_contract or {},
            "payload": payload.model_dump(mode="json"),
            "debug_steps": payload.debug_steps,
            "llm_traces": payload.llm_traces,
        },


    )


    event.trace_artifact_path = str(trace_path)


    append_audit_event(event)








def record_error(


    request: EstimateRequest,


    error: str,


    *,


    request_id: str,


    source_page_version: str | None = None,


    normalized_user_input: str | None = None,


) -> None:


    raw_user_input = _normalize_text(request.text)


    normalized_input = _normalize_text(normalized_user_input or _normalize_user_input_for_estimation(request.text)["normalized_text"])


    event = AuditEvent(


        request_id=request_id,


        timestamp=now_iso(),


        text=request.text,


        raw_user_input=raw_user_input,


        normalized_user_input=normalized_input,


        user_input_unicode_escape=_unicode_escape(request.text),


        source_page_version=source_page_version,


        allow_search=request.allow_search,


        status="error",


        error=error,


    )


    trace_path = write_request_trace_artifact(


        request_id,


        {
            "request_id": request_id,
            "timestamp": now_iso(),
            "request": {
                "user_id": getattr(request, 'user_id', 'anonymous'),
                "text": request.text,
                "allow_search": request.allow_search,
            },
            "raw_user_input": request.text,
            "normalized_user_input": normalized_input,
            "source_page_version": source_page_version,
            "trace_meta": {
                "request_id": request_id,
                "user_id": getattr(request, 'user_id', 'anonymous'),
                "timestamp": now_iso(),
                "provider": None,
                "schema_signature": SCHEMA_SIGNATURE,
                "source_page_version": source_page_version,
            },
            "span_timeline": [],
            "decision_journal": {},
            "evidence_journal": {},
            "diagnosis": {
                "failed_layer": "repair_rescue",
                "why": error,
                "repairability": "high",
                "suggested_next_action": "inspect_request_trace",
                "trace_health": "degraded",
            },
            "error": error,
            "status": "error"
        },


    )


    event.trace_artifact_path = str(trace_path)


    append_audit_event(event)



