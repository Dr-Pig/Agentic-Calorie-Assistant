from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.application.onboarding_service import OnboardingBootstrapInput, bootstrap_body_plan_for_date
from app.application.recommendation_candidate_retrieval import build_recommendation_candidates
from app.application.recommendation_candidate_spec import build_recommendation_candidate_spec
from app.application.recommendation_candidate_retrieval import RecommendationCandidateRetrievalResult
from app.application.recommendation_context import build_recommendation_context
from app.application.recommendation_ranking import build_recommendation_ranking_and_synthesis
from app.application.recommendation_response import build_recommendation_response
from app.database import get_or_create_user
from app.domain import ActiveBodyPlanView, CurrentBudgetView
from app.infrastructure.canonical_persistence import commit_meal_payload_to_canonical
from app.infrastructure.preference_profile_persistence import PreferenceFacet, PreferenceProfileSummary
from app.models import Base, BodyPlanRecord, DayBudgetLedgerRecord, MealThreadRecord
from app.schemas import CommitRequestCandidate, RecommendationCandidate


def _session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    testing_session = sessionmaker(bind=engine, autocommit=False, autoflush=False)
    Base.metadata.create_all(bind=engine)
    return testing_session()


def _candidate(
    candidate_id: str,
    *,
    title: str,
    estimated_kcal: int,
    retrieval_tier: str,
    store_name: str | None = None,
    source_metadata: dict[str, object] | None = None,
) -> RecommendationCandidate:
    metadata = {
        "retrieval_tier": retrieval_tier,
        "item_kind": "meal",
        "staple_type": "rice",
        "cuisine_family": "taiwanese",
        "protein_posture": "high_protein",
    }
    if source_metadata:
        metadata.update(source_metadata)
    return RecommendationCandidate(
        candidate_id=candidate_id,
        candidate_kind="golden_order",
        title=title,
        store_name=store_name,
        estimated_kcal=estimated_kcal,
        protein_g=24,
        fit_summary="fit",
        source_metadata=metadata,
    )


def test_recommendation_response_returns_top_pick_backups_and_hint_packet() -> None:
    context = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-18",
            budget_kcal=1700,
            consumed_kcal=850,
            remaining_kcal=850,
            active_meal_count=1,
        ),
        active_body_plan_view=ActiveBodyPlanView(user_id=1, daily_budget_kcal=1700),
        preference_profile_summary=PreferenceProfileSummary(
            user_id=1,
            generated_at=None,
            common_store_names=(PreferenceFacet(value="Bowl Lab", count=4),),
            freshness_posture="fresh",
        ),
        raw_user_input="晚餐吃什麼",
    )
    retrieval_result = RecommendationCandidateRetrievalResult(
        candidate_items=[
            _candidate("top", title="Chicken Bowl", store_name="Bowl Lab", estimated_kcal=620, retrieval_tier="historical_match"),
            _candidate("backup-1", title="Tofu Bento", store_name="Bento House", estimated_kcal=560, retrieval_tier="nearby"),
            _candidate("backup-2", title="Egg Sandwich", store_name="Cafe", estimated_kcal=390, retrieval_tier="safe_fallback"),
        ],
        candidate_source_summary={},
        candidate_filter_reasons={},
        candidate_count=3,
    )

    ranking_result = build_recommendation_ranking_and_synthesis(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        retrieval_result=retrieval_result,
    )
    response_packet = build_recommendation_response(
        context_packet=context,
        ranking_result=ranking_result,
    )

    assert response_packet.response.top_pick is not None
    assert response_packet.response.top_pick.candidate_id == "top"
    assert [candidate.candidate_id for candidate in response_packet.response.backup_picks] == ["backup-1", "backup-2"]
    assert response_packet.response.hint_packet is not None
    assert response_packet.response.hint_packet.candidate_id == "top"
    assert "Chicken Bowl" in response_packet.response.reply_text
    assert "Tofu Bento" in response_packet.response.reply_text
    assert any(action["action"] == "recommendation_intake_handoff" for action in response_packet.response.quick_actions)


