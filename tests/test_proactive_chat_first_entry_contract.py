from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.proactive_entry_contract import (
    build_proactive_entry_contract,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_proactive_chat_first_pr_train.yaml"
)


def test_proactive_entry_contract_requires_closed_upstream_trains_and_controls() -> None:
    artifact = build_proactive_entry_contract(
        recommendation_train=_recommendation_train(),
        proactive_golden_set=_proactive_golden_set(),
    )

    assert artifact["artifact_type"] == "advanced_product_lab_proactive_entry_contract"
    assert artifact["status"] == "pass"
    assert artifact["ready_for_proactive_train"] is True
    assert artifact["ready_for_mainline_activation"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["lab_chat_delivery_allowed"] is True
    assert artifact["production_notification_delivery_allowed"] is False
    assert artifact["parent_recommendation_train"]["closed_by_pr"] == 24
    assert artifact["wake_to_delivery_ladder"] == [
        "deterministic_trigger_gate",
        "contextual_send_skip_decision",
        "lab_chat_first_delivery",
        "control_feedback_projection",
    ]
    assert artifact["control_path_required"] == {
        "dismiss": True,
        "snooze": True,
        "reopen_or_modify": True,
        "next_signal_required": True,
        "user_facing_undo_label_allowed": False,
    }
    assert artifact["next_train"]["planned_pr_count"] == 24
    assert artifact["next_train"]["dynamic_remaining_pr_count"] == 23
    assert artifact["blockers"] == []


def test_proactive_entry_contract_blocks_unclosed_recommendation_or_narrow_golden_set() -> None:
    artifact = build_proactive_entry_contract(
        recommendation_train={**_recommendation_train(), "status": "active"},
        proactive_golden_set={**_proactive_golden_set(), "status": "draft"},
    )

    assert artifact["status"] == "blocked"
    assert artifact["ready_for_proactive_train"] is False
    assert artifact["blockers"] == [
        "recommendation_train.status_not_completed",
        "proactive_golden_set.status_not_active_alignment_contract",
    ]


def test_proactive_chat_first_train_is_machine_readable_and_lab_complete() -> None:
    plan = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))

    assert plan["artifact_type"] == "advanced_product_lab_proactive_chat_first_pr_train"
    assert plan["status"] == "active"
    assert plan["planned_pr_count"] == 24
    assert plan["dynamic_remaining_pr_count"] <= 23
    assert plan["last_completed_pr_number"] >= 1
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 2
    assert plan["current_mainline"] == "advanced_product_lab_proactive_chat_first_integration"
    assert plan["parent_recommendation_train"] == {
        "path": "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
        "closed_by_pr": 24,
        "entry_contract_artifact": (
            "artifacts/advanced_product_lab_proactive_entry_contract_pr1.json"
        ),
    }
    assert plan["required_artifact_flags"]["lab_chat_delivery_allowed"] is True
    assert plan["required_artifact_flags"]["lab_scheduler_simulation_allowed"] is True
    assert plan["required_artifact_flags"]["mainline_activation_enabled"] is False
    assert plan["required_artifact_flags"]["production_notification_delivery_allowed"] is False
    assert plan["required_artifact_flags"]["production_db_migration_allowed"] is False
    assert plan["proactive_ladder"]["autonomy_tier_order"] == [
        "observe_only",
        "draft",
        "suggest",
        "ask_to_approve",
        "lab_chat_deliver_with_controls",
    ]
    assert len(plan["pr_train"]) == plan["planned_pr_count"]


def _recommendation_train() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_pr_train",
        "status": "completed",
        "planned_pr_count": 24,
        "dynamic_remaining_pr_count": 0,
        "last_completed_pr_number": 24,
        "active_pr_number": None,
        "next_capability_plan": {
            "primary_next_train": "advanced_product_lab_proactive_chat_first_integration",
            "dependencies_confirmed": {
                "memory": "completed",
                "context_engineering": "completed",
                "rescue_phase1": "completed",
                "recommendation": "completed",
            },
        },
    }


def _proactive_golden_set() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_proactive_golden_set",
        "status": "active_alignment_contract",
        "suite_contract": {
            "required_case_types": [
                "wake_trigger",
                "deterministic_gate",
                "llm_send_skip",
                "quiet_hours",
                "cooldown",
                "dismiss_snooze_reopen_modify",
                "chat_first_delivery",
                "stay_silent",
                "permission_posture",
                "copy_safety",
                "feedback_suppression",
                "scheduler_activation_wall",
                "live_send_skip_seed",
                "live_feedback_seed",
            ]
        },
    }
