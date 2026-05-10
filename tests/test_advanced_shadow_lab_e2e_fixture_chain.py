from __future__ import annotations

import json

from app.advanced_shadow_lab.e2e_fixture_chain import (
    run_advanced_shadow_e2e_fixture_chain,
)
from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
)


EXPECTED_UX_JOURNEY_IDS = ["F", "F2", "I", "L", "M", "N"]
EXPECTED_TERMINAL_OUTPUTS = {
    "F": ("same_day_rescue_coaching_hook", "rescue", "open_rescue_discussion"),
    "F2": ("planned_event_rescue_negotiation_packet", "rescue", "review_planned_event_adjustment"),
    "I": ("calibration_proposal_review_packet", "calibration", "review_calibration_proposal"),
    "L": ("recommendation_offer_pending_intent_packet", "recommendation", "review_recommendation_offer"),
    "M": ("memory_review_adjusted_recommendation_packet", "recommendation", "review_memory_signal"),
    "N": ("proactive_no_send_intervention_packet", "proactive", "review_no_send_candidate"),
}


def test_fixture_chain_terminates_in_no_send_review_sink() -> None:
    artifact = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=_memory_projection(),
        recommendation_payload=_recommendation_payload(),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_proposal_candidate_output(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
        interaction_plan=[
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    )
    serialized = json.dumps(artifact, ensure_ascii=False)

    assert artifact["artifact_type"] == "advanced_shadow_e2e_fixture_chain_artifact"
    assert artifact["status"] == "pass"
    assert artifact["stage_order"] == [
        "recommendation_three_node_shadow_artifact",
        "recommendation_shadow_summary_consumer_quality_report",
        "recommendation_prompt_no_send_review",
        "rescue_shadow_summary_context_projection",
        "rescue_shadow_chain_runner_artifact",
        "rescue_nudge_no_send_review",
        "proactive_no_send_nudge_candidate_bridge",
        "proactive_no_send_review_sink_artifact",
    ]
    assert [row["status"] for row in artifact["stage_trace"]] == [
        "pass",
        "pass",
        "candidate_for_human_review",
        "pass",
        "pass",
        "context_available",
        "pass",
        "pass",
    ]
    assert [stage["artifact_type"] for stage in artifact["stage_artifacts"]] == artifact[
        "stage_order"
    ]
    assert artifact["stage_artifacts"][1]["artifact_type"] == (
        "recommendation_shadow_summary_consumer_quality_report"
    )
    assert artifact["stage_artifacts"][1]["three_node_lab_bridge_used"] is True
    assert artifact["stage_artifacts"][1]["five_node_lab_bridge_used"] is False
    assert artifact["terminal_review_sink"]["status"] == "pass"
    assert artifact["chat_ux_packet"]["artifact_type"] == (
        "advanced_shadow_chat_ux_packet_artifact"
    )
    assert artifact["chat_ux_packet"]["status"] == "pass"
    assert artifact["chat_ux_packet"]["packet_count"] == 2
    assert artifact["terminal_review_sink"]["record_count"] == 2
    assert artifact["terminal_review_sink"]["control_path_evidence"] == {
        "status": "pass",
        "candidate_count": 2,
        "all_candidates_have_required_controls": True,
        "configured_paths": {
            "dismiss": True,
            "snooze": True,
            "undo": True,
        },
        "interaction_actions_observed": ["dismiss", "snooze"],
        "observed_all_interaction_actions": False,
        "next_signal_required_present": True,
    }
    assert [
        record["trigger_type"]
        for record in artifact["terminal_review_sink"]["records"]
    ] == ["recommendation_prompt", "rescue_nudge"]
    assert artifact["delivery_attempted"] is False
    assert artifact["scheduler_enabled"] is False
    assert artifact["push_or_line_delivery_connected"] is False
    assert artifact["mainline_runtime_connected"] is False
    assert artifact["manager_context_packet_changed"] is False
    assert artifact["user_facing_behavior_changed"] is False
    assert artifact["canonical_product_mutation_allowed"] is False
    assert artifact["durable_product_memory_written"] is False
    assert "hidden-food-candidate" not in serialized
    assert "Fixture headline, not user-facing" not in serialized


def test_fixture_chain_emits_terminal_evidence_for_each_mapped_ux_journey() -> None:
    artifact = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=_memory_projection(),
        recommendation_payload=_recommendation_payload(),
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_proposal_candidate_output(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
        interaction_plan=[
            {"action": "dismiss", "dismiss_reason": "too_frequent"},
            {"action": "snooze", "snooze_minutes": 120},
        ],
    )

    evidence = artifact["journey_terminal_evidence"]

    assert [row["journey_id"] for row in evidence] == EXPECTED_UX_JOURNEY_IDS
    for row in evidence:
        output_kind, workflow_family, primary_affordance = EXPECTED_TERMINAL_OUTPUTS[
            row["journey_id"]
        ]
        terminal = row["ux_terminal_output"]

        assert row["status"] == "pass"
        assert row["comparison_scope"] == "ux_journey_terminal_lab_only_evidence"
        assert row["source_artifact_refs"]
        assert row["product_contract_refs"]
        assert row["required_trace_fields"]
        assert terminal["status"] == "pass"
        assert terminal["output_kind"] == output_kind
        assert terminal["workflow_family"] == workflow_family
        assert terminal["surface"] == "chat"
        assert terminal["chat_first"] is True
        assert terminal["control_contract"]["primary_affordance"] == primary_affordance
        assert terminal["control_contract"]["dismiss_available"] is True
        assert terminal["control_contract"]["served_to_user"] is False
        assert terminal["control_contract"]["canonical_mutation_requested"] is False
        assert terminal["control_contract"]["scheduler_enqueued"] is False
        assert row["terminal_artifact_refs"] == [
            "advanced_shadow_e2e_fixture_chain_artifact",
            "proactive_no_send_review_sink_artifact",
            "advanced_shadow_chat_ux_packet_artifact",
        ]
        assert row["no_send_control_evidence"] == {
            "status": "pass",
            "configured_paths": {"dismiss": True, "snooze": True, "undo": True},
            "next_signal_required_present": True,
        }
        assert row["semantic_decision_inferred_by_runner"] is False
        assert row["mainline_runtime_connected"] is False
        assert row["delivery_attempted"] is False
        assert row["recommendation_served"] is False
        assert row["rescue_committed"] is False
        assert row["proposal_committed"] is False
        assert row["mutation_changed"] is False
        assert row["user_facing_behavior_changed"] is False
        assert row["product_readiness_claimed"] is False


def test_fixture_chain_blocks_activation_drift_before_review_sink() -> None:
    recommendation = _recommendation_payload()
    recommendation["shadow_offer_packet_fixture"]["recommendation_served"] = True

    artifact = run_advanced_shadow_e2e_fixture_chain(
        memory_summary_projection=_memory_projection(),
        recommendation_payload=recommendation,
        derived_memory_views=_derived_views(),
        current_budget_view=_budget_view(),
        active_body_plan_view=_body_plan_view(),
        open_proposals_view={"open_rescue_proposal_count": 0},
        proposal_candidate_output=_proposal_candidate_output(),
        user_control_models={
            "recommendation_prompt": _controls("new_app_open_with_qualified_pool"),
            "rescue_nudge": _controls(
                "material_budget_change_or_user_reopens_rescue"
            ),
        },
        interaction_plan=[],
    )

    assert artifact["status"] == "blocked"
    assert "recommendation_three_node_shadow_artifact.status_blocked" in artifact[
        "blockers"
    ]
    assert artifact["terminal_review_sink"]["status"] == "not_run"
    assert artifact["delivery_attempted"] is False
    assert artifact["recommendation_served"] is False
    assert artifact["proactive_sent"] is False
    assert artifact["mutation_changed"] is False


def _recommendation_payload() -> dict[str, object]:
    payload = build_fixture_recommendation_three_node_input()
    golden = _candidate(payload, "golden-1")
    golden.update(
        {
            "estimated_kcal": 520,
            "evidence_posture": "exact",
            "availability_posture": "available",
            "realistic_executable": True,
            "user_accessible": True,
            "store_name": "FamilyMart",
            "store_metadata": {"chain": "familymart", "raw_menu_blob": "hidden"},
            "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
            "debug_candidate_copy": "hidden-food-candidate",
        }
    )
    return payload


def _candidate(payload: dict[str, object], candidate_id: str) -> dict[str, object]:
    for item in payload["candidate_source_fixture"]:  # type: ignore[index]
        if isinstance(item, dict) and item.get("candidate_id") == candidate_id:
            return item
    raise AssertionError(f"candidate not found: {candidate_id}")


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": ["pref-1"],
            "negative_preference_blockers": ["neg-1"],
        },
        "golden_order_summary": {
            "orders": [{"candidate_id": "golden-1", "store_name": "FamilyMart"}]
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


def _proposal_candidate_output() -> dict[str, object]:
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
