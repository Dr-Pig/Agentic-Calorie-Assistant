from __future__ import annotations


def test_reviewed_memory_offer_runner_builds_non_served_three_node_packet() -> None:
    from app.recommendation.application.reviewed_memory_offer_runner import (
        build_reviewed_memory_recommendation_offer_packet,
    )

    packet = build_reviewed_memory_recommendation_offer_packet(
        memory_summary_projection=_memory_projection(),
        remaining_budget_kcal=700,
        requested_surface="chat",
    )

    assert packet["artifact_type"] == "recommendation_offer_shadow_packet"
    assert packet["status"] == "pass"
    assert packet["new_report_family_created"] is False
    assert packet["reviewed_memory_offer_runner_used"] is True
    assert packet["reviewed_memory_projection_used"] is True
    assert packet["source_memory_artifact_type"] == (
        "runtime_lab_memory_consumer_summary_projection"
    )
    assert packet["runner_stage_trace"] == [
        {
            "stage": "reviewed_memory_projection",
            "artifact_type": "runtime_lab_memory_consumer_summary_projection",
            "status": "pass",
        },
        {
            "stage": "recommendation_three_node_shadow",
            "artifact_type": "recommendation_three_node_shadow_artifact",
            "status": "pass",
        },
        {
            "stage": "recommendation_summary_quality",
            "artifact_type": "recommendation_shadow_summary_consumer_quality_report",
            "status": "pass",
        },
        {
            "stage": "recommendation_offer_shadow_packet",
            "artifact_type": "recommendation_offer_shadow_packet",
            "status": "pass",
        },
    ]
    assert packet["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert [row["logical_stage"] for row in packet["logical_stage_trace"]] == [
        "recommendation_context_result",
        "candidate_spec",
        "candidate_retrieval_guard_scoring",
        "ranking_result",
        "recommendation_response_result",
    ]
    assert packet["selected_primary"]["candidate_id"] == (
        "golden-order-morning-bar-oatmeal-latte"
    )
    assert packet["selected_primary"]["source_refs"] == [
        "memory_candidate:golden-order-morning-bar-oatmeal-latte"
    ]
    assert packet["offer_synthesis_trace"] == {
        "owner": "llm_fixture",
        "selected_candidate_id": "golden-order-morning-bar-oatmeal-latte",
        "backup_candidate_ids": [],
        "explanation_present": True,
    }
    assert packet["decision_ownership"] == {
        "recommendation_planning": "llm_fixture",
        "candidate_retrieval_guard_scoring": "deterministic",
        "offer_synthesis": "llm_fixture",
        "deterministic_role": "validate_filter_score_and_reject_only",
        "llm_role": "plan_and_synthesize_without_mutation",
    }
    assert packet["ux_packet"] == {
        "surface": "chat",
        "serve_allowed": False,
        "primary_candidate_id": "golden-order-morning-bar-oatmeal-latte",
        "backup_candidate_ids": [],
        "explanation": "Reviewed memory golden order fits the remaining budget.",
    }
    assert packet["recommendation_served"] is False
    assert packet["user_facing_behavior_changed"] is False
    assert packet["manager_context_packet_changed"] is False
    assert packet["durable_product_memory_written"] is False
    assert packet["canonical_product_mutation_allowed"] is False
    assert packet["intake_handoff_created"] is False


def test_reviewed_memory_offer_runner_blocks_memory_claim_drift_before_offer() -> None:
    from app.recommendation.application.reviewed_memory_offer_runner import (
        build_reviewed_memory_recommendation_offer_packet,
    )

    projection = _memory_projection()
    projection["recommendation_served"] = True

    packet = build_reviewed_memory_recommendation_offer_packet(
        memory_summary_projection=projection,
        remaining_budget_kcal=700,
    )

    assert packet["status"] == "blocked"
    assert packet["reviewed_memory_projection_used"] is False
    assert "reviewed_memory_bridge.consumer_summary_projection.recommendation_served" in packet[
        "blockers"
    ]
    assert packet["selected_primary"] is None
    assert packet["ux_packet"] is None
    assert packet["recommendation_served"] is False
    assert packet["user_facing_behavior_changed"] is False
    assert packet["canonical_product_mutation_allowed"] is False


def _memory_projection() -> dict[str, object]:
    return {
        "artifact_type": "runtime_lab_memory_consumer_summary_projection",
        "status": "pass",
        "preference_profile_summary": {
            "freshness_posture": "fresh",
            "accepted_shadow_candidate_ids": [
                "golden-order-morning-bar-oatmeal-latte"
            ],
            "negative_preference_blockers": [
                "negative-preference-ingredient-cilantro"
            ],
        },
        "golden_order_summary": {
            "orders": [
                {
                    "candidate_id": "golden-order-morning-bar-oatmeal-latte",
                    "store_name": "FamilyMart",
                    "summary": "FamilyMart oatmeal and latte",
                    "item_names": ["oatmeal", "latte"],
                    "estimated_kcal": 520,
                }
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
