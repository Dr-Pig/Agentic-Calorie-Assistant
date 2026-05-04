from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_weekly_insight_shadow_plan_is_chat_draft_and_no_send() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "weekly_insight_shadow_plan"
    ]

    assert artifact["artifact_type"] == "weekly_insight_shadow_plan"
    assert artifact["weekly_insight_report_written"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["scheduler_activated"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["narrative_summary_generated"] is False
    assert artifact["future_surface_policy"] == {
        "primary_surface": "chat_draft",
        "ui_history_mirror_allowed_later": True,
        "push_send_allowed_now": False,
        "user_dismiss_or_snooze_required_before_runtime": True,
    }
    assert artifact["deterministic_metrics"]["budget_day_count"] >= 1
    assert artifact["deterministic_metrics"]["math_truth_owner"] == (
        "budget_body_calibration_canonical_summaries"
    )
    assert artifact["llm_boundary"] == {
        "may_write_narrative_later": True,
        "may_invent_metrics": False,
        "may_send_without_proactive_gate": False,
    }
    assert artifact["review_packet"]["human_review_required"] is True
    assert artifact["review_packet"]["runtime_effect_allowed"] is False
    assert "positive_highlights" in artifact["review_packet"]["draft_sections"]
    assert "annoyance_suppression_check" in artifact["review_packet"]["draft_sections"]
