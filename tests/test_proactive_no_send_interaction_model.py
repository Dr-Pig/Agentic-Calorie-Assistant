from __future__ import annotations

from app.runtime.application.proactive_no_send_interaction_model import (
    apply_no_send_candidate_interaction,
)
from app.runtime.application.proactive_no_send_nudge_candidate import (
    build_no_send_nudge_candidate,
)


def test_dismiss_uses_allowed_reason_without_durable_suppression() -> None:
    result = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="dismiss",
        dismiss_reason="too_frequent",
    )

    assert result["artifact_type"] == "proactive_no_send_interaction_model_artifact"
    assert result["status"] == "pass"
    assert result["action"] == "dismiss"
    assert result["trigger_type"] == "recommendation_prompt"
    assert result["dismiss_reason"] == "too_frequent"
    assert result["interaction_state"] == {
        "candidate_visible": False,
        "dismissed": True,
        "snoozed_until": None,
        "undo_available": True,
        "scope": "current_no_send_candidate_only",
    }
    assert result["next_signal_required"] == "new_app_open_with_qualified_pool"
    assert result["durable_memory_written"] is False
    assert result["scheduler_enabled"] is False
    assert result["proactive_sent"] is False
    assert result["user_facing_behavior_changed"] is False


def test_snooze_requires_candidate_window_and_stays_lab_only() -> None:
    result = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="snooze",
        snooze_minutes=120,
    )

    assert result["status"] == "pass"
    assert result["action"] == "snooze"
    assert result["interaction_state"] == {
        "candidate_visible": False,
        "dismissed": False,
        "snoozed_until": "duration:120m",
        "undo_available": True,
        "scope": "current_no_send_candidate_only",
    }
    assert result["push_or_line_delivery_connected"] is False
    assert result["durable_snooze_written"] is False


def test_undo_only_reopens_current_candidate_instance() -> None:
    result = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="undo",
        undo_token="current_no_send_candidate_only",
    )

    assert result["status"] == "pass"
    assert result["action"] == "undo"
    assert result["interaction_state"] == {
        "candidate_visible": True,
        "dismissed": False,
        "snoozed_until": None,
        "undo_available": False,
        "scope": "current_no_send_candidate_only",
    }
    assert result["durable_memory_written"] is False
    assert result["mutation_changed"] is False


def test_interaction_blocks_invalid_reason_snooze_or_undo_scope() -> None:
    invalid_reason = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="dismiss",
        dismiss_reason="never_send_this_again",
    )
    invalid_snooze = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="snooze",
        snooze_minutes=360,
    )
    invalid_undo = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="undo",
        undo_token="durable_preference",
    )

    assert invalid_reason["status"] == "blocked"
    assert invalid_reason["blockers"] == [
        "dismiss_reason_not_allowed:never_send_this_again"
    ]
    assert invalid_snooze["status"] == "blocked"
    assert invalid_snooze["blockers"] == ["snooze_minutes_exceed_candidate_window:360"]
    assert invalid_undo["status"] == "blocked"
    assert invalid_undo["blockers"] == ["undo_scope_not_allowed:durable_preference"]


def test_interaction_blocks_candidate_that_is_not_no_send_or_has_claim_drift() -> None:
    candidate = _candidate()
    candidate["proactive_sent"] = True

    result = apply_no_send_candidate_interaction(
        no_send_candidate=candidate,
        action="dismiss",
        dismiss_reason="too_frequent",
    )

    assert result["status"] == "blocked"
    assert result["blockers"] == ["no_send_candidate.proactive_sent"]
    assert result["interaction_state"]["candidate_visible"] is True
    assert result["proactive_sent"] is False


def _candidate() -> dict[str, object]:
    return build_no_send_nudge_candidate(
        trigger_type="recommendation_prompt",
        candidate_source={
            "source_report_used": True,
            "status": "candidate_for_human_review",
            "actual_candidates_included": False,
            "candidate_ids_exposed": False,
            "runtime_effect_allowed": False,
            "recommendation_served": False,
            "proactive_sent": False,
            "scheduler_enabled": False,
            "live_delivery_allowed": False,
            "scheduler_activation_allowed": False,
            "manager_context_injected": False,
        },
        user_control_model={
            "dismiss_reason_choices": [
                "not_relevant_now",
                "already_handled",
                "too_frequent",
            ],
            "snooze_window": {"kind": "duration", "minutes": 180},
            "undo_scope": "current_no_send_candidate_only",
            "next_signal_required": "new_app_open_with_qualified_pool",
        },
    )
