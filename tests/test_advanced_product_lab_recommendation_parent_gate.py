from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.recommendation_parent_entry_gate import (
    build_recommendation_parent_entry_gate,
)


ROOT = Path(__file__).resolve().parents[1]
TRAIN_PATH = ROOT / "docs" / "quality" / "advanced_product_lab_recommendation_pr_train.yaml"


def test_recommendation_parent_gate_allows_pr2_only_from_shared_manager_entry() -> None:
    artifact = build_recommendation_parent_entry_gate(
        recommendation_train=_train(active_pr_number=1),
        context_train=_context_train(),
        entry_contract=_entry_contract(),
    )

    assert artifact["artifact_type"] == "advanced_product_lab_recommendation_parent_entry_gate"
    assert artifact["status"] == "pass"
    assert artifact["completed_pr_number"] == 1
    assert artifact["next_active_pr_number"] == 2
    assert artifact["dynamic_remaining_after_pr1"] == 23
    assert artifact["manager_tool_entry"]["tool_name"] == "recommendation.run"
    assert artifact["manager_tool_entry"]["runtime_surface"] == "manager_tool_loop"
    assert artifact["recommendation_graph"]["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["served_to_mainline_user"] is False
    assert artifact["blockers"] == []


def test_recommendation_parent_gate_blocks_parallel_recommendation_entry() -> None:
    entry_contract = _entry_contract()
    entry_contract["manager_tool_entry"] = {
        "tool_name": "recommendation.run",
        "capability_id": "recommendation",
        "tool_mode": "candidate_context",
        "runtime_surface": "parallel_lab_orchestrator",
        "parallel_orchestration_allowed": True,
    }

    artifact = build_recommendation_parent_entry_gate(
        recommendation_train=_train(active_pr_number=1),
        context_train=_context_train(),
        entry_contract=entry_contract,
    )

    assert artifact["status"] == "blocked"
    assert artifact["blockers"] == [
        "manager_tool_entry.runtime_surface_not_manager_tool_loop",
        "manager_tool_entry.parallel_orchestration_allowed",
    ]


def test_recommendation_parent_gate_accepts_train_after_pr1_progression() -> None:
    train = _train(active_pr_number=2)
    train["last_completed_pr_number"] = 1
    train["dynamic_remaining_pr_count"] = 23

    artifact = build_recommendation_parent_entry_gate(
        recommendation_train=train,
        context_train=_context_train(),
        entry_contract=_entry_contract(),
    )

    assert artifact["status"] == "pass"
    assert artifact["next_active_pr_number"] == 2


def test_recommendation_train_records_pr1_completion_and_next_active_slice() -> None:
    plan = yaml.safe_load(TRAIN_PATH.read_text(encoding="utf-8-sig"))

    assert plan["planned_pr_count"] == 24
    assert plan["dynamic_remaining_pr_count"] <= 23
    assert plan["last_completed_pr_number"] >= 1
    assert plan["active_pr_number"] >= 2
    assert plan["last_merge_evidence"]["completed_prs"][0] == {
        "pr_number": 1,
        "pull_request": "local_logical_slice",
        "merge_commit": "working_branch_uncommitted",
        "result": "recommendation_parent_entry_and_gate_alignment_completed_locally",
        "gate_artifact": "artifacts/advanced_product_lab_recommendation_parent_entry_gate_pr1.json",
    }
    assert plan["pr_train"][1]["slice_id"] == "recommendation_tool_argument_contract"
    assert "After PR1 logical completion, remaining estimate moved to 23." in plan[
        "estimate_notes"
    ]


def _train(*, active_pr_number: int) -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_pr_train",
        "planned_pr_count": 24,
        "dynamic_remaining_pr_count": 24,
        "last_completed_pr_number": 0,
        "active_pr_number": active_pr_number,
        "manager_tool_entry": _manager_tool_entry(),
        "recommendation_graph": _recommendation_graph(),
        "required_artifact_flags": {
            "mainline_activation_enabled": False,
            "served_to_mainline_user": False,
            "canonical_product_mutation_allowed": False,
        },
    }


def _context_train() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_context_engineering_pr_train",
        "status": "complete",
        "planned_pr_count": 29,
        "dynamic_remaining_pr_count": 0,
        "last_completed_pr_number": 29,
        "active_pr_number": None,
    }


def _entry_contract() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_recommendation_entry_contract",
        "status": "pass",
        "ready_for_recommendation_train": True,
        "mainline_activation_enabled": False,
        "served_to_mainline_user": False,
        "manager_tool_entry": _manager_tool_entry(),
        "recommendation_graph": _recommendation_graph(),
        "blockers": [],
    }


def _manager_tool_entry() -> dict[str, object]:
    return {
        "tool_name": "recommendation.run",
        "capability_id": "recommendation",
        "tool_mode": "candidate_context",
        "runtime_surface": "manager_tool_loop",
        "parallel_orchestration_allowed": False,
    }


def _recommendation_graph() -> dict[str, object]:
    return {
        "physical_node_order": [
            "recommendation_planning",
            "candidate_retrieval_guard_scoring",
            "offer_synthesis",
        ],
        "logical_stage_boundaries": [
            "recommendation_context_result",
            "candidate_spec",
            "candidate_retrieval_guard_scoring",
            "ranking_result",
            "recommendation_response_result",
        ],
        "legacy_five_node_runner_is_canonical": False,
    }
