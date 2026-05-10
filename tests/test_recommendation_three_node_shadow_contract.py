from __future__ import annotations

from app.recommendation.application.three_node_shadow_contract import (
    build_fixture_recommendation_three_node_input,
    run_recommendation_three_node_shadow,
)


def test_three_node_contract_allows_llm_decision_after_deterministic_guard() -> None:
    payload = build_fixture_recommendation_three_node_input()

    artifact = run_recommendation_three_node_shadow(payload)

    assert artifact["artifact_type"] == "recommendation_three_node_shadow_artifact"
    assert artifact["status"] == "pass"
    assert artifact["node_order"] == [
        "manager_recommendation_decision_fixture",
        "deterministic_candidate_guard",
        "shadow_offer_packet_fixture",
    ]
    assert artifact["physical_graph_profile"] == (
        "three_node_recommendation_planning_guard_offer"
    )
    assert artifact["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert [row["logical_stage"] for row in artifact["logical_stage_trace"]] == [
        "recommendation_context_result",
        "candidate_spec",
        "candidate_retrieval_guard_scoring",
        "ranking_result",
        "recommendation_response_result",
    ]
    assert artifact["legacy_five_node_artifact_source"] is False
    assert artifact["llm_owned_nodes"] == [
        "manager_recommendation_decision_fixture",
        "shadow_offer_packet_fixture",
    ]
    assert artifact["deterministic_nodes"] == ["deterministic_candidate_guard"]
    assert artifact["candidate_guard"]["allowed_candidate_ids"] == ["golden-1"]
    assert artifact["candidate_guard"]["filtered_candidates"] == [
        {"candidate_id": "over-1", "reason_codes": ["over_budget"]},
        {
            "candidate_id": "cilantro-1",
            "reason_codes": ["confirmed_negative_preference"],
        },
        {"candidate_id": "fried-1", "reason_codes": ["accepted_rescue_conflict"]},
        {"candidate_id": "closed-1", "reason_codes": ["unavailable"]},
    ]
    assert artifact["selected_candidate_id"] == "golden-1"
    assert artifact["shadow_offer_packet"] == {
        "candidate_id": "golden-1",
        "is_canonical_truth": False,
        "recommendation_served": False,
        "intake_commit_requested": False,
        "source_refs": ["fixture:golden-1"],
    }
    assert artifact["activation_flags"] == _false_activation_flags()


def test_three_node_contract_blocks_non_fixture_llm_node() -> None:
    payload = build_fixture_recommendation_three_node_input()
    payload["manager_recommendation_decision_fixture"]["decision_mode"] = "deterministic"

    artifact = run_recommendation_three_node_shadow(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "manager_recommendation_decision_fixture.decision_mode_not_llm_fixture"
    ]
    assert artifact["candidate_guard"]["allowed_candidate_ids"] == []
    assert artifact["shadow_offer_packet"] is None
    assert artifact["activation_flags"] == _false_activation_flags()


def test_three_node_contract_blocks_filtered_selection_and_offer_claims() -> None:
    payload = build_fixture_recommendation_three_node_input()
    payload["manager_recommendation_decision_fixture"]["top_candidate_id"] = "over-1"
    payload["shadow_offer_packet_fixture"]["candidate_id"] = "over-1"
    payload["shadow_offer_packet_fixture"]["recommendation_served"] = True
    payload["shadow_offer_packet_fixture"]["is_canonical_truth"] = True
    payload["shadow_offer_packet_fixture"]["intake_commit_requested"] = True

    artifact = run_recommendation_three_node_shadow(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "manager_recommendation_decision_fixture.top_candidate_not_allowed:over-1",
        "shadow_offer_packet_fixture.candidate_not_allowed:over-1",
        "shadow_offer_packet_fixture.recommendation_served_not_allowed",
        "shadow_offer_packet_fixture.is_canonical_truth_not_allowed",
        "shadow_offer_packet_fixture.intake_commit_requested_not_allowed",
    ]
    assert artifact["shadow_offer_packet"] is None
    assert artifact["activation_flags"] == _false_activation_flags()


def _false_activation_flags() -> dict[str, bool]:
    return {
        "runtime_effect_allowed": False,
        "mainline_runtime_connected": False,
        "mainline_route_or_api_mount_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "user_facing_behavior_changed": False,
        "live_provider_used": False,
        "recommendation_served": False,
        "intake_committed": False,
        "product_readiness_claimed": False,
    }
