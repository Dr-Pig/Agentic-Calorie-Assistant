from __future__ import annotations

from typing import Any

from ....nutrition.application.evidence_normalizer import split_evidence_lanes
from ....nutrition.application.evidence_selector import db_hit_type, summarize_retrieved_evidence
from ....schemas import ComponentEstimate, EstimatePayload, EstimateRequest


def unicode_escape(text: str) -> str:
    return text.encode("unicode_escape", errors="backslashreplace").decode("ascii")


def _build_component_estimates(
    components: list[str],
    *,
    source: str,
    component_breakdown: list[dict[str, Any]] | None = None,
) -> list[ComponentEstimate]:
    by_name = {
        str(item.get("name") or item.get("title") or "").strip(): item
        for item in (component_breakdown or [])
        if str(item.get("name") or item.get("title") or "").strip()
    }
    return [
        ComponentEstimate(
            name=str(component),
            source=source,  # type: ignore[arg-type]
            quantity_hint=str(
                by_name.get(str(component), {}).get("quantity_hint")
                or by_name.get(str(component), {}).get("portion_hint")
                or ""
            ).strip()
            or None,
            reason=str(by_name.get(str(component), {}).get("reason") or "").strip(),
            evidence_ids=[
                str(item)
                for item in by_name.get(str(component), {}).get("evidence_ids", [])
                if str(item).strip()
            ],
            estimated_kcal=int(by_name.get(str(component), {}).get("estimated_kcal") or 0),
            protein_g=int(by_name.get(str(component), {}).get("protein_g") or 0),
            carb_g=int(by_name.get(str(component), {}).get("carb_g") or 0),
            fat_g=int(by_name.get(str(component), {}).get("fat_g") or 0),
        )
        for component in components
        if str(component).strip()
    ]


def _trace_followup_decision(best_parsed: dict[str, Any]) -> str:
    if bool(best_parsed.get("follow_up_needed")) or str(best_parsed.get("followup_question") or "").strip():
        return "should_ask"
    return "not_needed"


def _trace_followup_reason(best_parsed: dict[str, Any]) -> str | None:
    reason = str(best_parsed.get("follow_up_reasoning") or "").strip()
    return reason or None


