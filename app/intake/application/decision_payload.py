"""Intake decision payload builders extracted from context_assembly."""
from __future__ import annotations

from typing import Any

from app.shared.domain import CanonicalMealState, ConversationState
from app.nutrition.application.context_normalizer import (
    extract_drink_customization_clues,
    extract_portion_clues,
    has_packaged_drink_identity_cue,
    looks_like_standardized_drink,
)
from app.nutrition.application.payload_policies import (
    has_explicit_exact_brand_hint,
    should_soft_avoid_exact_for_generic_drink,
)
from app.runtime.application.context_pack_builder import _compact_chunk, _compact_open_meal


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
    
) -> dict[str, Any]:
    from app.nutrition.application.evidence_assembly import (
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
