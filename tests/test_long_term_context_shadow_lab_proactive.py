from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_proactive_intelligence_shadow_eval_prefers_useful_silence_over_noise() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "proactive_intelligence_shadow_eval"
    ]

    assert artifact["artifact_type"] == "proactive_intelligence_shadow_eval"
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_activated"] is False
    assert artifact["channel_send_attempted"] is False
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["lowest_autonomy_tier_policy"] == {
        "default_tier": "observe_only",
        "max_shadow_tier": "suggest",
        "auto_action_allowed": False,
        "ask_approval_before_user_visible_send": True,
    }
    assert artifact["suppression_policy"]["quiet_window_suppresses_push"] is True
    assert artifact["suppression_policy"]["prefer_inbox_digest_before_push"] is True
    assert artifact["suppression_policy"]["dismiss_snooze_correction_required"] is True
    assert artifact["agentic_product_pattern_basis"] == [
        "guardrails_before_user_visible_action",
        "session_state_and_scope_before_recall",
        "human_interrupt_or_approval_for_high_impact_action",
        "personalization_control_and_memory_review",
        "lowest_autonomy_tier_that_creates_value",
    ]

    decisions = {
        decision["source_candidate_id"]: decision
        for decision in artifact["candidate_trigger_decisions"]
    }
    assert decisions["app-usage-style-pattern"]["recommended_shadow_surface"] == (
        "silent_observe"
    )
    assert decisions["pattern-budget-overshoot-frequency"][
        "recommended_shadow_surface"
    ] in {"inbox_digest_candidate", "future_nudge_candidate"}
    assert all(
        decision["annoyance_risk_score"] >= 0
        for decision in artifact["candidate_trigger_decisions"]
    )
    assert all(
        decision["runtime_effect_allowed"] is False
        for decision in artifact["candidate_trigger_decisions"]
    )

    false_positive = {
        case["case_id"]: case for case in artifact["false_positive_silence_cases"]
    }
    assert (
        false_positive["late_night_backfill_already_logged"]["should_stay_silent"]
        is True
    )
    assert (
        false_positive["low_confidence_preference_signal"]["next_signal_required"]
        == "more_evidence_or_user_confirmation"
    )
