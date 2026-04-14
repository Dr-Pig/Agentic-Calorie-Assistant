"""
Nutrition Resolution Pass - Core nutrition estimation.

Responsibilities:
- Estimate calories, protein, carbs, fat from components
- Use evidence to ground estimates
- Determine resolution mode and confidence

Best Practices:
- Single responsibility: nutrition estimation
- Evidence gathered before pass, not inside
- Strict validation of LLM output
- Two-round iteration for tool usage
"""

from __future__ import annotations

from typing import Any

from ...agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from ...agent.nutrition_resolution_normalizer import (
    normalize_structured_answer as _normalize_structured_answer,
    nutrition_result_from_primary,
)
from ...agent.nutrition_resolution_parser import augment_followup_metadata
from ...agent.nutrition_resolution_prompt import NUTRITION_RESOLUTION_PROMPT
from ...application.context_assembly import (
    build_nutrition_resolution_payload,
    knowledge_context,
    risk_context,
)
from ...application.evidence_assembly import (
    build_tool_result,
    execute_primary_tool_request,
    merge_evidence_items,
    normalize_tool_evidence,
)
from ...application.nutrition_invariants import apply_nutrition_invariant_guards
from ...application.pass_runner import run_pass
from ...schemas import NutritionResolutionResult
from .base import run_text_stage


PRIMARY_MAX_TOKENS = 8192
MAX_SELECTED_EVIDENCE_ITEMS = 3


