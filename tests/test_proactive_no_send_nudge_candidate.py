from __future__ import annotations

from app.runtime.application.proactive_no_send_nudge_candidate import (
    build_no_send_nudge_candidate,
)


def test_recommendation_review_becomes_controlled_no_send_candidate() -> None:
    candidate = build_no_send_nudge_candidate(
        trigger_type="recommendation_prompt",
        candidate_source=_recommendation_review(),
        user_control_model=_controls(),
        wake_source="app_open",
    )

    assert candidate["artifact_type"] == "proactive_no_send_nudge_candidate"
    assert candidate["status"] == "pass"
    assert candidate["trigger_type"] == "recommendation_prompt"
    assert candidate["candidate_kind"] == "recommendation_prompt_review"
    assert candidate["candidate_source_used"] is True
    assert candidate["dismiss_reason_choices"] == [
        "not_relevant_now",
        "already_handled",
        "too_frequent",
    ]
    assert candidate["snooze_window"] == {"kind": "duration", "minutes": 180}
    assert candidate["undo_scope"] == "current_no_send_candidate_only"
    assert candidate["next_signal_required"] == "new_app_open_with_qualified_pool"
    assert candidate["sent"] is False
    assert candidate["runtime_effect_allowed"] is False
    assert candidate["scheduler_enabled"] is False
    assert candidate["live_delivery_allowed"] is False
    assert candidate["recommendation_served"] is False
    assert candidate["manager_context_packet_changed"] is False
    assert candidate["mutation_changed"] is False
    assert candidate["primary_actions"] == []
    assert candidate["non_claims"] == [
        "not_notification",
        "not_user_facing_delivery",
        "not_scheduler_activation",
        "not_durable_dismiss_or_snooze_state",
        "not_runtime_mutation",
    ]


def test_rescue_review_becomes_controlled_no_send_candidate() -> None:
    candidate = build_no_send_nudge_candidate(
        trigger_type="rescue_nudge",
        candidate_source=_rescue_review(),
        user_control_model={
            **_controls(),
            "next_signal_required": "material_budget_change_or_user_reopens_rescue",
        },
        wake_source="manual_shadow_review",
    )

    assert candidate["status"] == "pass"
    assert candidate["candidate_kind"] == "rescue_nudge_review"
    assert candidate["next_signal_required"] == (
        "material_budget_change_or_user_reopens_rescue"
    )
    assert candidate["rescue_committed"] is False
    assert candidate["proposal_committed"] is False


def test_candidate_blocks_missing_user_control_paths() -> None:
    candidate = build_no_send_nudge_candidate(
        trigger_type="recommendation_prompt",
        candidate_source=_recommendation_review(),
        user_control_model={
            "dismiss_reason_choices": [],
            "snooze_window": {},
            "undo_scope": "",
            "next_signal_required": "",
        },
    )

    assert candidate["status"] == "blocked"
    assert candidate["blockers"] == [
        "user_control_model.dismiss_reason_choices_missing",
        "user_control_model.snooze_window_missing",
        "user_control_model.undo_scope_missing",
        "user_control_model.next_signal_required_missing",
    ]
    assert candidate["candidate_source_used"] is False
    assert candidate["sent"] is False


def test_candidate_blocks_source_claiming_runtime_scheduler_or_mutation() -> None:
    source = _recommendation_review()
    source["proactive_sent"] = True
    source["scheduler_enabled"] = True
    source["recommendation_served"] = True
    source["manager_context_injected"] = True

    candidate = build_no_send_nudge_candidate(
        trigger_type="recommendation_prompt",
        candidate_source=source,
        user_control_model=_controls(),
    )

    assert candidate["status"] == "blocked"
    assert candidate["blockers"] == [
        "candidate_source.proactive_sent",
        "candidate_source.scheduler_enabled",
        "candidate_source.recommendation_served",
        "candidate_source.manager_context_injected",
    ]
    assert candidate["sent"] is False
    assert candidate["recommendation_served"] is False
    assert candidate["manager_context_packet_changed"] is False


def test_candidate_blocks_unsupported_or_suppressed_source_review() -> None:
    suppressed = _recommendation_review()
    suppressed["status"] = "suppressed"
    unsupported = build_no_send_nudge_candidate(
        trigger_type="weekly_insight",
        candidate_source={"status": "candidate_for_human_review"},
        user_control_model=_controls(),
    )
    suppressed_result = build_no_send_nudge_candidate(
        trigger_type="recommendation_prompt",
        candidate_source=suppressed,
        user_control_model=_controls(),
    )

    assert unsupported["status"] == "blocked"
    assert unsupported["blockers"] == ["candidate_source.unsupported_trigger_type"]
    assert suppressed_result["status"] == "blocked"
    assert suppressed_result["blockers"] == [
        "candidate_source.status_not_candidate_for_human_review"
    ]


def _recommendation_review() -> dict[str, object]:
    return {
        "source_report_used": True,
        "status": "candidate_for_human_review",
        "recommendation_pool_decision": "primary_plus_backup",
        "prompt_posture": "invitation_only",
        "actual_candidates_included": False,
        "candidate_ids_exposed": False,
        "runtime_effect_allowed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "manager_context_injected": False,
    }


def _rescue_review() -> dict[str, object]:
    return {
        "source_projection_used": True,
        "status": "context_available",
        "prompt_posture": "later_only_review_context",
        "runtime_effect_allowed": False,
        "rescue_committed": False,
        "proposal_committed": False,
        "day_budget_mutated": False,
        "body_plan_mutated": False,
        "meal_thread_mutated": False,
        "durable_memory_written": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "scheduler_activation_allowed": False,
        "manager_context_injected": False,
        "recommendation_served": False,
    }


def _controls() -> dict[str, object]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": "new_app_open_with_qualified_pool",
    }
