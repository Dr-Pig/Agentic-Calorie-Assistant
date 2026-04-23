"""Nutrition resolution payload builder extracted from context_assembly."""
from __future__ import annotations

from typing import Any

from app.shared.domain import CanonicalMealState
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


def build_nutrition_resolution_payload(
    *,
    meal_state: CanonicalMealState | None,
    meal_link_result: TaskMealLinkResult,
    decision_result: ToolRoutingDecision,
    normalized_evidence: list[dict[str, Any]],
    calibration_packet: dict[str, Any] | None,
    user_input: str,
    partial_grounding: dict[str, Any] | None = None,
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