async def run_nutrition_resolution_pass(
    provider: Any,
    request_id: str,
    user_input: str,
    task_meal_link_result: Any,
    decision_result: Any,
    canonical_meal_state: Any,
    filtered_knowledge: list[dict[str, Any]],
    normalized_evidence: list[dict[str, Any]],
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
    active_meal_context_allowed: bool,
    latest_log: Any | None,
    llm_traces: list[dict[str, Any]] | None = None,
    debug_steps: list[dict[str, Any]] | None = None,
    executed_tool_calls: list[dict[str, Any]] | None = None,
    sources: list[dict[str, Any]] | None = None,
    used_search: bool = False,
    search_query: str | None = None,
    search_quality: str | None = None,
    search_adapter: Any | None = None,
) -> tuple[
    dict[str, Any],
    NutritionResolutionResult,
    list[dict[str, Any]],
    list[dict[str, Any]],
    bool,
    str | None,
    dict[str, Any] | None,
]:
    """
    Execute the nutrition resolution pass with two rounds.

    Returns:
        tuple: (current_parsed, nutrition_result, filtered_knowledge, sources,
                used_search, search_query, search_quality)
    """
    llm_traces = llm_traces or []
    debug_steps = debug_steps or []
    executed_tool_calls = executed_tool_calls or []
    sources = sources or []

    selected_evidence = list(filtered_knowledge)
    current_parsed: dict[str, Any] = {}
    nutrition_result: NutritionResolutionResult | None = None

    # Two rounds: initial + optional tool iteration
    for round_index in range(2):
        stage_name = (
            "nutrition_resolution_pass_initial"
            if round_index == 0
            else "nutrition_resolution_pass_tool_round_2"
        )

        # Build evidence context
        evidence_ctx = knowledge_context(selected_evidence[:5])
        risk_ctx = risk_context(risk_packet)

        # Build calibration packet
        calibration = None
        packet_id = suggest_calibration_packet(user_input)
        if packet_id:
            calibration = get_meal_calibration(packet_id)

        # Old components for continuation
        old_components = (
            list(latest_log.components_json or [])
            if latest_log is not None and active_meal_context_allowed
            else []
        )

        nutrition_payload = build_nutrition_resolution_payload(
            meal_state=canonical_meal_state,
            meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            normalized_evidence=normalized_evidence,
            calibration_packet=calibration,
            user_input=user_input,
        )
        nutrition_payload["user_input"] = user_input
        nutrition_payload["risk_packet"] = risk_packet
        nutrition_payload["selected_evidence_summary"] = [
            {"title": item.get("title", ""), "source": item.get("source_type", "")}
            for item in selected_evidence[:3]
        ]
        nutrition_payload["active_meal_context_allowed"] = active_meal_context_allowed
        nutrition_payload["old_components"] = old_components

        # Fallback for this pass
        fallback_parsed = augment_followup_metadata(
            _normalize_structured_answer(
                None,
                user_text=user_input,
                risk_packet=risk_packet,
                meal_template=meal_template,
            )
        )

        current_parsed, nutrition_envelope = await run_pass(
            provider=provider,
            stage=stage_name,
            system_prompt=NUTRITION_RESOLUTION_PROMPT + "\n\n[EVIDENCE_CONTEXT]\n" + evidence_ctx + "\n\n[RISK_CONTEXT]\n" + risk_ctx,
            user_payload=nutrition_payload,
            max_tokens=PRIMARY_MAX_TOKENS,
            fallback_result=fallback_parsed,
            normalize=lambda raw, fb: augment_followup_metadata(
                _normalize_structured_answer(
                    raw,
                    user_text=user_input,
                    risk_packet=risk_packet,
                    meal_template=meal_template,
                )
            ),
            dump=lambda r: dict(r),
            run_stage=run_text_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="nutrition_resolution" if round_index == 0 else "nutrition_tool_iteration",
            handoff_contract={
                "meal_link_action": task_meal_link_result.meal_link_action,
                "decision_next_action": decision_result.next_action,
                "evidence_count": len(selected_evidence),
            },
            required_fields=["action_taken", "response_mode_hint"],
            required_fields_source="normalized",
        )

        if nutrition_envelope.status != "success":
            debug_steps.append({
                "request_id": request_id,
                "step": "nutrition_resolution_pass",
                "stage": stage_name,
                "status": nutrition_envelope.status,
                "error": nutrition_envelope.error,
            })

        # Build nutrition result
        nutrition_result = nutrition_result_from_primary(current_parsed)
        if nutrition_result.answer_payload is not None:
            nutrition_result.answer_payload.setdefault("estimate_mode", current_parsed.get("estimate_mode"))
            nutrition_result.answer_payload.setdefault("exactness", current_parsed.get("exactness"))

        # Apply invariant guards
        nutrition_result, guard_meta = apply_nutrition_invariant_guards(
            result=nutrition_result,
            normalized_evidence=normalized_evidence,
        )

        # Update parsed with guarded result
        current_parsed["answer_payload"] = dict(nutrition_result.answer_payload or {})
        current_parsed["title"] = nutrition_result.answer_payload.get("title") or current_parsed.get("title")
        current_parsed["estimated_kcal"] = int(nutrition_result.answer_payload.get("estimated_kcal") or 0)
        current_parsed["protein_g"] = int(nutrition_result.answer_payload.get("protein_g") or 0)
        current_parsed["carb_g"] = int(nutrition_result.answer_payload.get("carb_g") or 0)
        current_parsed["fat_g"] = int(nutrition_result.answer_payload.get("fat_g") or 0)
        current_parsed["unresolved_info"] = list(nutrition_result.unresolved_info or [])
        current_parsed["state_transition_hint"] = nutrition_result.state_transition_hint

        debug_steps.append({
            "request_id": request_id,
            "step": "nutrition_invariant_guard",
            **guard_meta,
        })

        # Check if we should do tool iteration
        if current_parsed.get("action_taken") != "request_tool":
            break

        requested_tool = str(current_parsed.get("tool_request") or "none")
        if round_index >= 1 or requested_tool == "none":
            current_parsed["action_taken"] = "clarify_before_estimate"
            break

        # Execute tool request
        # Note: request param in execute_primary_tool_request is unused in function body
        tool_evidence, tool_sources, sq, sq_meta = await execute_primary_tool_request(
            tool_request=requested_tool,
            tool_reason=str(current_parsed.get("tool_request_reason") or ""),
            retrieval_query=user_input,
            resolved_query=user_input,
            planner_result=task_meal_link_result,
            request=None,  # request param is unused in execute_primary_tool_request
            search_adapter=search_adapter,
            executed_tool_calls=executed_tool_calls,
            build_tool_result=build_tool_result,
        )

        if tool_sources:
            used_search = True
            sources = merge_evidence_items(sources, tool_sources)
        if not tool_evidence:
            current_parsed["action_taken"] = "clarify_before_estimate"
            if not current_parsed.get("followup_question"):
                current_parsed["followup_question"] = "請更具體描述食物內容"
            current_parsed = augment_followup_metadata(current_parsed)
            nutrition_result = NutritionResolutionResult(
                resolution_mode="cannot_estimate_yet",
                resolution_basis="component_model",
                confidence="low",
                exactness="unknown",
                answer_payload={},
                unresolved_info=[str(item) for item in current_parsed.get("unresolved_info", [])],
                state_transition_hint="draft_unresolved",
            )
            break

        selected_evidence = merge_evidence_items(selected_evidence, tool_evidence)
        normalized_evidence = [
            *normalized_evidence,
            *normalize_tool_evidence(tool_evidence, source_type=requested_tool, query=sq or user_input),
        ]
        if sq:
            search_query = sq
        if sq_meta:
            search_quality = sq_meta

    return (
        current_parsed,
        nutrition_result,
        selected_evidence,
        sources,
        used_search,
        search_query,
        search_quality,
    )
