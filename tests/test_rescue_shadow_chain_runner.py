from __future__ import annotations

import json

from app.rescue.application.shadow_chain_runner import (
    run_rescue_shadow_chain,
)


def test_rescue_shadow_chain_composes_existing_stages_without_runtime_effects() -> None:
    artifact = run_rescue_shadow_chain(
        memory_summary_projection=_memory_projection(),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_candidate_output(),
        budget_context={"current_date": "2026-05-09", "overshoot_kcal": 300},
        body_plan_context={"safety_floor_kcal": 1200, "target_days_count": 5},
        rescue_history_context={"recent_rescue_count": 1, "summary": "accepted once"},
        suppression_context=[{"trigger_type": "rescue_nudge", "summary": "dismissed once"}],
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "rescue_shadow_chain_runner_artifact"
    assert artifact["status"] == "pass"
    assert artifact["runner_role"] == "chain_integrity_only"
    assert artifact["stage_order"] == [
        "rescue_shadow_summary_context_projection",
        "rescue_no_commit_viability_shadow_packet",
        "rescue_option_generation_shadow_packet",
        "rescue_proposal_shaping_input_shadow_packet",
        "rescue_proposal_shaping_fake_runner_artifact",
    ]
    assert artifact["stage_trace"] == [
        {"stage": "rescue_shadow_summary_context_projection", "status": "pass"},
        {"stage": "rescue_no_commit_viability_shadow_packet", "status": "pass"},
        {"stage": "rescue_option_generation_shadow_packet", "status": "pass"},
        {"stage": "rescue_proposal_shaping_input_shadow_packet", "status": "pass"},
        {"stage": "rescue_proposal_shaping_fake_runner_artifact", "status": "pass"},
    ]
    assert [stage["artifact_type"] for stage in artifact["stage_artifacts"]] == artifact[
        "stage_order"
    ]
    assert artifact["final_validation_status"] == "pass"
    assert artifact["blockers"] == []
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["live_llm_invoked"] is False
    assert artifact["provider_called"] is False
    assert artifact["rescue_committed"] is False
    assert artifact["proposal_committed"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["meal_thread_mutated"] is False
    assert artifact["durable_memory_written"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proposal_card"] is None
    assert artifact["primary_actions"] == []
    assert "Fixture headline, not user-facing" not in serialized
    assert "Fixture summary, not user-facing" not in serialized


def test_rescue_shadow_chain_blocks_upstream_stage_failure() -> None:
    memory = _memory_projection()
    memory["rescue_proposal_committed"] = True

    artifact = run_rescue_shadow_chain(
        memory_summary_projection=memory,
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_candidate_output(),
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "rescue_shadow_summary_context_projection.status_blocked",
        "rescue_shadow_summary_context_projection.consumer_summary_projection.rescue_proposal_committed",
    ]
    assert artifact["stage_trace"][0] == {
        "stage": "rescue_shadow_summary_context_projection",
        "status": "blocked",
    }
    assert artifact["final_validation_status"] == "not_run"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["proposal_committed"] is False


def test_rescue_shadow_chain_blocks_stage_runtime_effect_claim_drift() -> None:
    artifact = run_rescue_shadow_chain(
        memory_summary_projection=_memory_projection(),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output={
            **_candidate_output(),
            "primary_actions": ["accept_rescue_plan"],
        },
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "rescue_proposal_shaping_fake_runner_artifact.status_fail",
        "rescue_proposal_shaping_fake_runner_artifact.candidate_output.primary_actions_forbidden",
    ]
    assert artifact["stage_trace"][-1] == {
        "stage": "rescue_proposal_shaping_fake_runner_artifact",
        "status": "fail",
    }
    assert artifact["proposal_committed"] is False
    assert artifact["primary_actions"] == []


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "suppression_summary": {
            "suppression_blockers": [
                {"candidate_id": "suppress-1", "trigger_type": "rescue_nudge"}
            ]
        },
        "runtime_effect_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "recommendation_served": False,
        "proactive_sent": False,
        "rescue_proposal_committed": False,
        "retrieval_ranking_changed": False,
    }


def _derived_views() -> dict[str, object]:
    return {
        "rescue_history_summary": {
            "is_durable_memory_truth": False,
            "rescue_event_count": 1,
        },
        "adherence_summary": {
            "is_durable_memory_truth": False,
            "adherence_posture": "mixed",
        },
    }


def _budget_view() -> dict[str, int]:
    return {
        "base_budget_kcal": 1800,
        "effective_budget_kcal": 1800,
        "meal_consumption_total_kcal": 2100,
    }


def _body_plan_view() -> dict[str, object]:
    return {
        "safety_floor_kcal": 1200,
        "target_days": [
            {
                "local_date": f"2026-05-{10 + index:02d}",
                "base_budget_kcal": 1800,
                "calibration_adjustment_total_kcal": 0,
            }
            for index in range(5)
        ],
    }


def _candidate_output() -> dict[str, object]:
    return {
        "proposal_headline": "Fixture headline, not user-facing",
        "proposal_summary": "Fixture summary, not user-facing",
        "coaching_frame": "Fixture frame, not user-facing",
        "recommended_days": 2,
        "daily_kcal_adjustment": -150,
        "cap_mode": "standard_15_percent",
        "special_posture": "standard_spread",
        "rubric": {
            "future_oriented": True,
            "no_shame": True,
            "not_user_facing": True,
            "fixture_only": True,
        },
    }
