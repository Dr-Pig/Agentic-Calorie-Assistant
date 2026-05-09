from __future__ import annotations

from app.recommendation.application.five_node_shadow_fixture import (
    build_fixture_recommendation_five_node_input,
)
from app.recommendation.application.five_node_shadow_runner import (
    run_recommendation_five_node_lab_runner,
)


def test_five_node_runner_records_pass_chain_without_runtime_effect() -> None:
    payload = build_fixture_recommendation_five_node_input()

    artifact = run_recommendation_five_node_lab_runner(payload)

    assert artifact["artifact_type"] == "recommendation_five_node_lab_runner_artifact"
    assert artifact["status"] == "pass"
    assert artifact["runner_role"] == "lab_observability_only"
    assert artifact["node_order"] == _node_order()
    assert artifact["llm_owned_nodes"] == [
        "recommendation_context_fixture",
        "candidate_spec_fixture",
        "ranking_synthesis_fixture",
        "response_offer_fixture",
    ]
    assert artifact["deterministic_nodes"] == ["deterministic_candidate_retrieval"]
    assert artifact["candidate_retrieval"]["allowed_candidate_ids"] == ["golden-1"]
    assert artifact["candidate_retrieval"]["filtered_candidates"] == [
        {"candidate_id": "over-1", "reason_codes": ["over_budget"]},
        {
            "candidate_id": "cilantro-1",
            "reason_codes": ["confirmed_negative_preference"],
        },
        {"candidate_id": "fried-1", "reason_codes": ["accepted_rescue_conflict"]},
        {"candidate_id": "closed-1", "reason_codes": ["unavailable"]},
    ]
    assert artifact["ranking_synthesis"]["selected_candidate_id"] == "golden-1"
    assert artifact["response_offer_packet"] == {
        "candidate_id": "golden-1",
        "is_canonical_truth": False,
        "recommendation_served": False,
        "intake_commit_requested": False,
        "source_refs": ["fixture:golden-1"],
    }
    assert artifact["node_trace"] == [
        {"node": "recommendation_context_fixture", "owner": "llm_fixture"},
        {"node": "candidate_spec_fixture", "owner": "llm_fixture"},
        {"node": "deterministic_candidate_retrieval", "owner": "deterministic"},
        {"node": "ranking_synthesis_fixture", "owner": "llm_fixture"},
        {"node": "response_offer_fixture", "owner": "llm_fixture"},
    ]
    assert artifact["activation_flags"] == _false_activation_flags()


def test_five_node_runner_blocks_non_fixture_llm_node() -> None:
    payload = build_fixture_recommendation_five_node_input()
    payload["ranking_synthesis_fixture"]["decision_mode"] = "deterministic"

    artifact = run_recommendation_five_node_lab_runner(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "ranking_synthesis_fixture.decision_mode_not_llm_fixture"
    ]
    assert artifact["candidate_retrieval"]["allowed_candidate_ids"] == []
    assert artifact["response_offer_packet"] is None
    assert artifact["activation_flags"] == _false_activation_flags()


def test_five_node_runner_blocks_ranking_filtered_or_unknown_candidate() -> None:
    payload = build_fixture_recommendation_five_node_input()
    payload["ranking_synthesis_fixture"]["selected_candidate_id"] = "over-1"
    payload["ranking_synthesis_fixture"]["ranked_candidate_ids"] = ["over-1", "golden-1"]

    artifact = run_recommendation_five_node_lab_runner(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "ranking_synthesis_fixture.selected_candidate_not_allowed:over-1",
        "ranking_synthesis_fixture.ranked_candidate_not_allowed:over-1",
    ]
    assert artifact["response_offer_packet"] is None


def test_five_node_runner_blocks_response_claims_and_commit_attempts() -> None:
    payload = build_fixture_recommendation_five_node_input()
    payload["response_offer_fixture"]["recommendation_served"] = True
    payload["response_offer_fixture"]["is_canonical_truth"] = True
    payload["response_offer_fixture"]["intake_commit_requested"] = True

    artifact = run_recommendation_five_node_lab_runner(payload)

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "response_offer_fixture.recommendation_served_not_allowed",
        "response_offer_fixture.is_canonical_truth_not_allowed",
        "response_offer_fixture.intake_commit_requested_not_allowed",
    ]
    assert artifact["response_offer_packet"] is None


def _node_order() -> list[str]:
    return [
        "recommendation_context_fixture",
        "candidate_spec_fixture",
        "deterministic_candidate_retrieval",
        "ranking_synthesis_fixture",
        "response_offer_fixture",
    ]


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
