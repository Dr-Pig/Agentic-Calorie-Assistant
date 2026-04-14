from __future__ import annotations

import json
import re
import unicodedata
from typing import Any

from ..domain import CanonicalMealState, ConversationState, PlannerContextPayload
from ..schemas import ContextPackTrace, DecisionPassResult, NutritionResolutionResult, PlanningBrief, TaskMealLinkResult, TurnState

# Re-exports to maintain compatibility for legacy consumers
from .context_normalizer import (
    canonicalize_lookup_text,
    extract_drink_customization_clues,
    extract_portion_clues,
    has_packaged_drink_identity_cue,
    looks_like_standardized_drink,
    lookup_key,
    lookup_tokens,
    normalize_text,
    normalize_user_input_for_estimation,
)
from .pass_payload_policies import (
    has_explicit_exact_brand_hint,
    should_soft_avoid_exact_for_generic_drink,
)
from .planner_context_assembler import (
    build_planner_context_payload,
    build_turn_state,
    normalized_input_from_debug_steps,
    render_conversation_state_prompt,
)
from .context_pack_builder import (
    _compact_chunk,
    _compact_open_meal,
    build_context_pack_trace,
    estimate_token_count,
)


def knowledge_context(snippets: list[dict[str, Any]]) -> str:
    if not snippets:
        return "- No supporting evidence was retrieved."
    lines = [
        "| ID | Item | Lane | Tier | Identity | Kcal | Note |",
        "|:---|:---|:---|:---|:---|:---|:---|",
    ]
    for item in snippets[:5]:
        evidence_id = str(item.get("evidence_id") or "")
        title = str(item.get("title") or item.get("name") or "")
        lane = str(item.get("retrieval_lane") or "support_lane")
        tier = str(item.get("source_tier") or "")
        identity = str(item.get("identity_confidence") or item.get("match_confidence") or "none")
        kcal = item.get("label_kcal") or item.get("kcal") or ""
        note = str(item.get("snippet") or item.get("summary") or item.get("note") or "").replace("\n", " ").strip()
        lines.append(f"| {evidence_id} | {title} | {lane} | {tier} | {identity} | {kcal} | {note} |")
    return "\n".join(lines)


def risk_context(packet: dict[str, Any]) -> str:
    lines: list[str] = []
    if packet.get("risk_flags"):
        lines.append(f"- risk_flags: {', '.join(str(item) for item in packet['risk_flags'])}")
    for item in packet.get("review_focus", []):
        lines.append(f"- review_focus: {item}")
    for item in packet.get("must_ask_if_uncertain", []):
        lines.append(f"- must_ask_if_uncertain: {item}")
    for item in packet.get("portion_clues", {}).get("review_focus", []):
        lines.append(f"- portion_review_focus: {item}")
    return "\n".join(lines) if lines else "- no additional risk context"


def calibration_context(packet: dict[str, Any]) -> str:
    """Format calibration packet for LLM context in system prompt."""
    if not packet:
        return "- No specific calibration context for this dish type."
    lines = []
    title = packet.get("title", "")
    if title:
        lines.append(f"[{title}]")
    bias_notes = packet.get("bias_notes", [])
    if bias_notes:
        for note in bias_notes:
            lines.append(f"- 注意: {note}")
    high_calorie = packet.get("high_calorie_sources", [])
    if high_calorie:
        lines.append(f"- 高熱量來源: {', '.join(str(item) for item in high_calorie)}")
    adjustment = packet.get("typical_adjustment_range", {})
    if adjustment:
        low = adjustment.get("kcal_delta_low", "")
        high = adjustment.get("kcal_delta_high", "")
        if low and high:
            lines.append(f"- 典型調整範圍: +{low} ~ +{high} kcal")
    return "\n".join(lines) if lines else "- No specific calibration context for this dish type."


