from __future__ import annotations

from app.runtime.application.proactive_no_send_control_feedback import (
    evaluate_no_send_control_feedback,
)
from app.runtime.application.proactive_no_send_interaction_model import (
    apply_no_send_candidate_interaction,
)
from tests.test_proactive_no_send_interaction_model import _candidate


def test_recent_dismiss_suppresses_same_trigger_until_next_signal() -> None:
    result = evaluate_no_send_control_feedback(
        trigger_type="recommendation_prompt",
        prior_interactions=[
            {
                "artifact_type": "proactive_no_send_interaction_model_artifact",
                "status": "pass",
                "action": "dismiss",
                "next_signal_required": "new_app_open_with_qualified_pool",
                "interaction_state": {"dismissed": True},
                "trigger_type": "recommendation_prompt",
            }
        ],
        observed_signals=[],
    )

    assert result["artifact_type"] == "proactive_no_send_control_feedback"
    assert result["status"] == "suppressed"
    assert result["suppression_reasons"] == ["recent_dismiss_without_next_signal"]
    assert result["review_decision"] == {
        "status": "suppressed_feedback",
        "reviewer_next_step": "keep_silent_until_next_signal",
    }
    assert result["next_signal_required"] == "new_app_open_with_qualified_pool"
    assert result["proactive_sent"] is False
    assert result["scheduler_enabled"] is False
    assert result["durable_memory_written"] is False
    assert result["user_facing_behavior_changed"] is False


def test_material_context_signal_releases_dismiss_only_suppression() -> None:
    result = evaluate_no_send_control_feedback(
        trigger_type="recommendation_prompt",
        prior_interactions=[
            {
                "artifact_type": "proactive_no_send_interaction_model_artifact",
                "status": "pass",
                "action": "dismiss",
                "next_signal_required": "new_app_open_with_qualified_pool",
                "interaction_state": {"dismissed": True},
                "trigger_type": "recommendation_prompt",
            }
        ],
        observed_signals=["new_app_open_with_qualified_pool"],
    )

    assert result["status"] == "not_suppressed"
    assert result["suppression_reasons"] == []
    assert result["review_decision"]["status"] == "candidate_for_human_review"
    assert result["next_signal_observed"] == "new_app_open_with_qualified_pool"
    assert result["proactive_sent"] is False


def test_explicit_opt_out_suppresses_even_after_material_context_change() -> None:
    result = evaluate_no_send_control_feedback(
        trigger_type="recommendation_prompt",
        prior_interactions=[
            {
                "artifact_type": "proactive_no_send_interaction_model_artifact",
                "status": "pass",
                "action": "dismiss",
                "dismiss_reason": "too_frequent",
                "next_signal_required": "new_app_open_with_qualified_pool",
                "interaction_state": {"dismissed": True},
                "trigger_type": "recommendation_prompt",
            }
        ],
        observed_signals=["new_app_open_with_qualified_pool"],
        explicit_trigger_opt_out=True,
    )

    assert result["status"] == "suppressed"
    assert result["suppression_reasons"] == ["explicit_trigger_opt_out"]
    assert result["review_decision"] == {
        "status": "suppressed_feedback",
        "reviewer_next_step": "respect_trigger_opt_out",
    }
    assert result["next_signal_observed"] == "new_app_open_with_qualified_pool"
    assert result["durable_memory_written"] is False


def test_feedback_ignores_blocked_or_cross_trigger_interactions() -> None:
    result = evaluate_no_send_control_feedback(
        trigger_type="meal_reminder",
        prior_interactions=[
            {
                "artifact_type": "proactive_no_send_interaction_model_artifact",
                "status": "blocked",
                "action": "dismiss",
                "next_signal_required": "new_app_open_with_qualified_pool",
                "trigger_type": "meal_reminder",
            },
            {
                "artifact_type": "proactive_no_send_interaction_model_artifact",
                "status": "pass",
                "action": "dismiss",
                "next_signal_required": "new_app_open_with_qualified_pool",
                "trigger_type": "recommendation_prompt",
            },
        ],
        observed_signals=[],
    )

    assert result["status"] == "not_suppressed"
    assert result["suppression_reasons"] == []
    assert result["ignored_interaction_count"] == 2
    assert result["matched_interaction_count"] == 0


def test_feedback_consumes_real_no_send_interaction_artifact() -> None:
    interaction = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="dismiss",
        dismiss_reason="too_frequent",
    )

    suppressed = evaluate_no_send_control_feedback(
        trigger_type="recommendation_prompt",
        prior_interactions=[interaction],
        observed_signals=[],
    )
    released = evaluate_no_send_control_feedback(
        trigger_type="recommendation_prompt",
        prior_interactions=[interaction],
        observed_signals=["new_app_open_with_qualified_pool"],
    )

    assert suppressed["status"] == "suppressed"
    assert suppressed["matched_interaction_count"] == 1
    assert released["status"] == "not_suppressed"
