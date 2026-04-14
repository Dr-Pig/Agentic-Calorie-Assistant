from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ..agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from ..agent.nutrition_resolution_normalizer import (
    normalize_structured_answer as _normalize_structured_answer,
    nutrition_result_from_primary,
)
from ..agent.nutrition_resolution_parser import augment_followup_metadata
from ..agent.nutrition_resolution_prompt import NUTRITION_RESOLUTION_PROMPT
from ..application.answer_support import is_private_only_case as _is_private_only_case
from ..application.context_assembly import (
    build_nutrition_resolution_payload,
    calibration_context as _calibration_context,
    knowledge_context as _knowledge_context,
    risk_context as _risk_context,
)
from ..application.evidence_assembly import (
    build_reasoning_state,
    build_partial_grounding_packet,
    build_tool_result as _build_tool_result,
    execute_primary_tool_request,
    merge_evidence_items as _merge_evidence_items,
    normalize_tool_evidence,
)
from ..application.followup_policy import annotate_followup_policy
from ..application.nutrition_invariants import apply_nutrition_invariant_guards
from ..application.pass_runner import run_pass
from ..schemas import NutritionResolutionResult


@dataclass
class NutritionLoopOutcome:
    current_parsed: dict[str, Any]
    nutrition_result: NutritionResolutionResult | None
    selected_evidence_for_primary: list[dict[str, Any]]
    normalized_evidence: list[dict[str, Any]]
    partial_grounding: dict[str, Any]
    used_search: bool
    search_query: str | None
    search_quality: Any
    sources: list[dict[str, Any]]
    current_private: bool


