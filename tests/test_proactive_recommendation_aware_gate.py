from __future__ import annotations

import json

from app.runtime.application.proactive_no_send_shadow_evaluator import (
    ProactiveNoSendShadowInput,
    build_proactive_no_send_simulation,
)


def _review(status: str, *, reason: str | None = None) -> dict[str, object]:
    return {
        "source_report_used": True,
        "status": status,
        "recommendation_pool_decision": (
            "silent_no_qualified_candidate"
            if status == "suppressed"
            else "primary_plus_backup"
        ),
        "prompt_posture": "invitation_only" if status == "candidate_for_human_review" else "silent",
        "suppression_reasons": [reason] if reason else [],
        "blockers": ["recommendation_quality_report.recommendation_served"]
        if status == "blocked"
        else [],
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


def _recommendation_prompt(
    review: dict[str, object] | None = None,
) -> ProactiveNoSendShadowInput:
    return ProactiveNoSendShadowInput(
        trigger_type="recommendation_prompt",
        local_time="17:30",
        data_sufficiency_status="higher",
        user_benefit_strength="strong",
        lower_frequency_ready=True,
        delivery_surface="app_open",
        recommendation_prompt_review=review,
    )


def test_recommendation_prompt_requires_bridge_review_before_human_review() -> None:
    artifact = build_proactive_no_send_simulation([_recommendation_prompt()])
    row = artifact["trigger_evaluations"][0]

    assert row["suppression_status"] == "suppressed"
    assert "recommendation_prompt_review_required" in row["suppression_reasons"]
    assert row["recommendation_served"] is False
    assert row["intake_hint_packet_created"] is False
    assert row["proactive_sent"] is False


def test_recommendation_prompt_silent_pool_suppresses_trigger() -> None:
    artifact = build_proactive_no_send_simulation(
        [
            _recommendation_prompt(
                _review(
                    "suppressed",
                    reason="recommendation_pool_silent_no_qualified_candidate",
                )
            )
        ]
    )
    row = artifact["trigger_evaluations"][0]

    assert row["suppression_status"] == "suppressed"
    assert row["recommendation_prompt_review"]["status"] == "suppressed"
    assert "recommendation_pool_silent_no_qualified_candidate" in row["suppression_reasons"]
    assert row["recommendation_served"] is False


def test_recommendation_prompt_reviewable_bridge_preserves_invitation_only() -> None:
    artifact = build_proactive_no_send_simulation(
        [_recommendation_prompt(_review("candidate_for_human_review"))]
    )
    row = artifact["trigger_evaluations"][0]

    assert row["suppression_status"] == "not_suppressed"
    assert row["review_decision"]["status"] == "candidate_for_human_review"
    assert row["recommendation_prompt_review"]["status"] == "candidate_for_human_review"
    assert row["recommendation_prompt_boundary"]["allowed"] == ["candidate_invitation_only"]
    assert row["recommendation_served"] is False
    assert row["intake_hint_packet_created"] is False


def test_recommendation_prompt_blocked_bridge_suppresses_without_runtime_effects() -> None:
    artifact = build_proactive_no_send_simulation(
        [_recommendation_prompt(_review("blocked"))]
    )
    row = artifact["trigger_evaluations"][0]

    assert row["suppression_status"] == "suppressed"
    assert "recommendation_prompt_review_blocked" in row["suppression_reasons"]
    assert row["recommendation_prompt_review"]["blockers"] == [
        "recommendation_quality_report.recommendation_served"
    ]
    assert row["recommendation_served"] is False
    assert row["proactive_sent"] is False
    assert artifact["scheduler_enabled"] is False


def test_recommendation_prompt_review_does_not_leak_candidate_details() -> None:
    review = _review("blocked")
    review["candidate_ids"] = ["hidden-candidate-123"]
    review["candidate_copy"] = "Hidden candidate copy should not be surfaced."

    artifact = build_proactive_no_send_simulation([_recommendation_prompt(review)])
    row_text = json.dumps(artifact["trigger_evaluations"][0], sort_keys=True)

    assert "hidden-candidate-123" not in row_text
    assert "Hidden candidate copy" not in row_text
