from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.recommendation_train_closeout import (
    build_recommendation_train_closeout,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_recommendation_pr_train.yaml"


def test_recommendation_train_closeout_passes_after_dormancy_gate() -> None:
    closeout = build_recommendation_train_closeout(
        pr_train=_closed_train(),
        quality_decision_pack=_quality_pack(),
        dormancy_gate=_dormancy_gate(),
    )

    assert closeout["artifact_type"] == "advanced_product_lab_recommendation_train_closeout"
    assert closeout["status"] == "pass"
    assert closeout["recommendation_train_closed"] is True
    assert closeout["completed_pr_count"] == 24
    assert closeout["dynamic_estimate"] == {
        "remaining_pr_count_after_pr24_merge": 0,
        "estimate_may_change_after_real_dogfood": True,
        "real_dogfood_traces_available": False,
    }
    assert closeout["ready_for_next_capability_planning"] is True
    assert closeout["next_capability_plan"]["primary_next_train"] == (
        "advanced_product_lab_proactive_chat_first_integration"
    )
    assert closeout["next_capability_plan"]["first_slice"] == (
        "proactive_entry_contract_from_memory_rescue_recommendation_outputs"
    )
    assert closeout["next_capability_plan"]["estimated_pr_range"] == {
        "optimistic": 18,
        "likely": 24,
        "conservative": 30,
    }
    assert closeout["ready_for_mainline_activation"] is False
    assert closeout["mainline_activation_enabled"] is False
    assert closeout["mainline_runtime_connected"] is False
    assert closeout["generic_workflow_engine_required"] is False
    assert closeout["blockers"] == []


def test_recommendation_train_closeout_blocks_unclosed_train_or_gate_failure() -> None:
    unclosed_train = {**_closed_train(), "last_completed_pr_number": 23}
    gate = {**_dormancy_gate(), "status": "blocked"}

    closeout = build_recommendation_train_closeout(
        pr_train=unclosed_train,
        quality_decision_pack={**_quality_pack(), "status": "blocked"},
        dormancy_gate=gate,
    )

    assert closeout["status"] == "blocked"
    assert closeout["recommendation_train_closed"] is False
    assert closeout["ready_for_next_capability_planning"] is False
    assert closeout["blockers"] == [
        "pr_train.last_completed_pr_number_not_24",
        "quality_decision_pack.status_not_pass",
        "dormancy_gate.status_not_pass",
    ]


def test_recommendation_train_file_records_pr24_closeout_and_next_capability() -> None:
    plan = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))

    assert plan["status"] == "completed"
    assert plan["planned_pr_count"] == 24
    assert plan["dynamic_remaining_pr_count"] == 0
    assert plan["last_completed_pr_number"] == 24
    assert plan["active_pr_number"] is None
    assert plan["next_capability_plan"]["primary_next_train"] == (
        "advanced_product_lab_proactive_chat_first_integration"
    )
    assert plan["next_capability_plan"]["dependencies_confirmed"] == {
        "memory": "completed",
        "context_engineering": "completed",
        "rescue_phase1": "completed",
        "recommendation": "completed",
    }
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 24,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_train_closeout_and_next_capability_plan_completed_locally",
    }


def _closed_train() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_pr_train",
        "status": "completed",
        "planned_pr_count": 24,
        "dynamic_remaining_pr_count": 0,
        "last_completed_pr_number": 24,
        "active_pr_number": None,
    }


def _quality_pack() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_quality_decision_pack",
        "status": "pass",
        "ready_for_recommendation_mainline_dormancy_gate": True,
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "blockers": [],
    }


def _dormancy_gate() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_mainline_dormancy_gate",
        "status": "pass",
        "ready_for_recommendation_train_closeout": True,
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "blockers": [],
    }
