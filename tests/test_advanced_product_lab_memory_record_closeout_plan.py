from __future__ import annotations

from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "docs" / "quality" / "advanced_product_lab_memory_record_closeout_plan.yaml"
GOLDEN_SET = ROOT / "docs" / "quality" / "runtime_lab_memory_edd_golden_set.yaml"


def test_memory_record_closeout_plan_records_completed_lab_chain() -> None:
    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8-sig"))

    assert plan["artifact_type"] == "advanced_product_lab_memory_record_closeout_plan"
    assert plan["status"] == "active_closeout"
    assert plan["train_closed_for_simulated_lab"] is True
    assert plan["mainline_activation_enabled"] is False
    assert plan["self_use_v1_affected"] is False
    assert plan["required_final_runner"] == (
        "scripts/run_advanced_product_lab_memory_record_closure_pipeline.py"
    )
    assert plan["completion_evidence"] == [
        "advanced_product_lab_memory_record_closure_pack",
        "advanced_product_lab_activation_wall_audit",
        "advanced_product_lab_live_edd_decision_pack",
        "runtime_lab_closure_alignment",
    ]
    assert plan["remaining_before_real_user_activation"] == [
        "real_dogfood_trace_calibration",
        "optional_env_gated_grokfast_live_diagnostic",
        "explicit_activation_pr_with_rollback",
    ]


def test_memory_record_closeout_plan_keeps_legacy_lab_memory_paths_bounded() -> None:
    plan = yaml.safe_load(PLAN.read_text(encoding="utf-8-sig"))
    legacy = plan["legacy_lab_memory_path_policy"]

    assert legacy["delete_now"] is False
    assert legacy["primary_runtime_lab_path"] == "MemoryRecord"
    assert legacy["legacy_paths"] == [
        "app/advanced_shadow_lab/product_lab_memory.py",
        "app/advanced_shadow_lab/product_lab_memory_context.py",
        "app/advanced_shadow_lab/product_lab_memory_tools.py",
    ]
    assert legacy["retirement_trigger"] == "approved_memory_record_only_activation_plan"
    assert legacy["must_not_block_mainline_dormancy"] is True


def test_golden_set_next_slice_points_to_real_dogfood_after_closeout() -> None:
    golden = yaml.safe_load(GOLDEN_SET.read_text(encoding="utf-8-sig"))

    assert golden["version"] == 1.3
    assert golden["runtime_lab_closure_alignment"]["next_required_slice"] == (
        "real_dogfood_trace_calibration_when_available"
    )
