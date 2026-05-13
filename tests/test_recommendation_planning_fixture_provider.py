from __future__ import annotations

import json

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.recommendation.application.planning_fixture_provider import (
    FixtureRecommendationPlanningProvider,
    planning_fixture_output_blockers,
)


def test_planning_fixture_provider_outputs_only_llm_owned_planning_fields() -> None:
    provider = FixtureRecommendationPlanningProvider(model_profile="fast_router_model")

    artifact = provider.plan(
        turn={"semantic_intent_fixture": "pre_meal_planning"},
        fixture_inputs=build_product_lab_fixture_inputs(),
        memory_context_pack={
            "selected_record_ids": ["golden-bento-1"],
            "entries": [],
        },
    )
    serialized = json.dumps(artifact)

    assert artifact["artifact_type"] == "recommendation_planning_fixture_output"
    assert artifact["node"] == "recommendation_planning"
    assert artifact["owner"] == "llm_fixture_provider"
    assert artifact["decision_mode"] == "llm_fixture"
    assert artifact["model_profile"] == "fast_router_model"
    assert artifact["recommendation_context_result"]["user_goal"] == "pre_meal_planning"
    assert artifact["recommendation_context_result"]["soft_preferences"] == [
        "golden-bento-1"
    ]
    assert artifact["candidate_spec"]["desired_source_types"] == [
        "memory_golden_order",
        "golden_order",
        "nearby_fixture",
        "safe_fallback",
    ]
    assert artifact["candidate_spec"]["hard_blockers_must_be_deterministic"] is True
    assert "allowed_candidate_ids" not in serialized
    assert "qualified_candidates" not in serialized
    assert "selected_primary" not in serialized
    assert artifact["blockers"] == []


def test_planning_fixture_provider_blocks_retrieval_or_offer_fields() -> None:
    artifact = {
        "artifact_type": "recommendation_planning_fixture_output",
        "recommendation_context_result": {"user_goal": "pre_meal"},
        "candidate_spec": {"desired_source_types": ["golden_order"]},
        "allowed_candidate_ids": ["golden-1"],
        "selected_primary": {"candidate_id": "golden-1"},
    }

    assert planning_fixture_output_blockers(artifact) == [
        "planning_output.forbidden_field:allowed_candidate_ids",
        "planning_output.forbidden_field:selected_primary",
    ]


def test_planning_fixture_provider_schema_blocks_missing_context_or_spec() -> None:
    assert planning_fixture_output_blockers(
        {
            "artifact_type": "recommendation_planning_fixture_output",
            "recommendation_context_result": {},
            "candidate_spec": {},
        }
    ) == [
        "recommendation_context_result.user_goal_missing",
        "candidate_spec.desired_source_types_missing",
    ]


def test_recommendation_train_records_pr4_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 20
    assert plan["last_completed_pr_number"] >= 4
    assert plan["active_pr_number"] >= 5
    assert {
        "pr_number": 4,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_planning_fixture_provider_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]
