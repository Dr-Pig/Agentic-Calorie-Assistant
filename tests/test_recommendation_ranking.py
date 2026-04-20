from __future__ import annotations

from app.application.recommendation_candidate_spec import build_recommendation_candidate_spec
from app.application.recommendation_candidate_retrieval import RecommendationCandidateRetrievalResult
from app.application.recommendation_context import build_recommendation_context
from app.application.recommendation_ranking import build_recommendation_ranking_and_synthesis
from app.domain import ActiveBodyPlanView, CurrentBudgetView, ProposalContainer
from app.infrastructure.preference_profile_persistence import PreferenceFacet, PreferenceProfileSummary
from app.schemas import RecommendationCandidate


def _candidate(
    candidate_id: str,
    *,
    title: str,
    estimated_kcal: int,
    retrieval_tier: str,
    item_kind: str = "meal",
    staple_type: str = "rice",
    cuisine_family: str = "taiwanese",
    store_name: str | None = None,
    protein_g: int = 20,
    protein_posture: str = "balanced",
) -> RecommendationCandidate:
    return RecommendationCandidate(
        candidate_id=candidate_id,
        candidate_kind="golden_order",
        title=title,
        store_name=store_name,
        estimated_kcal=estimated_kcal,
        protein_g=protein_g,
        fit_summary="fit",
        source_metadata={
            "retrieval_tier": retrieval_tier,
            "item_kind": item_kind,
            "staple_type": staple_type,
            "cuisine_family": cuisine_family,
            "protein_posture": protein_posture,
        },
    )


def test_recommendation_ranking_applies_hard_constraints_before_soft_preferences() -> None:
    context = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-18",
            budget_kcal=1600,
            consumed_kcal=1080,
            remaining_kcal=520,
            active_meal_count=2,
        ),
        active_body_plan_view=ActiveBodyPlanView(user_id=1, daily_budget_kcal=1600),
        preference_profile_summary=PreferenceProfileSummary(
            user_id=1,
            generated_at=None,
            common_store_names=(PreferenceFacet(value="favorite ramen", count=4),),
            freshness_posture="fresh",
        ),
        raw_user_input="晚餐吃什麼",
    )
    retrieval_result = RecommendationCandidateRetrievalResult(
        candidate_items=[
            _candidate(
                "preferred-but-over",
                title="Favorite Ramen",
                store_name="Favorite Ramen",
                estimated_kcal=760,
                retrieval_tier="historical_match",
                cuisine_family="japanese",
            ),
            _candidate(
                "budget-fit",
                title="Chicken Bento",
                store_name="Bento House",
                estimated_kcal=500,
                retrieval_tier="safe_fallback",
                protein_g=30,
                protein_posture="high_protein",
            ),
        ],
        candidate_source_summary={},
        candidate_filter_reasons={},
        candidate_count=2,
    )

    result = build_recommendation_ranking_and_synthesis(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        retrieval_result=retrieval_result,
    )

    assert result.top_pick is not None
    assert result.top_pick.candidate_id == "budget-fit"
    assert "preferred-but-over" in result.filter_reasons
    assert "exceeds_remaining_budget" in result.filter_reasons["preferred-but-over"]


def test_recommendation_ranking_uses_soft_preferences_to_break_ties() -> None:
    context = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-18",
            budget_kcal=1800,
            consumed_kcal=900,
            remaining_kcal=900,
            active_meal_count=1,
        ),
        active_body_plan_view=ActiveBodyPlanView(user_id=1, daily_budget_kcal=1800),
        preference_profile_summary=PreferenceProfileSummary(
            user_id=1,
            generated_at=None,
            common_store_names=(PreferenceFacet(value="Bowl Lab", count=4),),
            common_cuisine_families=(PreferenceFacet(value="japanese", count=3),),
            protein_posture_preference="high_protein",
            freshness_posture="fresh",
        ),
        raw_user_input="推薦晚餐",
    )
    retrieval_result = RecommendationCandidateRetrievalResult(
        candidate_items=[
            _candidate(
                "store-fit",
                title="Chicken Bowl",
                store_name="Bowl Lab",
                estimated_kcal=620,
                retrieval_tier="historical_match",
                cuisine_family="japanese",
                protein_g=32,
                protein_posture="high_protein",
            ),
            _candidate(
                "plain-fit",
                title="Pasta Plate",
                store_name="Cafe X",
                estimated_kcal=610,
                retrieval_tier="historical_match",
                cuisine_family="western",
                protein_g=18,
                protein_posture="balanced",
            ),
        ],
        candidate_source_summary={},
        candidate_filter_reasons={},
        candidate_count=2,
    )

    result = build_recommendation_ranking_and_synthesis(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        retrieval_result=retrieval_result,
    )

    assert result.top_pick is not None
    assert result.top_pick.candidate_id == "store-fit"
    assert result.backup_picks[0].candidate_id == "plain-fit"


def test_recommendation_ranking_filters_excess_when_rescue_is_active() -> None:
    context = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-18",
            budget_kcal=1500,
            consumed_kcal=1050,
            remaining_kcal=450,
            active_meal_count=2,
        ),
        active_body_plan_view=ActiveBodyPlanView(user_id=1, daily_budget_kcal=1500),
        open_proposals=[ProposalContainer(proposal_type="rescue", proposal_status="open")],
        raw_user_input="幫我推薦晚餐",
    )
    retrieval_result = RecommendationCandidateRetrievalResult(
        candidate_items=[
            _candidate(
                "too-big",
                title="Pork Rice",
                estimated_kcal=520,
                retrieval_tier="nearby",
            ),
            _candidate(
                "legal",
                title="Tofu Set",
                estimated_kcal=380,
                retrieval_tier="safe_fallback",
                protein_g=24,
                protein_posture="high_protein",
            ),
        ],
        candidate_source_summary={},
        candidate_filter_reasons={},
        candidate_count=2,
    )

    result = build_recommendation_ranking_and_synthesis(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        retrieval_result=retrieval_result,
    )

    assert result.top_pick is not None
    assert result.top_pick.candidate_id == "legal"
    assert "too-big" in result.filter_reasons
    assert "exceeds_rescue_overlay_budget" in result.filter_reasons["too-big"]
