from __future__ import annotations

import json

from app.runtime.application.proactive_no_send_nudge_bridge import (
    build_no_send_nudge_candidate_bridge,
)
from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)


def test_bridge_wraps_recommendation_and_rescue_reviews_as_no_send_candidates() -> None:
    bridge = build_no_send_nudge_candidate_bridge(
        recommendation_prompt_review=_recommendation_review(),
        rescue_nudge_review=_rescue_review(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
    )
    serialized = json.dumps(bridge, ensure_ascii=False)

    assert bridge["artifact_type"] == "proactive_no_send_nudge_candidate_bridge"
    assert bridge["status"] == "pass"
    assert bridge["candidate_count"] == 2
    assert [candidate["trigger_type"] for candidate in bridge["candidates"]] == [
        "recommendation_prompt",
        "rescue_nudge",
    ]
    assert bridge["simulation_input_metadata"] == [
        {
            "trigger_type": "recommendation_prompt",
            "wake_source": "app_open",
            "delivery_surface": "app_open",
            "candidate_kind": "recommendation_prompt_review",
            "has_required_user_controls": True,
        },
        {
            "trigger_type": "rescue_nudge",
            "wake_source": "manual_shadow_review",
            "delivery_surface": "app_open",
            "candidate_kind": "rescue_nudge_review",
            "has_required_user_controls": True,
        },
    ]
    assert bridge["runtime_effect_allowed"] is False
    assert bridge["proactive_sent"] is False
    assert bridge["scheduler_enabled"] is False
    assert bridge["live_delivery_allowed"] is False
    assert bridge["recommendation_served"] is False
    assert bridge["rescue_committed"] is False
    assert bridge["proposal_committed"] is False
    assert bridge["mutation_changed"] is False
    assert "hidden-food-candidate" not in serialized
    assert "hidden rescue proposal" not in serialized
    assert "candidate_copy" not in serialized


def test_bridge_outputs_metadata_that_can_feed_existing_no_send_simulation() -> None:
    bridge = build_no_send_nudge_candidate_bridge(
        recommendation_prompt_review=_recommendation_review(),
        rescue_nudge_review=_rescue_review(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
    )

    simulation = build_proactive_no_send_simulation(
        [ProactiveNoSendShadowInput(**item) for item in bridge["simulation_inputs"]]
    )

    assert simulation["artifact_type"] == "proactive_no_send_simulation"
    assert simulation["proactive_sent"] is False
    assert simulation["scheduler_enabled"] is False
    assert simulation["summary"]["trigger_count"] == 2
    assert "recommendation_prompt" in simulation["summary"][
        "candidate_for_human_review_trigger_types"
    ]
    assert "rescue_nudge" in simulation["summary"][
        "deferred_later_only_trigger_types"
    ]


def test_bridge_blocks_candidate_missing_user_control_model() -> None:
    bridge = build_no_send_nudge_candidate_bridge(
        recommendation_prompt_review=_recommendation_review(),
        rescue_nudge_review=_rescue_review(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": {
                "dismiss_reason_choices": [],
                "snooze_window": {},
                "undo_scope": "",
                "next_signal_required": "",
            },
        },
    )

    assert bridge["status"] == "blocked"
    assert bridge["blockers"] == [
        "rescue_nudge.user_control_model.dismiss_reason_choices_missing",
        "rescue_nudge.user_control_model.snooze_window_missing",
        "rescue_nudge.user_control_model.undo_scope_missing",
        "rescue_nudge.user_control_model.next_signal_required_missing",
    ]
    assert bridge["candidate_count"] == 0
    assert bridge["simulation_inputs"] == []
    assert bridge["proactive_sent"] is False


def test_bridge_blocks_source_claim_drift_without_leaking_source_details() -> None:
    review = _recommendation_review()
    review["recommendation_served"] = True
    review["candidate_id"] = "hidden-food-candidate"

    bridge = build_no_send_nudge_candidate_bridge(
        recommendation_prompt_review=review,
        rescue_nudge_review=None,
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool")
        },
    )
    serialized = json.dumps(bridge, ensure_ascii=False)

    assert bridge["status"] == "blocked"
    assert bridge["blockers"] == [
        "recommendation_prompt.candidate_source.recommendation_served"
    ]
    assert bridge["candidates"] == []
    assert "hidden-food-candidate" not in serialized
    assert bridge["recommendation_served"] is False


def _recommendation_review() -> dict[str, object]:
    return {
        "source_report_used": True,
        "status": "candidate_for_human_review",
        "recommendation_pool_decision": "primary_plus_backup",
        "prompt_posture": "invitation_only",
        "candidate_ids": ["hidden-food-candidate"],
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
        "proposal_summary": "hidden rescue proposal",
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


def _controls(next_signal: str) -> dict[str, object]:
    return {
        "dismiss_reason_choices": [
            "not_relevant_now",
            "already_handled",
            "too_frequent",
        ],
        "snooze_window": {"kind": "duration", "minutes": 180},
        "undo_scope": "current_no_send_candidate_only",
        "next_signal_required": next_signal,
    }
