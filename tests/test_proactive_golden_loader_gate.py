from __future__ import annotations

import yaml

from app.advanced_shadow_lab.proactive_golden_gate import (
    build_proactive_golden_gate_report,
)


def test_proactive_golden_gate_loads_cases_and_width_contract() -> None:
    report = build_proactive_golden_gate_report()

    assert report["artifact_type"] == "advanced_product_lab_proactive_golden_gate_report"
    assert report["status"] == "pass"
    assert report["case_count"] == 14
    assert report["split_counts"] == {
        "fixture": 8,
        "negative_holdout": 4,
        "live_diagnostic_seed": 2,
    }
    assert report["semantic_width"]["missing_required_axes"] == []
    assert report["raw_keyword_semantic_oracle_allowed"] is False
    assert report["runner_inferred_semantics_allowed"] is False
    assert report["ready_for_deterministic_trigger_gate_pr4"] is True
    assert report["blockers"] == []


def test_proactive_golden_gate_blocks_narrow_or_keyword_oracle_artifact() -> None:
    narrow_artifact = {
        "artifact_type": "advanced_product_lab_proactive_golden_set",
        "status": "active_alignment_contract",
        "mainline_activation_enabled": False,
        "raw_keyword_semantic_oracle_allowed": False,
        "case_schema": {"required_fields": ["case_id", "case_type"]},
        "suite_contract": {
            "required_case_types": ["wake_trigger"],
            "required_split_counts": {"fixture": 1},
            "semantic_contract_width": {
                "required_axes": ["positive_capability_path", "overtrigger_false_positive"],
                "axis_case_types": {"positive_capability_path": ["wake_trigger"]},
            },
        },
        "cases": [
            {
                "case_id": "too-narrow",
                "case_type": "wake_trigger",
                "split": "fixture",
                "oracle": {"semantic_oracle_source": "raw_keyword"},
                "mutation_posture": {},
            }
        ],
    }

    report = build_proactive_golden_gate_report(proactive_golden_set=narrow_artifact)

    assert report["status"] == "blocked"
    assert report["ready_for_deterministic_trigger_gate_pr4"] is False
    assert "semantic_contract_width.overtrigger_false_positive.missing_case_types" in report[
        "blockers"
    ]
    assert "too-narrow.oracle_not_product_trace" in report["blockers"]


def test_proactive_train_records_pr3_completion_and_next_active_slice() -> None:
    with open(
        "docs/quality/advanced_product_lab_proactive_chat_first_pr_train.yaml",
        encoding="utf-8-sig",
    ) as handle:
        plan = yaml.safe_load(handle)

    assert plan["dynamic_remaining_pr_count"] <= 21
    assert plan["last_completed_pr_number"] >= 3
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 4
    assert {
        "pr_number": 3,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "proactive_golden_set_loader_and_width_gate_completed_locally",
        "dynamic_remaining_pr_count_after": 21,
    } in plan["last_merge_evidence"]["completed_prs"]
