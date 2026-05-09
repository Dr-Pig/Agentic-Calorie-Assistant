from __future__ import annotations

import json

from app.runtime.application.proactive_no_send_interaction_model import (
    apply_no_send_candidate_interaction,
)
from app.runtime.application.proactive_no_send_nudge_candidate import (
    build_no_send_nudge_candidate,
)
from app.runtime.application.proactive_no_send_review_sink import (
    build_no_send_review_sink,
)


def test_review_sink_records_no_send_candidate_without_delivery() -> None:
    candidate = _candidate()
    interaction = apply_no_send_candidate_interaction(
        no_send_candidate=candidate,
        action="dismiss",
        dismiss_reason="too_frequent",
    )

    result = build_no_send_review_sink(
        no_send_candidates=[candidate],
        interaction_artifacts=[interaction],
    )

    assert result["artifact_type"] == "proactive_no_send_review_sink_artifact"
    assert result["status"] == "pass"
    assert result["record_count"] == 1
    assert result["records"] == [
        {
            "trigger_type": "recommendation_prompt",
            "candidate_kind": "recommendation_prompt_review",
            "candidate_status": "pass",
            "interaction_status": "pass",
            "interaction_action": "dismiss",
            "delivery_attempted": False,
            "scheduler_enqueued": False,
            "user_facing_visible": False,
            "next_signal_required": "new_app_open_with_qualified_pool",
            "dismiss_reason_choices_present": True,
            "snooze_window_present": True,
            "undo_scope": "current_no_send_candidate_only",
        }
    ]
    assert result["delivery_attempted"] is False
    assert result["scheduler_enabled"] is False
    assert result["push_or_line_delivery_connected"] is False
    assert result["manager_context_injected"] is False
    assert result["recommendation_served"] is False
    assert result["rescue_committed"] is False
    assert result["proposal_committed"] is False
    assert result["mutation_changed"] is False
    assert result["durable_memory_written"] is False
    assert result["user_facing_behavior_changed"] is False


def test_review_sink_blocks_candidate_or_interaction_claim_drift() -> None:
    drifting_candidate = _candidate()
    drifting_candidate["proactive_sent"] = True
    clean_interaction = apply_no_send_candidate_interaction(
        no_send_candidate=_candidate(),
        action="dismiss",
        dismiss_reason="too_frequent",
    )
    blocked_by_candidate = build_no_send_review_sink(
        no_send_candidates=[drifting_candidate],
        interaction_artifacts=[clean_interaction],
    )
    drifting_interaction = dict(clean_interaction)
    drifting_interaction["scheduler_enabled"] = True
    blocked_by_interaction = build_no_send_review_sink(
        no_send_candidates=[_candidate()],
        interaction_artifacts=[drifting_interaction],
    )

    assert blocked_by_candidate["status"] == "blocked"
    assert blocked_by_candidate["blockers"] == ["candidate[0].proactive_sent"]
    assert blocked_by_candidate["records"] == []
    assert blocked_by_candidate["delivery_attempted"] is False
    assert blocked_by_interaction["status"] == "blocked"
    assert blocked_by_interaction["blockers"] == ["interaction[0].scheduler_enabled"]
    assert blocked_by_interaction["scheduler_enabled"] is False


def test_review_sink_blocks_missing_control_paths() -> None:
    candidate = {
        "artifact_type": "proactive_no_send_nudge_candidate",
        "status": "pass",
        "trigger_type": "recommendation_prompt",
        "candidate_kind": "recommendation_prompt_review",
        "dismiss_reason_choices": [],
        "snooze_window": {},
        "undo_scope": "",
        "next_signal_required": "",
        "proactive_sent": False,
        "scheduler_enabled": False,
        "live_delivery_allowed": False,
        "runtime_effect_allowed": False,
    }

    result = build_no_send_review_sink(
        no_send_candidates=[candidate],
        interaction_artifacts=[],
    )

    assert result["status"] == "blocked"
    assert result["blockers"] == [
        "candidate[0].dismiss_reason_choices_missing",
        "candidate[0].snooze_window_missing",
        "candidate[0].undo_scope_missing",
        "candidate[0].next_signal_required_missing",
    ]
    assert result["records"] == []
    assert result["delivery_attempted"] is False


def test_review_sink_keeps_pending_candidate_reviewable_without_payload_leak() -> None:
    candidate = _candidate()
    candidate["candidate_id"] = "hidden-food-candidate"

    result = build_no_send_review_sink(
        no_send_candidates=[candidate],
        interaction_artifacts=[],
    )
    serialized = json.dumps(result, ensure_ascii=False)

    assert result["status"] == "pass"
    assert result["record_count"] == 1
    assert result["records"][0]["interaction_status"] == "not_provided"
    assert result["records"][0]["interaction_action"] is None
    assert "hidden-food-candidate" not in serialized
    assert "candidate_copy" not in serialized
    assert result["user_facing_behavior_changed"] is False


def _candidate() -> dict[str, object]:
    return build_no_send_nudge_candidate(
        trigger_type="recommendation_prompt",
        candidate_source={
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
