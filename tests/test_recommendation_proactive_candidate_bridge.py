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