def build_dynamic_system_addition(*, selected_evidence_summary: list[dict[str, Any]], risk_packet: dict[str, Any]) -> dict[str, Any]:
    return {
        "selected_evidence_summary": selected_evidence_summary,
        "risk_flags": risk_packet.get("risk_flags", []),
        "required_checks": risk_packet.get("required_checks", {}),
    }


def build_boundary_features(*, state: ConversationState, latest_log: Any | None) -> dict[str, Any]:
    return {
        "time_gap_seconds": int(state.active_meal_time_gap_seconds or 0),
        "pending_question_present": bool(
            (getattr(latest_log, "pending_question", None) if latest_log is not None else None)
            or state.pending_question
            or state.planner_state_digest.pending_question
        ),
        "active_meal_exists": bool(latest_log or state.active_meal_summary.meal_title),
        "active_meal_status": str(getattr(latest_log, "status", "") or ""),
        "transcript_link_hit_count": len([chunk for chunk in state.retrieved_transcript_chunks if str(chunk.linked_meal_id or "").strip()]),
        "meal_record_hit_count": len(state.retrieved_meal_records),
    }


def build_task_meal_link_payload(
    *,
    user_input: str,
    state: ConversationState,
    meal_log_summaries: list[dict[str, Any]],
    boundary_features: dict[str, Any],
) -> dict[str, Any]:
    return {
        "current_user_input": user_input,
        "recent_transcript": [_compact_chunk(chunk) for chunk in state.retrieved_transcript_chunks[:4]],
        "open_unresolved_meals": [
            _compact_open_meal(meal)
            for meal in state.retrieved_meal_records
            if str(getattr(meal, "status", "") or "") == "draft_unresolved"
        ][:3],
        "meal_log_summaries": meal_log_summaries[:5],
        "boundary_features": boundary_features,
        "active_meal_summary": state.active_meal_summary.model_dump(mode="json"),
        "linking_policy": {
            "prefer_create_new_meal_for_complete_intake": True,
            "attach_only_for_clear_continuation_or_pending_question_answer": True,
            "older_unresolved_meals_are_context_not_override": True,
        },
    }


