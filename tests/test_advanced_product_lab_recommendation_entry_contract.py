from __future__ import annotations

from pathlib import Path

import yaml

from app.advanced_shadow_lab.recommendation_entry_contract import (
    build_recommendation_entry_contract,
)


ROOT = Path(__file__).resolve().parents[1]
NEXT_TRAIN_PATH = (
    ROOT / "docs" / "quality" / "advanced_product_lab_recommendation_pr_train.yaml"
)


def test_recommendation_entry_contract_opens_manager_tool_train_only_after_context_pack() -> None:
    artifact = build_recommendation_entry_contract(
        context_train=_context_train(),
        context_decision_pack=_decision_pack(),
    )

    assert artifact["artifact_type"] == "advanced_product_lab_recommendation_entry_contract"
    assert artifact["status"] == "pass"
    assert artifact["ready_for_recommendation_train"] is True
    assert artifact["ready_for_mainline_activation"] is False
    assert artifact["mainline_activation_enabled"] is False
    assert artifact["self_use_v1_affected"] is False
    assert artifact["parent_context_engineering_train"]["closed_by_pr"] == 29
    assert artifact["manager_tool_entry"] == {
        "tool_name": "recommendation.run",
        "capability_id": "recommendation",
        "tool_mode": "candidate_context",
        "runtime_surface": "manager_tool_loop",
        "parallel_orchestration_allowed": False,
    }
    assert artifact["recommendation_graph"]["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert artifact["recommendation_graph"]["logical_stage_boundaries"] == [
        "recommendation_context_result",
        "candidate_spec",
        "candidate_retrieval_guard_scoring",
        "ranking_result",
        "recommendation_response_result",
    ]
    assert artifact["recommendation_graph"]["legacy_five_node_runner_is_canonical"] is False
    assert artifact["next_train"]["planned_pr_count"] >= 20
    assert artifact["blockers"] == []


def test_recommendation_entry_contract_blocks_when_context_decision_pack_is_not_ready() -> None:
    artifact = build_recommendation_entry_contract(
        context_train=_context_train(),
        context_decision_pack=_decision_pack(status="blocked", ready=False),
    )

    assert artifact["status"] == "blocked"
    assert artifact["ready_for_recommendation_train"] is False
    assert artifact["blockers"] == [
        "context_decision_pack.status_not_pass",
        "context_decision_pack.not_ready_for_recommendation_entry_contract",
    ]


def test_recommendation_next_train_is_machine_readable_and_manager_style() -> None:
    plan = yaml.safe_load(NEXT_TRAIN_PATH.read_text(encoding="utf-8-sig"))

    assert plan["artifact_type"] == "advanced_product_lab_recommendation_pr_train"
    assert plan["status"] in {"active", "completed"}
    assert plan["current_mainline"] == "advanced_product_lab_recommendation_manager_tool_train"
    assert plan["planned_pr_count"] >= 20
    assert plan["dynamic_remaining_pr_count"] <= plan["planned_pr_count"]
    assert plan["active_pr_number"] is None or plan["active_pr_number"] >= 1
    assert plan["parent_context_engineering_train"] == {
        "path": "docs/quality/advanced_product_lab_context_engineering_pr_train.yaml",
        "closed_by_pr": 29,
        "entry_contract_artifact": (
            "artifacts/advanced_product_lab_recommendation_entry_contract_pr29.json"
        ),
    }
    assert plan["manager_tool_entry"]["tool_name"] == "recommendation.run"
    assert plan["manager_tool_entry"]["runtime_surface"] == "manager_tool_loop"
    assert plan["recommendation_graph"]["physical_node_order"] == [
        "recommendation_planning",
        "candidate_retrieval_guard_scoring",
        "offer_synthesis",
    ]
    assert plan["recommendation_graph"]["legacy_five_node_runner_is_canonical"] is False
    assert plan["required_artifact_flags"]["mainline_activation_enabled"] is False
    assert plan["required_artifact_flags"]["recommendation_served_to_lab"] is True
    assert plan["required_artifact_flags"]["served_to_mainline_user"] is False
    assert len(plan["pr_train"]) == plan["planned_pr_count"]


def _context_train() -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_context_engineering_pr_train",
        "status": "active",
        "planned_pr_count": 29,
        "dynamic_remaining_pr_count": 1,
        "last_completed_pr_number": 28,
        "active_pr_number": 29,
    }


def _decision_pack(*, status: str = "pass", ready: bool = True) -> dict[str, object]:
    return {
        "artifact_type": "advanced_product_lab_context_engineering_decision_pack",
        "status": status,
        "ready_for_recommendation_entry_contract": ready,
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "comparison": {
            "manager_tool_order": ["memory.search", "reusable_meal.search", "rescue.run"],
        },
        "live_grokfast_summary": {"live_grokfast_diagnostic_pass": True},
        "blockers": [] if status == "pass" else ["fixture_blocker"],
    }
