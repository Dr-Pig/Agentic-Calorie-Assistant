from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.proactive_train_closeout import (
    build_proactive_train_closeout,
)


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_proactive_chat_first_pr_train.yaml"


def test_proactive_train_closeout_passes_after_live_e2e_and_dormancy_gate() -> None:
    closeout = build_proactive_train_closeout(
        pr_train=_closed_train(),
        live_diagnostic=_live_diagnostic(),
        paired_comparison=_paired_comparison(),
        recommendation_e2e=_recommendation_e2e(),
        rescue_e2e=_rescue_e2e(),
        latency_report=_latency_report(),
        dormancy_gate=_dormancy_gate(),
    )

    assert closeout["artifact_type"] == "advanced_product_lab_proactive_train_closeout"
    assert closeout["status"] == "pass"
    assert closeout["proactive_train_closed"] is True
    assert closeout["completed_pr_count"] == 24
    assert closeout["dynamic_estimate"] == {
        "remaining_pr_count_after_pr24_merge": 0,
        "estimate_may_change_after_real_dogfood": True,
        "real_dogfood_traces_available": False,
    }
    assert closeout["quality_evidence_summary"] == {
        "fixture_and_holdout_evidence": "pass",
        "recommendation_feedback_e2e": "pass",
        "rescue_suppression_e2e": "pass",
        "paired_shadow_comparison": "pass",
        "grokfast_live_feedback_diagnostic": "pass",
        "latency_cost_omission_trace": "pass",
        "mainline_dormancy_gate": "pass",
    }
    assert closeout["next_capability_plan"]["primary_next_train"] == (
        "advanced_product_lab_real_dogfood_and_activation_calibration"
    )
    assert closeout["ready_for_mainline_activation"] is False
    assert closeout["mainline_activation_enabled"] is False
    assert closeout["blockers"] == []


def test_proactive_train_closeout_blocks_missing_live_or_dormancy_evidence() -> None:
    closeout = build_proactive_train_closeout(
        pr_train={**_closed_train(), "dynamic_remaining_pr_count": 1},
        live_diagnostic={**_live_diagnostic(), "status": "blocked"},
        paired_comparison=_paired_comparison(),
        recommendation_e2e=_recommendation_e2e(),
        rescue_e2e=_rescue_e2e(),
        latency_report=_latency_report(),
        dormancy_gate={**_dormancy_gate(), "status": "blocked"},
    )

    assert closeout["status"] == "blocked"
    assert closeout["proactive_train_closed"] is False
    assert closeout["blockers"] == [
        "pr_train.dynamic_remaining_pr_count_not_0",
        "live_diagnostic.status_not_pass",
        "dormancy_gate.status_not_pass",
    ]


def test_proactive_train_file_records_pr24_closeout_and_next_capability() -> None:
    plan = yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))

    assert plan["status"] == "completed"
    assert plan["planned_pr_count"] == 24
    assert plan["dynamic_remaining_pr_count"] == 0
    assert plan["last_completed_pr_number"] == 24
    assert plan["active_pr_number"] is None
    assert plan["next_capability_plan"]["primary_next_train"] == (
        "advanced_product_lab_real_dogfood_and_activation_calibration"
    )
    assert plan["next_capability_plan"]["dependencies_confirmed"] == {
        "memory": "completed",
        "context_engineering": "completed",
        "rescue_phase1": "completed",
        "recommendation": "completed",
        "proactive": "completed",
    }
    assert plan["last_merge_evidence"]["completed_prs"][-1] == {
        "pr_number": 24,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "proactive_train_closeout_and_next_capability_plan_completed_locally",
        "dynamic_remaining_pr_count_after": 0,
    }


def _closed_train() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_proactive_chat_first_pr_train",
        "status": "completed",
        "planned_pr_count": 24,
        "dynamic_remaining_pr_count": 0,
        "last_completed_pr_number": 24,
        "active_pr_number": None,
    }


def _live_diagnostic() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_proactive_feedback_live_diagnostic",
        "status": "pass",
        "live_grokfast_diagnostic_pass": True,
        "mainline_activation_enabled": False,
    }


def _paired_comparison() -> dict[str, object]:
    return {"artifact_type": "advanced_product_lab_paired_shadow_comparison", "status": "pass"}


def _recommendation_e2e() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_proactive_feedback_e2e_report",
        "status": "pass",
    }


def _rescue_e2e() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_rescue_proactive_suppression_e2e_report",
        "status": "pass",
    }


def _latency_report() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_proactive_latency_cost_omission_report",
        "status": "pass",
    }


def _dormancy_gate() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_proactive_mainline_dormancy_gate",
        "status": "pass",
        "ready_for_proactive_train_closeout": True,
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
    }