def _nutrition_repair_note(*, parsed: dict[str, Any], nutrition_payload: dict[str, Any]) -> str | None:
    exact_truth_available = bool(nutrition_payload.get("exact_truth_available"))
    standardized_drink_like = bool(nutrition_payload.get("standardized_drink_like"))
    cup_size_provided = bool(nutrition_payload.get("cup_size_provided"))
    packaged_exact_candidate_count = int(nutrition_payload.get("packaged_exact_candidate_count") or 0)
    generic_drink_soft_avoid_exact = bool(nutrition_payload.get("generic_drink_soft_avoid_exact"))
    exact_brand_conflict_count = int(nutrition_payload.get("exact_brand_conflict_count") or 0)
    core_default_candidate_count = int(nutrition_payload.get("core_default_candidate_count") or 0)
    anchor_lane_count = len(nutrition_payload.get("anchor_lane_candidates") or [])
    template_lane_count = len(nutrition_payload.get("template_lane_hits") or [])
    meal_template_hit = bool(nutrition_payload.get("meal_template_hit"))
    missing_components = list((nutrition_payload.get("partial_grounding") or {}).get("missing_components") or [])
    drink_customization_clues = [str(item) for item in nutrition_payload.get("drink_customization_clues", []) if str(item).strip()]
    resolution_mode = str(parsed.get("resolution_mode") or "")
    estimate_mode = str(parsed.get("estimate_mode") or "")
    confidence = str(parsed.get("confidence") or "")
    followup_question = str(parsed.get("followup_question") or "").strip()
    unresolved_info = [str(item) for item in parsed.get("unresolved_info", []) if str(item).strip()]
    current_user_input = str(nutrition_payload.get("current_user_input") or "")

    if (
        (template_lane_count > 0 or meal_template_hit)
        and anchor_lane_count == 0
        and not exact_truth_available
        and estimate_mode in {"heuristic_fallback", "llm_only", "anchored_component"}
        and str(parsed.get("action_taken") or "") != "clarify_before_estimate"
    ):
        return (
            "Only template-level scaffold evidence is available and there are no exact or anchor lane candidates. "
            "Do not output a concrete target kcal. Re-answer with action_taken=clarify_before_estimate, "
            "resolution_mode=cannot_estimate_yet, exactness=unknown, estimate_mode=llm_only, and one short follow-up "
            "focused on the missing actual items or portions."
        )

    if (
        anchor_lane_count > 0
        and not exact_truth_available
        and int(parsed.get("estimated_kcal") or 0) <= 0
        and not list(parsed.get("components") or [])
    ):
        return (
            "Anchor evidence is already available for this dish class. Do not stop at zero-kcal clarification. "
            "Re-answer with a useful provisional estimate using the available anchor priors, keep exactness below exact_item, "
            "include a component_breakdown, and add one short follow-up only for the highest-impact missing detail."
        )

    if generic_drink_soft_avoid_exact and (
        estimate_mode == "exact_item" or resolution_mode in {"exact_label_finalize", "near_exact_finalize"}
    ):
        return (
            "This is a generic tea-shop drink class without an explicit brand or packaged-drink cue from the user. "
            "Do not finalize exact_item from packaged-retail evidence. Re-answer with a class-level provisional estimate, "
            "keep exactness below exact_item, and treat any follow-up as optional refinement rather than exact identity resolution."
        )

    if exact_truth_available and (cup_size_provided or not standardized_drink_like) and estimate_mode != "exact_item":
        if exact_brand_conflict_count > 0 and core_default_candidate_count > 0:
            return (
                "Multiple core-default exact candidates exist with conflicting brand hints. Do not ask the user for brand by default. Pick the dominant same-item core-default candidate using query_alignment and brand_hint, and finalize unless the conflict truly makes the item indeterminate."
            )
        return (
            "Exact evidence is already available for this item. Unless there is a material identity contradiction, finalize from "
            "the best same-item exact candidate instead of falling back to heuristic or anchored estimation."
        )
    if exact_truth_available and estimate_mode == "exact_item" and confidence != "high":
        return "You finalized from exact evidence. Raise confidence to high unless the evidence contains a material identity contradiction."
    if not exact_truth_available and (
        estimate_mode == "exact_item" or resolution_mode in {"exact_label_finalize", "near_exact_finalize"}
    ):
        return (
            "You cannot finalize as exact without exact evidence. Re-answer using anchored or heuristic posture and keep exactness below exact_item."
        )
    if standardized_drink_like and not cup_size_provided and estimate_mode == "exact_item":
        return (
            "Cup size is still missing for a standardized drink. Re-answer as a non-exact estimate with one short size follow-up instead of exact_item finalization."
        )
    if standardized_drink_like and drink_customization_clues and estimate_mode == "llm_only":
        return (
            "Sugar or ice modifiers already provide class-level anchors for this drink. Re-answer using estimate_mode=anchored_component instead of llm_only."
        )
    if standardized_drink_like and not drink_customization_clues and estimate_mode == "llm_only" and not followup_question:
        return (
            "For a generic tea-shop drink class without size, keep estimate_mode=llm_only but include one short cup-size follow-up so the user can refine the estimate."
        )
    if standardized_drink_like and packaged_exact_candidate_count > 0 and not drink_customization_clues and estimate_mode != "llm_only":
        return (
            "This is a generic drink class with packaged-retail references and no explicit size or modifier anchors. Re-answer using estimate_mode=llm_only rather than exact_item or heuristic_fallback."
        )
    if estimate_mode == "heuristic_fallback" and followup_question and "拉麵" in str(nutrition_payload.get("current_user_input") or ""):
        return (
            "For a specific named ramen shop item, the shop/item identity is already enough anchor for a direct answer. Re-answer using estimate_mode=anchored_component with no follow-up; keep broth, soup, and ordinary add-on variance inside uncertainty_factors unless the user explicitly mentioned them."
        )
    if (
        (template_lane_count > 0 or meal_template_hit)
        and anchor_lane_count == 0
        and not exact_truth_available
        and not followup_question
        and any(token in current_user_input for token in ("滷味", "熱炒", "合菜", "拼盤"))
        and not missing_components
    ):
        return (
            "This is still a high-variance generic class with only template support. Ask a short follow-up about the actual items eaten instead of giving a direct target kcal."
        )
    return None


