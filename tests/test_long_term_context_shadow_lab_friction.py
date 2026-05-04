from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_contextual_friction_budget_shadow_eval_limits_followups_with_reversible_defaults() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "contextual_friction_budget_shadow_eval"
    ]

    assert artifact["artifact_type"] == "contextual_friction_budget_shadow_eval"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["intake_commit_requested"] is False
    assert artifact["response_generated"] is False
    assert (
        artifact["default_strategy"] == "estimate_then_one_targeted_followup_if_needed"
    )
    assert artifact["max_followup_questions_shadow"] == 1
    assert artifact["reversible_default_required"] is True

    decisions = {
        item["context_domain"]: item for item in artifact["friction_decisions"]
    }
    assert decisions["user_language_pattern"]["recommended_interaction"] in {
        "use_reversible_default_with_short_confirmation",
        "ask_one_targeted_followup",
    }
    assert decisions["intake_estimation_bias"]["recommended_interaction"] == (
        "ask_one_targeted_followup"
    )
    assert decisions["interaction_preference"]["recommended_interaction"] == (
        "short_direct_answer"
    )
    assert all(item["runtime_effect_allowed"] is False for item in decisions.values())
    assert artifact["measurement_plan"] == [
        "time_to_first_value",
        "followup_turn_count",
        "user_correction_rate",
        "dismissal_or_abandonment_rate",
    ]
