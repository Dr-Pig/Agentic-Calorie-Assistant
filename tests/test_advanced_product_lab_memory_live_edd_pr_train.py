from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_memory_live_edd_pr_train.yaml"


def _plan() -> dict:
    return yaml.safe_load(PLAN_PATH.read_text(encoding="utf-8-sig"))


def test_memory_live_edd_pr_train_records_fourteen_right_sized_prs() -> None:
    plan = _plan()

    assert plan["artifact_type"] == "advanced_product_lab_memory_live_edd_pr_train"
    assert plan["status"] == "active"
    assert plan["planned_pr_count"] == 14
    assert plan["dynamic_remaining_pr_count"] == 8
    assert plan["last_completed_pr_number"] == 6

    prs = plan["pr_train"]
    assert len(prs) == 14
    assert [item["pr_number"] for item in prs] == list(range(1, 15))
    assert prs[0]["slice_id"] == "sync_advanced_lab_with_main_memory_closeout"
    assert prs[-1]["slice_id"] == "live_edd_decision_pack_and_activation_wall_regression"


def test_memory_live_edd_pr_train_keeps_lab_live_from_mainline_activation() -> None:
    plan = _plan()

    assert plan["branch_strategy"]["target_branch"] == "codex/advanced-product-lab"
    assert plan["branch_strategy"]["mainline_activation_enabled"] is False
    assert plan["branch_strategy"]["self_use_v1_affected"] is False
    assert plan["branch_strategy"]["live_grokfast_diagnostics_allowed"] is True
    assert plan["branch_strategy"]["kimi_live_calls_allowed"] is False

    required_flags = plan["required_artifact_flags"]
    assert required_flags["lab_enabled"] is True
    assert required_flags["mainline_activation_enabled"] is False
    assert required_flags["durable_product_memory_written"] is False
    assert required_flags["canonical_product_mutation_allowed"] is False


def test_memory_live_edd_pr_train_names_required_live_milestones() -> None:
    plan = _plan()

    milestone_ids = {milestone["milestone_id"] for milestone in plan["live_edd_milestones"]}
    assert milestone_ids == {
        "grokfast_extraction_diagnostic",
        "memory_tool_lookup_diagnostic",
        "recommendation_with_blockers",
        "rescue_memory_context_diagnostic",
        "proactive_feedback_projection",
        "integrated_e2e_lab_loop",
        "failure_taxonomy_and_decision_pack",
    }
    assert all(
        milestone["provider_profile"] == "builderspace-grok-4-fast"
        for milestone in plan["live_edd_milestones"]
    )
    assert all(milestone["blocks_completion"] is True for milestone in plan["live_edd_milestones"])


def test_memory_live_edd_pr_train_dynamic_estimate_protocol_is_explicit() -> None:
    plan = _plan()

    protocol = plan["dynamic_estimate_protocol"]
    assert protocol["update_after_each_merge"] is True
    assert protocol["estimate_may_increase"] is True
    assert protocol["estimate_may_decrease"] is True
    assert protocol["do_not_use_chat_memory_as_only_plan"] is True
    assert (
        "docs/quality/advanced_product_lab_memory_live_edd_pr_train.yaml"
        in protocol["persistent_truth_files"]
    )