def build_trace_contract(
    *,
    request: EstimateRequest,
    effective_request: EstimateRequest,
    manager_result: Any,
    manager_enabled: bool,
    normalization: dict[str, Any],
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
    template_override_blocked: bool,
    retrieval_query: str | None,
    retrieved_knowledge: list[dict[str, Any]],
    sources: list[dict[str, Any]],
    used_search: bool,
    search_query: str | None,
    current_parsed: dict[str, Any],
    best_parsed: dict[str, Any],
    best_source: str,
    quality_signals: dict[str, Any],
    retry_triggered: bool,
    retry_reason: str | None,
    context_pack_trace: dict[str, Any] | None = None,
    tool_decision_trace: dict[str, Any] | None = None,
    boundary_trace: dict[str, Any] | None = None,
    judge_trace: dict[str, Any] | None = None,
    evidence_resolution_trace: dict[str, Any] | None = None,
    memory_trace: dict[str, Any] | None = None,
) -> dict[str, Any]:
    manager_mode = (
        "llm"
        if manager_enabled and not str(manager_result.route_hints.get("manager_source", "")).startswith("fallback")
        else "fallback"
        if manager_enabled
        else "disabled"
    )
    normalizer_mode = "off"
    if not manager_enabled:
        normalizer_mode = "manager_off_fallback"
    elif normalization.get("normalizer_applied"):
        normalizer_mode = "post_manager_estimation_cleanup"
    manager_input_view = request.text if manager_enabled else effective_request.text
    grounding_attempts: list[dict[str, Any]] = []
    if retrieval_query:
        grounding_attempts.append({"kind": "local_retrieval", "query": retrieval_query, "hit_count": len(retrieved_knowledge), "used": bool(retrieved_knowledge)})
    if used_search:
        grounding_attempts.append({"kind": "search", "query": search_query, "hit_count": len(sources), "used": True})
    return {
        "raw_input_bundle": {"text": request.text, "modalities": ["text"]},
        "manager_used": manager_enabled,
        "manager_input_view": manager_input_view,
        "manager_output": {
            "intent": manager_result.intent,
            "meal_boundary": manager_result.meal_boundary,
            "active_meal_reference": manager_result.active_meal_reference,
            "boundary_confidence": manager_result.boundary_confidence,
            "manager_self_reported_boundary_confidence": manager_result.route_hints.get("manager_self_reported_boundary_confidence"),
            "resolved_query": manager_result.resolved_query,
            "resolution_mode": manager_result.resolution_mode,
            "manager_brief": manager_result.manager_brief.model_dump(mode="json"),
            "route_hints": manager_result.route_hints,
            "missing_context": manager_result.missing_info,
            "contextual_cues": manager_result.input_signals,
            "normalized_user_input": manager_result.normalized_user_input,
            "manager_mode": manager_mode,
            "manager_source": manager_result.route_hints.get("manager_source"),
        },
        "normalizer_mode": normalizer_mode,
        "normalizer_diff": {
            "changed": bool(normalization.get("normalizer_applied")),
            "raw_text": normalization.get("raw_text"),
            "normalized_text": normalization.get("normalized_text"),
            "notes": normalization.get("notes", []),
        },
        "risk_validator_input": effective_request.text,
        "risk_flags": risk_packet.get("risk_flags", []),
        "required_checks": risk_packet.get("required_checks", {}),
        "validator_adjustments": {
            "review_focus": risk_packet.get("review_focus", []),
            "must_ask_if_uncertain": risk_packet.get("must_ask_if_uncertain", []),
        },
        "template_match": {
            "matched": bool(meal_template),
            "blocked": template_override_blocked,
            "why_blocked": "specific_item_phrase_detected" if template_override_blocked else None,
            "template_id": meal_template.get("template_id") if meal_template else None,
            "template_title": meal_template.get("title") if meal_template else None,
        },
        "primary_llm_output": {
            "decision": current_parsed.get("decision"),
            "food_origin": current_parsed.get("food_origin"),
            "food_class": current_parsed.get("food_class"),
            "needs_external_data": current_parsed.get("needs_external_data"),
            "estimated_kcal": current_parsed.get("estimated_kcal"),
            "uncertainty_factors": current_parsed.get("uncertainty_factors", []),
            "followup_question": current_parsed.get("followup_question", ""),
            "follow_up_needed": current_parsed.get("follow_up_needed", False),
            "unresolved_info": current_parsed.get("unresolved_info", []),
        },
        "followup_decision": _trace_followup_decision(best_parsed),
        "followup_reason": _trace_followup_reason(best_parsed),
        "followup_policy_decision": best_parsed.get("followup_policy_decision"),
        "route_family": best_parsed.get("route_family"),
        "response_mode_hint": best_parsed.get("response_mode_hint"),
        "missing_slots": best_parsed.get("missing_slots", []),
        "missing_high_impact_slots": best_parsed.get("missing_high_impact_slots", []),
        "blocking_slots": best_parsed.get("blocking_slots", []),
        "unresolved_info": best_parsed.get("unresolved_info", []),
        "followup_targets": best_parsed.get("followup_targets", []),
        "why_followup": best_parsed.get("why_followup"),
        "reason_not_direct_answer": best_parsed.get("reason_not_direct_answer"),
        "why_not_exact": best_parsed.get("why_not_exact"),
        "why_no_more_tools": best_parsed.get("why_no_more_tools"),
        "grounding_attempts": grounding_attempts,
        "reasoning_state": dict((best_parsed.get("reasoning_state") or {})),
        "search_attempt_count": int((best_parsed.get("reasoning_state") or {}).get("search_attempt_count") or 0),
        "why_not_searching": str(best_parsed.get("reason_for_not_requesting_tool") or best_parsed.get("why_no_more_tools") or ""),
        "request_tool_reason_quality": "present" if str(best_parsed.get("tool_request_reason") or "").strip() else "missing",
        "observation_quality": str(((best_parsed.get("reasoning_state") or {}).get("observation_summary") or {}).get("coverage_status") or ""),
        "db_hit_type": db_hit_type(retrieved_knowledge=retrieved_knowledge, meal_template=meal_template),
        "grounding_summary": {
            "retrieved_knowledge_count": len(retrieved_knowledge),
            "source_count": len(sources),
            "exact_truth_present": bool(split_evidence_lanes(retrieved_knowledge)["exact_lane"]),
            "evidence_roles": sorted({str(item.get("evidence_role")) for item in [*retrieved_knowledge, *sources] if item.get("evidence_role")}),
        },
        "match_confidence": "none",
        "match_path": "none",
        "grounding_contradiction": False,
        "best_answer_source": best_source,
        "best_estimate_mode": best_parsed.get("estimate_mode"),
        "estimate_confidence_tier": best_parsed.get("estimate_confidence_tier"),
        "enrichment_applied": {
            "deterministic_component_estimates": bool(best_parsed.get("deterministic_component_estimates")),
            "estimate_mode": best_parsed.get("estimate_mode"),
            "estimate_confidence_tier": best_parsed.get("estimate_confidence_tier"),
        },
        "retry_triggered": retry_triggered,
        "retry_reason": retry_reason,
        "rescue_applied": {},
        "final_answer_summary": {
            "title": best_parsed.get("title"),
            "decision": best_parsed.get("decision"),
            "estimated_kcal": best_parsed.get("estimated_kcal"),
            "components": best_parsed.get("components", []),
        },
        "stage_quality_signals": quality_signals,
        "context_pack_trace": context_pack_trace or {},
        "tool_decision_trace": tool_decision_trace or {},
        "boundary_trace": boundary_trace or {},
        "judge_trace": judge_trace or {},
        "evidence_resolution_trace": evidence_resolution_trace or {},
        "memory_trace": memory_trace or {},
    }