def build_decision_payload(
    *,
    user_input: str,
    meal_state: CanonicalMealState | None,
    meal_link_result: TaskMealLinkResult,
    selected_evidence_summary: list[dict[str, Any]],
    available_tools: list[str],
    planning_brief: PlanningBrief | None = None,
) -> dict[str, Any]:
    from ..application.evidence_assembly import (
        build_attested_evidence_blocks,
        build_reasoning_state,
        infer_brand_hint,
        infer_candidate_relationship,
        infer_query_alignment,
        infer_variant_type,
        retrieval_lane_for_item,
        split_evidence_lanes,
    )
    portion_clues = extract_portion_clues(user_input)
    standardized_drink_like = looks_like_standardized_drink(user_input, selected_evidence_summary)
    drink_customization_clues = extract_drink_customization_clues(user_input) if standardized_drink_like else []
    lane_split = split_evidence_lanes(selected_evidence_summary)
    exact_truth_candidates = []
    for item in lane_split["exact_lane"]:
        exact_truth_candidates.append(
            {
                "title": str(item.get("title") or ""),
                "brand": str(item.get("brand") or ""),
                "source_class": str(item.get("source_class") or ""),
                "identity_confidence": str(item.get("identity_confidence") or "none"),
                "serving_basis": str(item.get("serving_basis") or ""),
                "kcal": item.get("kcal"),
                "match_path": str(item.get("match_path") or ""),
                "brand_hint": str(item.get("brand_hint") or infer_brand_hint(item, query=user_input)),
                "query_alignment": str(item.get("query_alignment") or infer_query_alignment(item, query=user_input)),
                "variant_type": str(item.get("variant_type") or infer_variant_type(item, query=user_input)),
                "candidate_relationship": str(item.get("candidate_relationship") or infer_candidate_relationship(item, query=user_input)),
                "retrieval_lane": retrieval_lane_for_item(item),
                "aliases": [str(alias) for alias in item.get("aliases", []) if str(alias).strip()][:5],
            }
        )
    exact_match_paths = [
        str(item.get("match_path") or "").strip()
        for item in exact_truth_candidates
        if str(item.get("match_path") or "").strip()
    ]
    packaged_exact_candidate_count = sum(1 for item in exact_truth_candidates if str(item.get("variant_type") or "") == "packaged_retail")
    exact_brand_hints = sorted({str(item.get("brand_hint") or "").strip() for item in exact_truth_candidates if str(item.get("brand_hint") or "").strip()})
    core_default_candidates = [item for item in exact_truth_candidates if str(item.get("variant_type") or "") == "core_default"]
    generic_drink_soft_avoid_exact = should_soft_avoid_exact_for_generic_drink(
        user_input=user_input,
        standardized_drink_like=standardized_drink_like,
        packaged_exact_candidate_count=packaged_exact_candidate_count,
        exact_brand_hints=exact_brand_hints,
    )
    attested_evidence_blocks = build_attested_evidence_blocks(selected_evidence_summary, query=user_input, limit=8)
    reasoning_state = build_reasoning_state(
        user_input=user_input,
        selected_evidence=selected_evidence_summary,
        partial_grounding=None,
        meal_template_hit=False,
    )
    scoped_meal_state = (
        meal_state.model_dump(mode="json")
        if meal_state and meal_link_result.meal_link_action == "attach_to_existing_meal"
        else {}
    )
    return {
        "current_user_input": user_input,
        "portion_clues": portion_clues,
        "drink_customization_clues": drink_customization_clues,
        "standardized_drink_like": standardized_drink_like,
        "cup_size_provided": bool(portion_clues),
        "exact_truth_candidate_count": len(exact_truth_candidates),
        "exact_match_paths": exact_match_paths[:5],
        "packaged_exact_candidate_count": packaged_exact_candidate_count,
        "exact_brand_hints": exact_brand_hints,
        "explicit_brand_cue_from_user": has_explicit_exact_brand_hint(user_input, exact_brand_hints),
        "packaged_drink_identity_cue": has_packaged_drink_identity_cue(user_input),
        "generic_drink_soft_avoid_exact": generic_drink_soft_avoid_exact,
        "exact_brand_conflict_count": max(0, len(exact_brand_hints) - 1),
        "core_default_candidate_count": len(core_default_candidates),
        "canonical_meal_state": scoped_meal_state,
        "meal_link_result": meal_link_result.model_dump(mode="json"),
        "selected_evidence_summary": selected_evidence_summary,
        "attested_evidence_blocks": attested_evidence_blocks,
        "reasoning_state": reasoning_state,
        "evidence_gap_state": reasoning_state,
        "observation_summary": dict(reasoning_state.get("observation_summary") or {}),
        "exact_lane_candidates": exact_truth_candidates[:5],
        "anchor_lane_candidates": lane_split["anchor_lane"][:5],
        "template_lane_hits": lane_split["template_lane"][:5],
        "evidence_policy": {
            "source_priority": [
                "tier_1_exact_verified",
                "tier_2_context_verified",
                "tier_3_anchor_prior",
                "tier_4_web_nonexact",
                "tier_5_model_context",
            ],
            "cite_evidence_ids_in_reasoning": True,
            "prefer_attested_evidence_over_model_knowledge": True,
        },
        "exact_truth_available": bool(exact_truth_candidates),
        "exact_truth_candidates": exact_truth_candidates[:5],
        "available_tools": available_tools,
        "planning_brief": planning_brief.model_dump(mode="json") if planning_brief else {},
        "slot_state": planning_brief.slot_state if planning_brief else None,
    }


