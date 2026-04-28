from __future__ import annotations

from app.archive.recommendation.application import build_recommendation_candidate_spec, build_recommendation_context
from app.shared.domain import ActiveBodyPlanView, CurrentBudgetView


def test_candidate_spec_generation_builds_semantic_blueprint() -> None:
    context = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-19",
            budget_kcal=1800,
            consumed_kcal=950,
            remaining_kcal=850,
        ),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=1,
            daily_budget_kcal=1800,
        ),
        raw_user_input="I want a light nearby dinner",
    )

    spec = build_recommendation_candidate_spec(context_packet=context)

    assert spec.desired_meal_style == "light"
    assert "nearby" in spec.retrieval_terms
    assert spec.target_kcal_max == 850
    assert spec.candidate_spec_posture == "semantic_blueprint"


def test_candidate_spec_generation_marks_budget_constrained_posture() -> None:
    context = build_recommendation_context(
        user_id=1,
        current_budget_view=CurrentBudgetView(
            user_id=1,
            local_date="2026-04-19",
            budget_kcal=1600,
            consumed_kcal=1280,
            remaining_kcal=320,
        ),
        active_body_plan_view=ActiveBodyPlanView(
            user_id=1,
            daily_budget_kcal=1600,
        ),
        raw_user_input="Show me something light",
    )

    spec = build_recommendation_candidate_spec(context_packet=context)

    assert spec.candidate_spec_posture == "budget_constrained"
    assert spec.target_kcal_max == 320
    assert "fried" in spec.excluded_item_patterns
