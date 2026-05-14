from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_recommendation_output_becomes_proactive_candidate_without_delivery() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-proactive-bridge-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    bridge = proactive["recommendation_proactive_candidate_bridge"]
    candidate = next(
        item
        for item in proactive["candidates"]
        if item["trigger_type"] == "recommendation_prompt"
    )

    assert bridge["artifact_type"] == (
        "advanced_product_lab_recommendation_proactive_candidate_bridge"
    )
    assert bridge["status"] == "pass"
    assert bridge["reads_recommendation_outputs"] is True
    assert bridge["candidate_created"] is True
    assert bridge["candidate_spec"]["trigger_type"] == "recommendation_prompt"
    assert bridge["candidate_spec"]["candidate_kind"] == "next_meal_recommendation"
    assert bridge["source_selected_candidate_id"] == "golden-1"
    assert bridge["scheduler_delivery_allowed"] is False
    assert bridge["notification_delivery_allowed"] is False
    assert bridge["served_to_mainline_user"] is False
    assert candidate["candidate_id"] == "recommendation_prompt:0"
    assert candidate["scheduler_delivery_allowed"] is False
    assert candidate["notification_delivery_allowed"] is False


def test_bridge_preserves_recommendation_quality_trace_for_proactive_review() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("recommendation-proactive-quality-trace-turn"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    proactive = artifact["product_lab_proactive_artifact"]
    bridge = proactive["recommendation_proactive_candidate_bridge"]
    candidate = next(
        item
        for item in proactive["candidates"]
        if item["trigger_type"] == "recommendation_prompt"
    )
    delivery_trace = proactive["delivery_packet"]["candidate_traces_by_candidate"][
        "recommendation_prompt"
    ]

    assert bridge["candidate_spec"]["downstream_workflow_family"] == "recommendation"
    assert bridge["candidate_spec"]["candidate_quality_tier"] == "high"
    assert bridge["candidate_spec"]["proactive_intensity"] == "primary_plus_backup"
    assert bridge["candidate_spec"]["source_bridge_trace"] == {
        "downstream_workflow_family": "recommendation",
        "source_selected_candidate_id": "golden-1",
        "candidate_quality_tier": "high",
        "proactive_intensity": "primary_plus_backup",
        "source_type": "golden_order",
        "quality_score": 96,
        "quality_signals": [
            "evidence:exact",
            "availability:available",
            "budget_fit",
        ],
        "source_refs": ["memory_candidate:pref-1", "memory_candidate:golden-1"],
        "recommendation_handoff_mode": "chat_first_invitation",
    }
    assert candidate["downstream_workflow_family"] == "recommendation"
    assert candidate["candidate_quality_tier"] == "high"
    assert candidate["recommendation_candidate_id"] == "golden-1"
    assert delivery_trace["downstream_workflow_family"] == "recommendation"
    assert delivery_trace["candidate_quality_tier"] == "high"


def test_bridge_blocks_low_quality_or_generic_recommendation_for_proactive() -> None:
    from app.advanced_shadow_lab.product_lab_proactive_recommendation_bridge import (
        build_recommendation_proactive_candidate_bridge,
    )

    bridge = build_recommendation_proactive_candidate_bridge(
        recommendation_artifact={
            "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
            "status": "pass",
            "recommendation_served_to_lab": True,
            "proactive_recommendation_candidate_allowed": True,
            "offer_synthesis": {
                "selected_primary": {
                    "candidate_id": "generic-1",
                    "quality_tier": "low",
                    "proactive_intensity": "none",
                    "source_type": "generic_category",
                }
            },
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert bridge["status"] == "blocked"
    assert bridge["candidate_created"] is False
    assert bridge["candidate_spec"] is None
    assert bridge["blockers"] == [
        "recommendation.low_quality_context",
        "recommendation.generic_category_only",
    ]
    assert bridge["scheduler_delivery_allowed"] is False
    assert bridge["notification_delivery_allowed"] is False


def test_bridge_omits_cleanly_when_recommendation_is_not_eligible() -> None:
    from app.advanced_shadow_lab.product_lab_proactive_recommendation_bridge import (
        build_recommendation_proactive_candidate_bridge,
    )

    bridge = build_recommendation_proactive_candidate_bridge(
        recommendation_artifact={
            "artifact_type": "advanced_product_lab_recommendation_runtime_artifact",
            "status": "pass",
            "recommendation_served_to_lab": True,
            "proactive_recommendation_candidate_allowed": False,
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    assert bridge["status"] == "omitted"
    assert bridge["reason"] == "recommendation_not_eligible_for_proactive"
    assert bridge["candidate_created"] is False
    assert bridge["candidate_spec"] is None
    assert bridge["scheduler_delivery_allowed"] is False
    assert bridge["notification_delivery_allowed"] is False


def test_recommendation_train_records_pr15_completion_and_next_active_slice() -> None:
    import yaml

    with open(
        "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 9
    assert plan["last_completed_pr_number"] >= 15
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 16
    assert {
        "pr_number": 15,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_proactive_candidate_bridge_completed_locally",
    } in plan["last_merge_evidence"]["completed_prs"]