async def run_nutrition_resolution_loop(
    *,
    primary_llm: Any,
    request_id: str,
    effective_user_input: str,
    request: Any,
    planner_result: Any,
    task_meal_link_result: Any,
    decision_result: Any,
    canonical_meal_state: Any,
    risk_packet: dict[str, Any],
    meal_template: dict[str, Any] | None,
    available_tools: list[str],
    latest_log: Any | None,
    active_meal_context_allowed: bool,
    local_exact_truth_present: bool,
    retrieval_query: str | None,
    selected_evidence_for_primary: list[dict[str, Any]],
    normalized_evidence: list[dict[str, Any]],
    partial_grounding: dict[str, Any],
    sources: list[dict[str, Any]],
    used_search: bool,
    search_query: str | None,
    search_quality: Any,
    llm_traces: list[dict[str, Any]],
    debug_steps: list[dict[str, Any]],
    executed_tool_calls: list[dict[str, Any]],
    run_stage: Any,
    search_adapter: Any | None = None,
    primary_max_tokens: int = 8192,
) -> NutritionLoopOutcome:
    current_parsed: dict[str, Any] = {}
    current_private = False
    nutrition_result: NutritionResolutionResult | None = None
    initial_reasoning_state = build_reasoning_state(
        user_input=effective_user_input,
        selected_evidence=[dict(item.get("raw") or {}) | {"query": str(item.get("query") or "")} for item in normalized_evidence],
        partial_grounding=partial_grounding,
        meal_template_hit=bool(meal_template),
        used_search=used_search,
        search_query=search_query,
        search_quality=search_quality,
        search_attempt_count=int(partial_grounding.get("search_attempt_count") or 0),
    )

    if decision_result.next_action == "run_clarify" and not decision_result.can_proceed_without_clarify:
        current_parsed = {
            "action_taken": "clarify_before_estimate",
            "confidence": "low",
            "exactness": "unknown",
            "tool_request": "none",
            "tool_request_reason": "",
            "title": str(canonical_meal_state.meal_title if canonical_meal_state else effective_user_input),
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
            "reasoning_state": initial_reasoning_state,
            "why_no_more_tools": str(initial_reasoning_state.get("why_current_evidence_is_insufficient") or ""),
            "reason_for_not_requesting_tool": "",
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
        packet_id = suggest_calibration_packet(effective_user_input)
        calibration_packet = get_meal_calibration(packet_id) if packet_id else None
        nutrition_payload = build_nutrition_resolution_payload(
            meal_state=canonical_meal_state,
            meal_link_result=task_meal_link_result,
            decision_result=decision_result,
            normalized_evidence=normalized_evidence,
            calibration_packet=calibration_packet,
            user_input=effective_user_input,
            partial_grounding=partial_grounding,
        )
        nutrition_payload["user_input"] = effective_user_input
        nutrition_payload["available_tools"] = available_tools
        nutrition_payload["risk_packet"] = risk_packet
        nutrition_payload["selected_evidence_summary"] = [
            {"title": item.get("title", ""), "source": item.get("source_type", "")}
            for item in selected_evidence_for_primary[:3]
        ]
        nutrition_payload["active_meal_context_allowed"] = active_meal_context_allowed
        nutrition_payload["meal_template_hit"] = bool(meal_template)
        nutrition_payload["old_components"] = (
            list(getattr(latest_log, "components_json", None) or [])
            if latest_log is not None and active_meal_context_allowed
            else []
        )
        fallback_primary_parsed = augment_followup_metadata(
            _normalize_structured_answer(
                None,
                user_text=effective_user_input,
                risk_packet=risk_packet,
                meal_template=meal_template,
            )
        )
        current_parsed, nutrition_envelope = await run_pass(
            provider=primary_llm,
            stage="nutrition_resolution_pass_initial" if round_index == 0 else "nutrition_resolution_pass_tool_round_2",
            system_prompt=NUTRITION_RESOLUTION_PROMPT
            + "\n\n[EVIDENCE_CONTEXT]\n"
            + evidence_context
            + "\n\n[CALIBRATION_CONTEXT]\n"
            + _calibration_context(calibration_packet)
            + "\n\n[RISK_CONTEXT]\n"
            + _risk_context(risk_packet),
            user_payload=nutrition_payload,
            max_tokens=primary_max_tokens,
            fallback_result=fallback_primary_parsed,
            normalize=lambda raw, fallback: augment_followup_metadata(
                _normalize_structured_answer(
                    raw,
                    user_text=effective_user_input,
                    risk_packet=risk_packet,
                    meal_template=meal_template,
                )
            ),
            dump=lambda result: dict(result),
            run_stage=run_stage,
            request_id=request_id,
            llm_traces=llm_traces,
            trigger_reason="nutrition_resolution" if round_index == 0 else "nutrition_tool_iteration",
            handoff_contract={
                "meal_link_action": task_meal_link_result.meal_link_action,
                "decision_next_action": decision_result.next_action,
                "evidence_count": len(selected_evidence_for_primary),
                "normalized_evidence_count": len(normalized_evidence),
            },
            required_fields=[
                "resolution_mode",
                "resolution_basis",
                "exactness",
                "estimate_mode",
                "confidence",
                "action_taken",
                "response_mode_hint",
            ],
            required_fields_source="normalized",
        )
        if nutrition_envelope.status != "success":
            debug_steps.append(
                {
                    "request_id": request_id,
                    "step": "nutrition_resolution_pass",
                    "stage": "nutrition_resolution_pass_initial" if round_index == 0 else "nutrition_resolution_pass_tool_round_2",
                    "status": nutrition_envelope.status,
                    "error": nutrition_envelope.error,
                }
            )

        prior_repair_notes: set[str] = set()
        repair_note = _nutrition_repair_note(parsed=current_parsed, nutrition_payload=nutrition_payload)
        while repair_note and repair_note not in prior_repair_notes and len(prior_repair_notes) < 2:
            prior_repair_notes.add(repair_note)
            current_parsed, nutrition_envelope = await run_pass(
                provider=primary_llm,
                stage="nutrition_resolution_pass_repair",
                system_prompt=NUTRITION_RESOLUTION_PROMPT
                + "\n\n[EVIDENCE_CONTEXT]\n"
                + evidence_context
                + "\n\n[CALIBRATION_CONTEXT]\n"
                + _calibration_context(calibration_packet)
                + "\n\n[RISK_CONTEXT]\n"
                + _risk_context(risk_packet)
                + "\n\n[REPAIR_NOTE]\n"
                + repair_note,
                user_payload=nutrition_payload,
                max_tokens=primary_max_tokens,
                fallback_result=current_parsed,
                normalize=lambda raw, fallback: augment_followup_metadata(
                    _normalize_structured_answer(
                        raw,
                        user_text=effective_user_input,
                        risk_packet=risk_packet,
                        meal_template=meal_template,
                    )
                ),
                dump=lambda result: dict(result),
                run_stage=run_stage,
                request_id=request_id,
                llm_traces=llm_traces,
                trigger_reason="nutrition_resolution_repair",
                handoff_contract={
                    "meal_link_action": task_meal_link_result.meal_link_action,
                    "decision_next_action": decision_result.next_action,
                    "evidence_count": len(selected_evidence_for_primary),
                    "normalized_evidence_count": len(normalized_evidence),
                    "repair_note": repair_note,
                },
                required_fields=[
                    "resolution_mode",
                    "resolution_basis",
                    "exactness",
                    "estimate_mode",
                    "confidence",
                    "action_taken",
                    "response_mode_hint",
                ],
                required_fields_source="normalized",
            )
            if nutrition_envelope.status != "success":
                debug_steps.append(
                    {
                        "request_id": request_id,
                        "step": "nutrition_resolution_pass_repair",
                        "status": nutrition_envelope.status,
                        "error": nutrition_envelope.error,
                    }
                )
            repair_note = _nutrition_repair_note(parsed=current_parsed, nutrition_payload=nutrition_payload)

        nutrition_result = nutrition_result_from_primary(
            {
                **current_parsed,
                "reasoning_state": dict(nutrition_payload.get("reasoning_state") or {}),
                "answer_payload": {
                    **dict(current_parsed.get("answer_payload") or {}),
                    "title": dict(current_parsed.get("answer_payload") or {}).get("title") or current_parsed.get("title"),
                    "components": dict(current_parsed.get("answer_payload") or {}).get("components") or current_parsed.get("components", []),
                    "estimated_kcal": dict(current_parsed.get("answer_payload") or {}).get("estimated_kcal", current_parsed.get("estimated_kcal", 0)),
                    "protein_g": dict(current_parsed.get("answer_payload") or {}).get("protein_g", current_parsed.get("protein_g", 0)),
                    "carb_g": dict(current_parsed.get("answer_payload") or {}).get("carb_g", current_parsed.get("carb_g", 0)),
                    "fat_g": dict(current_parsed.get("answer_payload") or {}).get("fat_g", current_parsed.get("fat_g", 0)),
                    "uncertainty_factors": dict(current_parsed.get("answer_payload") or {}).get(
                        "uncertainty_factors", current_parsed.get("uncertainty_factors", [])
                    ),
                    "base_estimated_kcal": dict(current_parsed.get("answer_payload") or {}).get(
                        "base_estimated_kcal", current_parsed.get("base_estimated_kcal")
                    ),
                    "base_protein_g": dict(current_parsed.get("answer_payload") or {}).get(
                        "base_protein_g", current_parsed.get("base_protein_g")
                    ),
                    "base_carb_g": dict(current_parsed.get("answer_payload") or {}).get(
                        "base_carb_g", current_parsed.get("base_carb_g")
                    ),
                    "base_fat_g": dict(current_parsed.get("answer_payload") or {}).get(
                        "base_fat_g", current_parsed.get("base_fat_g")
                    ),
                    "portion_multiplier": dict(current_parsed.get("answer_payload") or {}).get(
                        "portion_multiplier", current_parsed.get("portion_multiplier", 1.0)
                    ),
                    "portion_reason": dict(current_parsed.get("answer_payload") or {}).get(
                        "portion_reason", current_parsed.get("portion_reason", "")
                    ),
                    "items": dict(current_parsed.get("answer_payload") or {}).get("items", []),
                    "estimate_mode": current_parsed.get("estimate_mode"),
                    "exactness": current_parsed.get("exactness"),
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
        current_parsed["reasoning_state"] = dict(nutrition_payload.get("reasoning_state") or {})
        current_parsed["why_no_more_tools"] = str(current_parsed.get("why_no_more_tools") or "")
        current_parsed["reason_for_not_requesting_tool"] = str(current_parsed.get("reason_for_not_requesting_tool") or "")
        current_parsed = annotate_followup_policy(current_parsed)
        debug_steps.append({"request_id": request_id, "step": "nutrition_invariant_guard", **nutrition_guard_meta})
        current_private = _is_private_only_case(current_parsed, risk_packet, effective_user_input)

        if current_parsed.get("action_taken") != "request_tool":
            break

        requested_tool = str(current_parsed.get("tool_request") or "none")
        if (
            local_exact_truth_present
            and int(nutrition_payload.get("exact_brand_conflict_count") or 0) <= 0
            and requested_tool in {"search_official_nutrition", "read_official_doc_fragment"}
        ):
            current_parsed["tool_request"] = "none"
            requested_tool = "none"
        if requested_tool == "none":
            break

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
            break

        selected_evidence_for_primary = _merge_evidence_items(selected_evidence_for_primary, tool_evidence)
        normalized_evidence = [
            *normalized_evidence,
            *normalize_tool_evidence(tool_evidence, source_type=requested_tool, query=search_query or retrieval_query),
        ]
        partial_grounding = build_partial_grounding_packet(
            user_input=effective_user_input,
            planner_foods=[str(item) for item in planner_result.input_signals.get("foods", []) if str(item).strip()],
            selected_evidence=selected_evidence_for_primary,
        )
        partial_grounding["search_attempt_count"] = int(partial_grounding.get("search_attempt_count") or 0) + (1 if search_sources else 0)
        refreshed_reasoning_state = build_reasoning_state(
            user_input=effective_user_input,
            selected_evidence=[dict(item.get("raw") or {}) | {"query": str(item.get("query") or "")} for item in normalized_evidence],
            partial_grounding=partial_grounding,
            meal_template_hit=bool(meal_template),
            used_search=used_search,
            search_query=search_query,
            search_quality=search_quality,
            search_attempt_count=int(partial_grounding.get("search_attempt_count") or 0),
        )
        current_parsed["reasoning_state"] = refreshed_reasoning_state
        current_parsed = annotate_followup_policy(current_parsed)

    return NutritionLoopOutcome(
        current_parsed=current_parsed,
        nutrition_result=nutrition_result,
        selected_evidence_for_primary=selected_evidence_for_primary,
        normalized_evidence=normalized_evidence,
        partial_grounding=partial_grounding,
        used_search=used_search,
        search_query=search_query,
        search_quality=search_quality,
        sources=sources,
        current_private=current_private,
    )