def build_nutrition_resolution_payload(
    *,
    meal_state: CanonicalMealState | None,
    meal_link_result: TaskMealLinkResult,
    decision_result: DecisionPassResult,
    normalized_evidence: list[dict[str, Any]],
    calibration_packet: dict[str, Any] | None,
    user_input: str,
    partial_grounding: dict[str, Any] | None = None,
) -> dict[str, Any]:
    from ..application.evidence_assembly import (
        build_attested_evidence_blocks,
        build_reasoning_state,
        infer_brand_hint,
        infer_candidate_relationship,
        infer_query_alignment,
        infer_variant_type,
        retrieval_lane_for_item,
        split_evidence_lanes,
    )
    portion_clues = extract_portion_clues(user_input)
    standardized_drink_like = looks_like_standardized_drink(user_input, [dict(item.get("raw") or {}) for item in normalized_evidence])
    drink_customization_clues = extract_drink_customization_clues(user_input) if standardized_drink_like else []
    raw_items = [dict(item.get("raw") or {}) | {"query": str(item.get("query") or "")} for item in normalized_evidence]
    lane_split = split_evidence_lanes(raw_items)
    exact_truth_candidates = []
    for raw in lane_split["exact_lane"]:
        exact_truth_candidates.append(
            {
                "title": str(raw.get("title") or ""),
                "brand": str(raw.get("brand") or ""),
                "kcal": raw.get("label_kcal") or raw.get("kcal"),
                "label_macros": raw.get("label_macros") or raw.get("macros") or {},
                "match_quality": str(
                    raw.get("match_confidence")
                    or raw.get("identity_confidence")
                    or raw.get("match_quality")
                    or "unknown"
                ),
                "match_path": str(raw.get("match_path") or ""),
                "source_class": str(raw.get("source_class") or raw.get("source_type") or ""),
                "portion_basis_quality": str(raw.get("portion_basis_quality") or ""),
                "serving_basis": str(raw.get("serving_basis") or raw.get("portion_basis") or raw.get("serving_size") or ""),
                "brand_hint": str(raw.get("brand_hint") or infer_brand_hint(raw, query=user_input)),
                "query_alignment": str(raw.get("query_alignment") or infer_query_alignment(raw, query=user_input)),
                "variant_type": str(raw.get("variant_type") or infer_variant_type(raw, query=user_input)),
                "candidate_relationship": str(raw.get("candidate_relationship") or infer_candidate_relationship(raw, query=user_input)),
                "retrieval_lane": retrieval_lane_for_item(raw),
                "aliases": [str(alias) for alias in raw.get("aliases", []) if str(alias).strip()][:5],
            }
        )
    exact_match_paths = [
        str(item.get("match_path") or "").strip()
        for item in exact_truth_candidates
        if str(item.get("match_path") or "").strip()
    ]
    packaged_exact_candidate_count = sum(1 for item in exact_truth_candidates if str(item.get("variant_type") or "") == "packaged_retail")
    exact_brand_hints = sorted({str(item.get("brand_hint") or "").strip() for item in exact_truth_candidates if str(item.get("brand_hint") or "").strip()})
    core_default_candidates = [item for item in exact_truth_candidates if str(item.get("variant_type") or "") == "core_default"]
    generic_drink_soft_avoid_exact = should_soft_avoid_exact_for_generic_drink(
        user_input=user_input,
        standardized_drink_like=standardized_drink_like,
        packaged_exact_candidate_count=packaged_exact_candidate_count,
        exact_brand_hints=exact_brand_hints,
    )
    attested_evidence_blocks = build_attested_evidence_blocks(
        raw_items,
        query=user_input,
        limit=10,
    )
    meal_template_hit = bool((partial_grounding or {}).get("template_lane_hits")) or str((partial_grounding or {}).get("store_hint") or "").strip() != ""
    reasoning_state = build_reasoning_state(
        user_input=user_input,
        selected_evidence=raw_items,
        partial_grounding=partial_grounding or {},
        meal_template_hit=meal_template_hit,
        used_search=bool(any(str(item.get("source_class") or "") in {"web_search_official", "web_search_nonexact"} for item in raw_items)),
        search_query=next((str(item.get("query") or "") for item in normalized_evidence if str(item.get("query") or "").strip()), None),
        search_quality=next((item.get("search_quality") for item in normalized_evidence if item.get("search_quality") is not None), None),
        search_attempt_count=int((partial_grounding or {}).get("search_attempt_count") or 0),
    )
    scoped_meal_state = (
        meal_state.model_dump(mode="json")
        if meal_state and meal_link_result.meal_link_action == "attach_to_existing_meal"
        else {}
    )
    return {
        "current_user_input": user_input,
        "portion_clues": portion_clues,
        "drink_customization_clues": drink_customization_clues,
        "standardized_drink_like": standardized_drink_like,
        "cup_size_provided": bool(portion_clues),
        "exact_truth_candidate_count": len(exact_truth_candidates),
        "exact_match_paths": exact_match_paths[:5],
        "packaged_exact_candidate_count": packaged_exact_candidate_count,
        "exact_brand_hints": exact_brand_hints,
        "explicit_brand_cue_from_user": has_explicit_exact_brand_hint(user_input, exact_brand_hints),
        "packaged_drink_identity_cue": has_packaged_drink_identity_cue(user_input),
        "generic_drink_soft_avoid_exact": generic_drink_soft_avoid_exact,
        "exact_brand_conflict_count": max(0, len(exact_brand_hints) - 1),
        "core_default_candidate_count": len(core_default_candidates),
        "canonical_meal_state": scoped_meal_state,
        "meal_link_result": meal_link_result.model_dump(mode="json"),
        "decision_result": decision_result.model_dump(mode="json"),
        "normalized_evidence": normalized_evidence,
        "attested_evidence_blocks": attested_evidence_blocks,
        "reasoning_state": reasoning_state,
        "evidence_gap_state": reasoning_state,
        "observation_summary": dict(reasoning_state.get("observation_summary") or {}),
        "exact_lane_candidates": exact_truth_candidates[:5],
        "anchor_lane_candidates": lane_split["anchor_lane"][:8],
        "template_lane_hits": lane_split["template_lane"][:8],
        "evidence_policy": {
            "source_priority": [
                "tier_1_exact_verified",
                "tier_2_context_verified",
                "tier_3_anchor_prior",
                "tier_4_web_nonexact",
                "tier_5_model_context",
            ],
            "cite_evidence_ids_in_reasoning": True,
            "prefer_attested_evidence_over_model_knowledge": True,
            "conflict_policy": "prefer_higher_tier_same_item_evidence; verified exact evidence beats context memory; verified context beats generic priors; generic priors beat weak web; never let lower-tier sibling evidence override higher-tier exact evidence",
        },
        "exact_truth_available": bool(exact_truth_candidates),
        "exact_truth_candidates": exact_truth_candidates[:5],
        "calibration_packet": calibration_packet or {},
        "partial_grounding": partial_grounding or {},
        "meal_template_hit": meal_template_hit,
        "active_unresolved_meal_id": (
            meal_state.meal_id
            if meal_state
            and meal_link_result.meal_link_action == "attach_to_existing_meal"
            and meal_state.status != "completed_meal"
            else None
        ),
    }


def build_four_pass_final_response_payload(
    *,
    user_input: str,
    task_meal_link_result: TaskMealLinkResult,
    decision_result: DecisionPassResult,
    nutrition_result: NutritionResolutionResult,
    active_meal_summary: dict[str, Any],
) -> dict[str, Any]:
    return {
        "user_input": user_input,
        "task_meal_link_result": task_meal_link_result.model_dump(mode="json"),
        "decision_result": decision_result.model_dump(mode="json"),
        "nutrition_result": nutrition_result.model_dump(mode="json"),
        "active_meal_summary": active_meal_summary,
    }
