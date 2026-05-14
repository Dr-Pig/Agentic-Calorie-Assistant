from __future__ import annotations

from app.advanced_shadow_lab.product_lab_fixture_inputs import (
    build_product_lab_fixture_inputs,
)
from app.advanced_shadow_lab.product_lab_runtime import run_advanced_product_lab_turn
from tests.test_advanced_product_lab_runtime import _turn


def test_proactive_dashboard_mirror_projects_active_chat_cards_read_only() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn=_turn("proactive-dashboard-active"),
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    mirror = artifact["product_lab_proactive_dashboard_mirror"]

    assert mirror["artifact_type"] == (
        "advanced_product_lab_proactive_dashboard_mirror_read_model"
    )
    assert mirror["status"] == "pass"
    assert mirror["read_model_only"] is True
    assert mirror["ui_owns_truth"] is False
    assert mirror["canonical_product_mutation_allowed"] is False
    assert mirror["scheduler_delivery_allowed"] is False
    assert mirror["notification_delivery_allowed"] is False
    assert mirror["active_card_ids"] == ["recommendation_prompt:0", "rescue_nudge:1"]
    assert mirror["suppressed_card_count"] == 0
    first = mirror["active_cards"][0]
    assert first["candidate_id"] == "recommendation_prompt:0"
    assert first["workflow_family"] == "recommendation"
    assert first["controls_visible"] is True
    assert first["action_ids"] == [
        "dismiss:recommendation_prompt:0",
        "snooze:recommendation_prompt:0",
        "reopen_or_modify:recommendation_prompt:0",
    ]
    assert first["source_refs"] == [
        "advanced_product_lab_recommendation_runtime_artifact",
        "advanced_product_lab_proactive_runtime_artifact",
    ]
    assert mirror["raw_trace_exposed_to_ui"] is False


def test_proactive_dashboard_mirror_projects_suppressed_cards_without_actions() -> None:
    artifact = run_advanced_product_lab_turn(
        lab_mode="isolated_advanced_product_lab",
        turn={
            **_turn("proactive-dashboard-suppressed"),
            "proactive_gate_context": {"local_time": "23:15"},
        },
        fixture_inputs=build_product_lab_fixture_inputs(),
    )

    mirror = artifact["product_lab_proactive_dashboard_mirror"]

    assert mirror["status"] == "pass"
    assert mirror["active_cards"] == []
    assert mirror["suppressed_card_count"] == 2
    assert [
        (item["trigger_type"], item["omission_reason"])
        for item in mirror["suppressed_cards"]
    ] == [
        ("recommendation_prompt", "quiet_hours"),
        ("rescue_nudge", "quiet_hours"),
    ]
    assert all(item["actions"] == [] for item in mirror["suppressed_cards"])
    assert mirror["ui_owns_truth"] is False