def test_recommendation_response_remains_non_mutating_and_falls_back_without_candidates() -> None:
    db = _session()
    user = get_or_create_user(db, "recommendation-no-mutation")
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
        ),
    )
    before_body_plan_count = db.query(BodyPlanRecord).count()
    before_ledger_count = db.query(DayBudgetLedgerRecord).count()
    before_meal_thread_count = db.query(MealThreadRecord).count()

    context = build_recommendation_context(
        user_id=user.id,
        current_budget_view=CurrentBudgetView(
            user_id=user.id,
            local_date="2026-04-18",
            budget_kcal=1500,
            consumed_kcal=1450,
            remaining_kcal=50,
            active_meal_count=3,
        ),
        active_body_plan_view=ActiveBodyPlanView(user_id=user.id, daily_budget_kcal=1500),
        raw_user_input="推薦晚餐",
    )
    ranking_result = build_recommendation_ranking_and_synthesis(
        context_packet=context,
        candidate_spec=build_recommendation_candidate_spec(context_packet=context),
        retrieval_result=RecommendationCandidateRetrievalResult(
            candidate_items=[],
            candidate_source_summary={},
            candidate_filter_reasons={},
            candidate_count=0,
        ),
    )
    response_packet = build_recommendation_response(
        context_packet=context,
        ranking_result=ranking_result,
    )

    assert response_packet.response.top_pick is None
    assert response_packet.response.hint_packet is None
    assert not any(action["action"] == "recommendation_intake_handoff" for action in response_packet.response.quick_actions)
    assert response_packet.ui_hints["candidate_spec_posture"] == "budget_constrained"
    assert db.query(BodyPlanRecord).count() == before_body_plan_count
    assert db.query(DayBudgetLedgerRecord).count() == before_ledger_count
    assert db.query(MealThreadRecord).count() == before_meal_thread_count


def test_recommendation_pipeline_exposes_candidate_spec_and_handoff_ready() -> None:
    db = _session()
    user = get_or_create_user(db, "recommendation-preview")
    bootstrap_body_plan_for_date(
        db,
        user=user,
        inputs=OnboardingBootstrapInput(
            sex="female",
            age_years=30,
            height_cm=165.0,
            current_weight_kg=58.0,
            activity_level="sedentary",
            goal_type="lose_weight",
            weekly_target_rate_kg=0.5,
            local_date="2026-04-18",
        ),
    )
    commit_meal_payload_to_canonical(
        db,
        user=user,
        candidate=CommitRequestCandidate(
            request_id="recommendation-preview-meal-1",
            planner_intent="food_estimation",
            version_reason="new_intake",
            meal_title="breakfast sandwich",
            raw_input="breakfast sandwich",
            estimated_kcal=420,
            protein_g=18,
            carb_g=32,
            fat_g=14,
            resolution_status="completed_meal",
            local_date="2026-04-18",
        ),
    )

    context = build_recommendation_context(
        user_id=user.id,
        current_budget_view=CurrentBudgetView(
            user_id=user.id,
            local_date="2026-04-18",
            budget_kcal=1500,
            consumed_kcal=420,
            remaining_kcal=1080,
            active_meal_count=1,
        ),
        active_body_plan_view=ActiveBodyPlanView(user_id=user.id, daily_budget_kcal=1500),
        raw_user_input="recommend something light nearby",
    )
    candidate_spec = build_recommendation_candidate_spec(context_packet=context)
    retrieval_result = build_recommendation_candidates(
        context_packet=context,
        candidate_spec=candidate_spec,
        historical_matches=[
            _candidate(
                "top",
                title="Chicken Bowl",
                store_name="Bowl Lab",
                estimated_kcal=620,
                retrieval_tier="historical_match",
                source_metadata={"item_kind": "salad"},
            ),
        ],
        nearby_candidates=[
            _candidate(
                "backup-1",
                title="Tofu Bento",
                store_name="Bento House",
                estimated_kcal=560,
                retrieval_tier="nearby",
                source_metadata={"item_kind": "salad"},
            ),
        ],
    )
    ranking_result = build_recommendation_ranking_and_synthesis(
        context_packet=context,
        candidate_spec=candidate_spec,
        retrieval_result=retrieval_result,
    )
    response_packet = build_recommendation_response(
        context_packet=context,
        ranking_result=ranking_result,
    )

    assert context.recommendation_mode == "reactive_chat"
    assert candidate_spec.handoff_ready is True
    assert response_packet.response.top_pick is not None
    assert response_packet.ui_hints["non_mutating"] is True
    assert any(action["action"] == "recommendation_intake_handoff" for action in response_packet.response.quick_actions)
