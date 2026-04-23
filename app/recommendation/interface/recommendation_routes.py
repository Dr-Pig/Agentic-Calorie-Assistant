from __future__ import annotations

from dataclasses import asdict

from fastapi import APIRouter, Depends

from ...body.application import build_active_body_plan_view
from ...budget.application import build_current_budget_view
from ..application import (
    build_recommendation_candidates,
    build_recommendation_candidate_spec,
    build_recommendation_context,
    build_recommendation_ranking_and_synthesis,
    build_recommendation_response,
)
from ...database import get_db, get_or_create_user
from ...schemas import RecommendationCandidate

router = APIRouter()


def _preview_candidates(*, remaining_budget_kcal: int) -> list[RecommendationCandidate]:
    safe_budget = max(0, int(remaining_budget_kcal or 0))
    return [
        RecommendationCandidate(
            candidate_id="preview-historical-1",
            candidate_kind="golden_order",
            title="Chicken salad bowl",
            store_name="Fresh Box",
            estimated_kcal=min(safe_budget, 430) if safe_budget > 0 else 430,
            protein_g=32,
            fit_summary="high_protein",
            source_metadata={
                "item_kind": "salad",
                "staple_type": "salad",
                "cuisine_family": "western",
                "protein_posture": "high_protein",
                "retrieval_tier": "historical_match",
                "venue_type": "restaurant",
            },
        ),
        RecommendationCandidate(
            candidate_id="preview-nearby-1",
            candidate_kind="nearby",
            title="Hot chicken rice box",
            store_name="Local Bento",
            estimated_kcal=max(520, min(safe_budget, 620)) if safe_budget > 0 else 620,
            protein_g=26,
            fit_summary="balanced",
            source_metadata={
                "item_kind": "main_meal",
                "staple_type": "rice",
                "cuisine_family": "taiwanese",
                "protein_posture": "balanced",
                "retrieval_tier": "nearby",
                "venue_type": "restaurant",
            },
        ),
        RecommendationCandidate(
            candidate_id="preview-safe-1",
            candidate_kind="safe_fallback",
            title="Protein drink and egg",
            store_name="Convenience Store",
            estimated_kcal=210,
            protein_g=18,
            fit_summary="light",
            source_metadata={
                "item_kind": "snack",
                "staple_type": "light",
                "cuisine_family": "convenience",
                "protein_posture": "high_protein",
                "retrieval_tier": "safe_fallback",
                "venue_type": "convenience_store",
            },
        ),
    ]


@router.get("/recommendation/preview")
def recommendation_preview(
    user_id: str,
    local_date: str,
    raw_user_input: str = "",
    db=Depends(get_db),
) -> dict[str, object]:
    user = get_or_create_user(db, user_id)
    current_budget_view = build_current_budget_view(db, user_id=user.id, local_date=local_date)
    active_body_plan_view = build_active_body_plan_view(db, user_id=user.id)
    context_packet = build_recommendation_context(
        user_id=user.id,
        current_budget_view=current_budget_view,
        active_body_plan_view=active_body_plan_view,
        raw_user_input=raw_user_input,
    )
    candidate_spec = build_recommendation_candidate_spec(
        context_packet=context_packet,
    )
    retrieval_result = build_recommendation_candidates(
        context_packet=context_packet,
        candidate_spec=candidate_spec,
        historical_matches=_preview_candidates(
            remaining_budget_kcal=context_packet.hard_constraints.remaining_budget_kcal
        ),
    )
    ranking_result = build_recommendation_ranking_and_synthesis(
        context_packet=context_packet,
        candidate_spec=candidate_spec,
        retrieval_result=retrieval_result,
    )
    response_packet = build_recommendation_response(
        context_packet=context_packet,
        ranking_result=ranking_result,
    )
    return {
        "context_packet": asdict(context_packet),
        "candidate_spec": asdict(candidate_spec),
        "candidate_count": retrieval_result.candidate_count,
        "candidate_spec_used": retrieval_result.candidate_spec_used,
        "ranking_explanation": ranking_result.ranking_explanation,
        "filter_reasons": ranking_result.filter_reasons,
        "response": response_packet.response.model_dump(mode="json"),
        "asked_follow_up": response_packet.asked_follow_up,
        "ui_hints": response_packet.ui_hints,
    }
