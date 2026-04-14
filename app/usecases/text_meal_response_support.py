from __future__ import annotations

from typing import Any

from ..agent.final_response_llm import run_four_pass_final_response
from ..agent.nutrition_resolution_normalizer import nutrition_result_from_primary
from ..observability.payload_builders import build_payload
from ..schemas import EstimatePayload


def _looks_like_drink_size_followup(text: str) -> bool:
    lowered = str(text or "").lower()
    return any(token in lowered for token in ("tall", "grande", "venti", "中杯", "大杯", "小杯", "杯量", "尺寸"))


def _should_clear_ramen_followup(parsed: dict[str, Any], followup_text: str) -> bool:
    title = str(parsed.get("title") or "")
    if "拉麵" not in title:
        return False
    if _looks_like_drink_size_followup(followup_text):
        return False
    return True


async def finalize_response_payload(
    *,
    primary_llm: Any,
    effective_request: Any,
    request_id: str,
    task_meal_link_result: Any,
    decision_result: Any,
    nutrition_result: Any,
    conversation_state: Any,
    llm_traces: list[dict[str, Any]],
    max_tokens: int,
    run_stage: Any,
    best_parsed: dict[str, Any],
    risk_packet: dict[str, Any],
    action_taken: str,
    route_target: str,
    debug_steps: list[dict[str, Any]],
    best_quality: dict[str, Any],
    retry_triggered: bool,
    retry_reason: str | None,
    best_source: str,
    best_private: bool,
    retrieval_triggered: bool,
    retrieval_query: str | None,
    filtered_knowledge: list[dict[str, Any]],
    used_search: bool,
    search_query: str | None,
    search_quality: str | None,
    sources: list[dict[str, Any]],
    trace_envelope: Any,
) -> EstimatePayload:
    existing_followup = str(best_parsed.get("followup_question") or "").strip()
    final_response_result = await run_four_pass_final_response(
        provider=primary_llm,
        request_id=request_id,
        user_input=effective_request.text,
        task_meal_link_result=task_meal_link_result,
        decision_result=decision_result,
        nutrition_result=nutrition_result
        or nutrition_result_from_primary(
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
        max_tokens=max_tokens,
        run_stage=run_stage,
    )
    reply_text = final_response_result.reply_text
    final_best_parsed = dict(best_parsed)
    if final_response_result.asked_follow_up:
        final_best_parsed["follow_up_needed"] = True
        if not str(final_best_parsed.get("followup_question") or "").strip():
            final_best_parsed["followup_question"] = reply_text
    else:
        final_best_parsed["follow_up_needed"] = False
        final_best_parsed["followup_question"] = ""

    return build_payload(
        effective_request,
        request_id=request_id,
        parsed=final_best_parsed,
        risk_packet=risk_packet,
        action_taken=action_taken,
        route_target=route_target,
        route_reason="unified_grounding",
        debug_steps=debug_steps,
        llm_traces=llm_traces,
        retrieval_triggered=retrieval_triggered,
        retrieval_query=retrieval_query,
        retrieved_knowledge=filtered_knowledge,
        quality_signals=best_quality,
        retry_triggered=retry_triggered,
        retry_reason=retry_reason,
        best_answer_source=best_source,
        private_only=best_private,
        used_search=used_search,
        search_query=search_query,
        search_quality=search_quality,
        sources=sources,
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
