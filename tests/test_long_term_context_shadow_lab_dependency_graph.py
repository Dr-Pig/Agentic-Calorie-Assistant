from __future__ import annotations

from tests.long_term_context_shadow_fixture import _fixture_payload


def test_memory_dependency_graph_declares_recommendation_memory_as_prerequisite() -> (
    None
):
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_dependency_graph_shadow_eval"
    ]

    assert artifact["artifact_type"] == "memory_dependency_graph_shadow_eval"
    assert artifact["runtime_effect_allowed"] is False
    assert artifact["manager_context_injected"] is False
    assert artifact["live_consumer_activation_allowed"] is False
    assert artifact["topological_build_order"][0] == "memory_candidate_substrate"
    assert "recommendation_runtime" in artifact["blocked_live_consumers"]

    recommendation = artifact["consumer_dependencies"]["recommendation"]
    assert recommendation["memory_required_before_live_runtime"] is True
    assert recommendation["blocked_until"] == [
        "durable_memory_review_store",
        "reviewed_preference_profile_summary",
        "runtime_context_pack_injection_gate",
        "recommendation_graph_runtime",
    ]
    assert recommendation["shadow_buildable_now"] == [
        "preference_candidate_extraction",
        "negative_preference_filtering_eval",
        "golden_order_derived_view_eval",
        "recommendation_context_pack_eval",
    ]


def test_memory_dependency_graph_keeps_consumer_boundaries_product_aligned() -> None:
    from app.memory.application.long_term_context_shadow_lab import (
        build_shadow_lab_artifacts,
    )

    artifact = build_shadow_lab_artifacts(_fixture_payload())[
        "memory_dependency_graph_shadow_eval"
    ]

    calibration = artifact["consumer_dependencies"]["calibration"]
    assert calibration["memory_role"] == "bias_attribution_and_quality_context"
    assert calibration["forbidden_effects"] == [
        "calorie_truth_rewrite",
        "body_plan_mutation",
        "day_budget_mutation",
    ]

    proactive = artifact["consumer_dependencies"]["proactive"]
    assert "proactive_silence_policy_eval" in proactive["shadow_buildable_now"]
    assert "scheduler_activation" in proactive["blocked_until"]
    assert proactive["memory_role"] == "timing_suppression_and_context_quality"

    rescue = artifact["consumer_dependencies"]["rescue_later"]
    assert rescue["memory_required_before_live_runtime"] is True
    assert rescue["memory_role"] == "viability_context_after_budget_truth"
    assert "proposal_commit_runtime" in rescue["blocked_until"]

    for dependency in artifact["consumer_dependencies"].values():
        assert dependency["runtime_effect_allowed"] is False
        assert dependency["deterministic_boundary"]["may_decide_runtime_use"] is False
