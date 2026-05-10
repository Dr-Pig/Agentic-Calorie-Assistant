from __future__ import annotations

import json

from app.rescue.application.shadow_chain_runner import run_rescue_shadow_chain


def test_rescue_chain_adapter_builds_bounded_lifecycle_packets_without_commit() -> None:
    from app.rescue.application.chain_lifecycle_adapter import (
        build_rescue_chain_lifecycle_shadow_packets,
    )

    artifact = build_rescue_chain_lifecycle_shadow_packets(
        rescue_shadow_chain_artifact=_rescue_chain_artifact(),
        interaction_intents=["present", "accept", "dismiss", "request_gentler"],
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "rescue_chain_lifecycle_adapter_artifact"
    assert artifact["status"] == "pass"
    assert artifact["new_report_family_created"] is False
    assert artifact["source_rescue_chain_artifact_type"] == (
        "rescue_shadow_chain_runner_artifact"
    )
    assert artifact["source_stage_used"] == "rescue_option_generation_shadow_packet"
    assert artifact["interaction_intent_source"] == "bounded_lab_fixture_not_raw_text"
    assert artifact["semantic_interaction_owner"] == "future_llm_or_human_confirmation"
    assert artifact["stage_trace"] == [
        {
            "stage": "rescue_shadow_chain_runner_artifact",
            "status": "pass",
        },
        {
            "stage": "rescue_chat_negotiation_lifecycle_shadow_packet",
            "status": "pass",
            "interaction_intent": "present",
        },
        {
            "stage": "rescue_chat_negotiation_lifecycle_shadow_packet",
            "status": "pass",
            "interaction_intent": "accept",
        },
        {
            "stage": "rescue_chat_negotiation_lifecycle_shadow_packet",
            "status": "pass",
            "interaction_intent": "dismiss",
        },
        {
            "stage": "rescue_chat_negotiation_lifecycle_shadow_packet",
            "status": "pass",
            "interaction_intent": "request_gentler",
        },
    ]
    assert [row["lifecycle_state"] for row in artifact["lifecycle_packets"]] == [
        "presented",
        "accepted_shadow",
        "dismissed_shadow",
        "negotiating",
    ]
    assert artifact["lifecycle_summary"] == {
        "presented": 1,
        "accepted_shadow": 1,
        "dismissed_shadow": 1,
        "negotiating": 1,
    }
    assert "Fixture headline, not user-facing" not in serialized
    assert artifact["proposal_committed"] is False
    assert artifact["rescue_committed"] is False
    assert artifact["ledger_entry_created"] is False
    assert artifact["day_budget_mutated"] is False
    assert artifact["body_plan_mutated"] is False
    assert artifact["meal_thread_mutated"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["recommendation_served"] is False


def test_rescue_chain_adapter_blocks_chain_claim_drift_before_lifecycle() -> None:
    from app.rescue.application.chain_lifecycle_adapter import (
        build_rescue_chain_lifecycle_shadow_packets,
    )

    chain = _rescue_chain_artifact()
    chain["proposal_committed"] = True

    artifact = build_rescue_chain_lifecycle_shadow_packets(
        rescue_shadow_chain_artifact=chain,
        interaction_intents=["present"],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["rescue_shadow_chain_runner_artifact.proposal_committed"]
    assert artifact["lifecycle_packets"] == []
    assert artifact["proposal_committed"] is False
    assert artifact["day_budget_mutated"] is False


def test_rescue_chain_adapter_blocks_raw_text_or_unknown_intent() -> None:
    from app.rescue.application.chain_lifecycle_adapter import (
        build_rescue_chain_lifecycle_shadow_packets,
    )

    artifact = build_rescue_chain_lifecycle_shadow_packets(
        rescue_shadow_chain_artifact=_rescue_chain_artifact(),
        interaction_intents=["raw_text_accept"],
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == ["interaction_intent.unsupported:raw_text_accept"]
    assert artifact["lifecycle_packets"] == []
    assert artifact["proposal_committed"] is False


def _rescue_chain_artifact() -> dict[str, object]:
    return run_rescue_shadow_chain(
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
