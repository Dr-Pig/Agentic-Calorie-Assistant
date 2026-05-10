from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from app.nutrition.application.estimate_artifacts import EstimatedNutritionArtifact
from app.nutrition.application.fooddb_retrieval_artifact_parts import (
    approved_fooddb_trace,
    build_fooddb_followup_artifact,
    candidate_component,
    component_breakdown_item,
    fooddb_request_context,
    source_lane,
)
from app.shared.contracts.intake import EstimatePayload


def build_fooddb_retrieval_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    retrieval_result: dict[str, Any],
) -> EstimatedNutritionArtifact | None:
    boundary = str(retrieval_result.get("retrieval_boundary") or "").strip()
    candidates = [
        dict(item)
        for item in retrieval_result.get("accepted_candidates") or []
        if isinstance(item, dict) and item.get("runtime_truth_allowed") is True
    ]
    rejected = [dict(item) for item in retrieval_result.get("rejected_candidates") or [] if isinstance(item, dict)]
    if boundary == "bare_basket_ask_followup_no_estimate":
        return build_fooddb_followup_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date,
            retrieval_result=retrieval_result,
        )
    if boundary == "listed_basket_component_recall" and rejected:
        return build_fooddb_followup_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date,
            retrieval_result=retrieval_result,
            source_lane_value="listed_component",
        )
    if any(candidate.get("requires_manager_disambiguation") is True for candidate in candidates):
        return build_fooddb_followup_artifact(
            db,
            user_external_id=user_external_id,
            raw_user_input=raw_user_input,
            local_date=local_date,
            retrieval_result=retrieval_result,
            source_lane_value=source_lane(candidates),
            evidence_ids=[
                str(candidate.get("anchor_id") or "")
                for candidate in candidates
                if candidate.get("anchor_id")
            ],
            followup_reasoning="fooddb_candidate_requires_manager_disambiguation",
            disambiguation_required=True,
        )
    if not candidates:
        return None
    return _build_fooddb_candidate_artifact(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
        local_date=local_date,
        retrieval_result=retrieval_result,
        candidates=candidates,
    )


def _build_fooddb_candidate_artifact(
    db: Session,
    *,
    user_external_id: str,
    raw_user_input: str,
    local_date: str,
    retrieval_result: dict[str, Any],
    candidates: list[dict[str, Any]],
) -> EstimatedNutritionArtifact:
    request, runtime_context = fooddb_request_context(
        db,
        user_external_id=user_external_id,
        raw_user_input=raw_user_input,
    )
    source_lane_value = source_lane(candidates)
    components = [candidate_component(candidate, source_lane_value=source_lane_value) for candidate in candidates]
    estimated_kcal = sum(int(component.estimated_kcal or 0) for component in components)
    evidence_ids = [item for component in components for item in component.evidence_ids if item]
    retrieval_boundary = str(retrieval_result.get("retrieval_boundary") or "")
    approved_trace = approved_fooddb_trace(
        source_lane_value=source_lane_value,
        retrieval_boundary=retrieval_boundary,
        evidence_ids=evidence_ids,
        macro_visible=False,
        runtime_truth_allowed=True,
    )
    meal_title = " + ".join(component.name for component in components) or raw_user_input
    payload = EstimatePayload(
        request_id="intake_execution-approved-fooddb-packet",
        meal_title=meal_title,
        components=[component.name for component in components],
        component_estimates=components,
        component_breakdown=[
            component_breakdown_item(component, candidate=candidate, source_lane_value=source_lane_value)
            for component, candidate in zip(components, candidates, strict=True)
        ],
        estimated_kcal=estimated_kcal,
        protein_g=0,
        carb_g=0,
        fat_g=0,
        evidence_ids_used=evidence_ids,
        source_decision="ready",
        answer_mode="direct_answer",
        action_taken="direct_answer",
        route_target="direct_answer",
        reply_text=f"{meal_title} about {estimated_kcal} kcal.",
        best_answer_source="approved_fooddb_packet",
        best_estimate_mode="anchored_component",
        estimate_confidence_tier="medium",
        retrieved_evidence_summary=[
            {
                "title": component.name,
                "source_class": "approved_fooddb_packet",
                "source_lane": source_lane_value,
                "evidence_role": component.evidence_role,
            }
            for component in components
        ],
        sources=[
            {
                "source_class": "approved_fooddb_packet",
                "source_type": source_lane_value,
                "title": meal_title,
            }
        ],
        trace_contract={
            "local_date": local_date,
            "occurred_at": f"{local_date}T12:00:00+08:00",
            "timezone": "Asia/Taipei",
            "route_family": "food_logging",
            "response_mode_hint": "rough_estimate_ok",
            "db_hit_type": "approved_fooddb_packet",
            "approved_fooddb_evidence_trace": approved_trace,
            "macro_display_authorized": False,
            "macro_visibility_status": "hidden_missing_source",
            "macro_guard_reason": "no_macro_data",
            "grounding_summary": {
                "exact_truth_present": False,
                "retrieved_knowledge_count": len(components),
                "evidence_roles": [
                    "ingredient_anchor" if source_lane_value == "listed_component" else "meal_pattern_prior"
                ],
            },
            "reasoning_state": {
                "exact_lane_count": 0,
                "search_attempt_count": 0,
            },
            "search_attempt_count": 0,
            "search_query": None,
            "websearch_evidence_used": False,
            "shadow_stub": False,
        },
    )
    return EstimatedNutritionArtifact(request=request, runtime_context=runtime_context, payload=payload)
__all__ = ["build_fooddb_retrieval_artifact"]