def build_payload(
    request: EstimateRequest,
    *,
    request_id: str,
    parsed: dict[str, Any],
    risk_packet: dict[str, Any],
    action_taken: str,
    route_target: str,
    route_reason: str,
    debug_steps: list[dict[str, Any]],
    llm_traces: list[dict[str, Any]],
    retrieval_triggered: bool,
    retrieval_query: str | None,
    retrieved_knowledge: list[dict[str, Any]],
    quality_signals: dict[str, Any],
    retry_triggered: bool,
    retry_reason: str | None,
    best_answer_source: str,
    private_only: bool,
    used_search: bool,
    search_query: str | None,
    search_quality: str | None,
    sources: list[dict[str, Any]],
    reply_text: str | None = None,
    trace_contract: dict[str, Any] | None = None,
    north_star_evaluation: dict[str, Any] | None = None,
    multi_turn_context: dict[str, Any] | None = None,
    token_usage: dict[str, Any] | None = None,
    trace_meta: dict[str, Any] | None = None,
    span_timeline: list[dict[str, Any]] | None = None,
    decision_journal: dict[str, Any] | None = None,
    evidence_journal: dict[str, Any] | None = None,
    diagnosis: dict[str, Any] | None = None,
    context_pack_trace: dict[str, Any] | None = None,
    tool_decision_trace: dict[str, Any] | None = None,
    boundary_trace: dict[str, Any] | None = None,
    judge_trace: dict[str, Any] | None = None,
    evidence_resolution_trace: dict[str, Any] | None = None,
    memory_trace: dict[str, Any] | None = None,
) -> EstimatePayload:
    del private_only
    response_mode_hint = str(parsed.get("response_mode_hint") or "")
    unresolved_info = [str(item) for item in parsed.get("unresolved_info") or [] if str(item).strip()]
    blocking_slots = [str(item) for item in parsed.get("blocking_slots") or [] if str(item).strip()]
    source_decision: str
    if response_mode_hint == "clarify_first" or blocking_slots or unresolved_info:
        source_decision = "ask_user"
    else:
        source_decision = "retrieve" if retrieval_triggered or used_search else "ready"
    protein = parsed["protein_g"]
    carb = parsed["carb_g"]
    fat = parsed["fat_g"]
    answer_payload = dict(parsed.get("answer_payload") or {})
    raw_macro_breakdown = dict(answer_payload.get("raw_macro_breakdown") or {})
    display_macro_breakdown = dict(answer_payload.get("display_macro_breakdown") or answer_payload.get("macro_breakdown") or {})
    if display_macro_breakdown:
        protein = int(display_macro_breakdown.get("protein_g") or 0)
        carb = int(display_macro_breakdown.get("carb_g") or 0)
        fat = int(display_macro_breakdown.get("fat_g") or 0)
    source_label = "retrieval" if retrieved_knowledge else "llm"
    component_estimates = parsed.get("deterministic_component_estimates") or _build_component_estimates(
        parsed["components"],
        source=source_label,
        component_breakdown=list(parsed.get("component_breakdown") or []),
    )
    evidence_summary = summarize_retrieved_evidence(retrieved_knowledge or sources)
    normalized_search_quality = search_quality.get("quality") if isinstance(search_quality, dict) else search_quality
    fallback_reply_text = (reply_text or "").strip()
    if not fallback_reply_text:
        if parsed["estimated_kcal"] > 0:
            fallback_reply_text = f"{parsed['title'] or request.text} 約 {parsed['estimated_kcal']} kcal。"
        else:
            fallback_reply_text = "請再描述更具體的內容與份量。"
    return EstimatePayload(
        request_id=request_id,
        meal_title=parsed["title"] or request.text,
        components=parsed["components"],
        quantity_hints=parsed["components"],
        component_estimates=component_estimates,
        component_breakdown=list(parsed.get("component_breakdown") or answer_payload.get("component_breakdown") or []),
        macro_breakdown=dict(display_macro_breakdown or {
            "protein_g": protein if protein > 0 else None,
            "carb_g": carb if carb > 0 else None,
            "fat_g": fat if fat > 0 else None,
            "macro_source": "llm_hint" if any(value > 0 for value in (protein, carb, fat)) else "unavailable",
            "macro_confidence": "low",
        }),
        raw_macro_breakdown=dict(raw_macro_breakdown),
        display_macro_breakdown=dict(display_macro_breakdown or {
            "protein_g": protein if protein > 0 else None,
            "carb_g": carb if carb > 0 else None,
            "fat_g": fat if fat > 0 else None,
            "macro_source": "llm_hint" if any(value > 0 for value in (protein, carb, fat)) else "unavailable",
            "macro_confidence": "low",
        }),
        evidence_ids_used=list(parsed.get("evidence_ids_used") or answer_payload.get("evidence_ids_used") or []),
        protein_g=protein,
        carb_g=carb,
        fat_g=fat,
        estimated_kcal=parsed["estimated_kcal"],
        uncertain_macro_areas=parsed["uncertainty_factors"],
        source_decision=source_decision,
        answer_mode="best_effort" if retry_triggered or parsed["uncertainty_factors"] else "direct_answer",
        action_taken=action_taken,
        route_target=route_target,  # type: ignore[arg-type]
        route_reason=route_reason,
        followup_question=parsed["followup_question"] or None,
        follow_up_needed=bool(parsed.get("follow_up_needed")),
        follow_up_reasoning=str(parsed.get("follow_up_reasoning") or ""),
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        reply_text=fallback_reply_text,
        retrieval_triggered=retrieval_triggered,
        retrieval_query=retrieval_query,
        retrieved_knowledge=retrieved_knowledge,
        risk_packet=risk_packet,
        quality_signals=quality_signals,
        retry_triggered=retry_triggered,
        retry_reason=retry_reason,
        best_answer_source=best_answer_source,
        best_estimate_mode=str(parsed.get("estimate_mode") or "llm_only"),
        estimate_confidence_tier=str(parsed.get("estimate_confidence_tier") or "low"),
        retrieved_evidence_summary=evidence_summary,
        failure_family=quality_signals.get("failure_family"),
        used_search=used_search,
        search_query=search_query,
        search_quality=str(normalized_search_quality or "") or None,
        sources=sources,
        trace_contract=trace_contract or {},
        failed_layer=(north_star_evaluation or {}).get("failed_layer"),
        primary_failure_reason=(north_star_evaluation or {}).get("why"),
        north_star_evaluation=north_star_evaluation or {},
        multi_turn_context=multi_turn_context or {},
        token_usage=token_usage or {},
        trace_meta=trace_meta or {},
        span_timeline=span_timeline or [],
        decision_journal=decision_journal or {},
        evidence_journal=evidence_journal or {},
        diagnosis=diagnosis or {},
        reasoning_state=dict(parsed.get("reasoning_state") or {}),
        context_pack_trace=context_pack_trace or {},
        tool_decision_trace=tool_decision_trace or {},
        boundary_trace=boundary_trace or {},
        judge_trace=judge_trace or {},
        evidence_resolution_trace=evidence_resolution_trace or {},
        memory_trace=memory_trace or {},
    )
