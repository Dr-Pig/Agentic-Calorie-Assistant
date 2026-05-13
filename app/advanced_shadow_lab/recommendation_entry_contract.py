from __future__ import annotations

from typing import Any, Mapping


PHYSICAL_NODE_ORDER = [
    "recommendation_planning",
    "candidate_retrieval_guard_scoring",
    "offer_synthesis",
]
LOGICAL_STAGE_BOUNDARIES = [
    "recommendation_context_result",
    "candidate_spec",
    "candidate_retrieval_guard_scoring",
    "ranking_result",
    "recommendation_response_result",
]
NEXT_TRAIN_PLANNED_PR_COUNT = 24


def build_recommendation_entry_contract(
    *,
    context_train: Mapping[str, Any],
    context_decision_pack: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *_context_train_blockers(context_train),
        *_context_decision_pack_blockers(context_decision_pack),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_recommendation_entry_contract",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/recommendation_entry_contract.py",
        "consumer": "advanced_product_lab_recommendation_pr_train",
        "readiness_scope": "recommendation_train_entry_only",
        "ready_for_recommendation_train": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "parent_context_engineering_train": {
            "path": "docs/quality/advanced_product_lab_context_engineering_pr_train.yaml",
            "closed_by_pr": 29,
            "decision_pack_required": True,
        },
        "manager_tool_entry": {
            "tool_name": "recommendation.run",
            "capability_id": "recommendation",
            "tool_mode": "candidate_context",
            "runtime_surface": "manager_tool_loop",
            "parallel_orchestration_allowed": False,
        },
        "recommendation_graph": {
            "physical_node_order": list(PHYSICAL_NODE_ORDER),
            "logical_stage_boundaries": list(LOGICAL_STAGE_BOUNDARIES),
            "ownership_boundaries": [
                "llm_planning_to_deterministic_guard",
                "deterministic_guard_to_llm_offer_synthesis",
            ],
            "legacy_five_node_runner_is_canonical": False,
            "generic_workflow_engine_required": False,
        },
        "next_train": {
            "path": "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
            "planned_pr_count": NEXT_TRAIN_PLANNED_PR_COUNT,
            "dynamic_remaining_pr_count": NEXT_TRAIN_PLANNED_PR_COUNT,
            "active_pr_number": 1,
        },
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "production_scheduler_delivery_allowed": False,
        "served_to_mainline_user": False,
        "blockers": blockers,
    }


def _context_train_blockers(context_train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if context_train.get("artifact_type") != "advanced_product_lab_context_engineering_pr_train":
        blockers.append("context_train.unsupported_artifact_type")
    if int(context_train.get("planned_pr_count") or 0) != 29:
        blockers.append("context_train.planned_pr_count_not_29")
    if int(context_train.get("last_completed_pr_number") or 0) not in {28, 29}:
        blockers.append("context_train.pr28_not_completed")
    active_pr = context_train.get("active_pr_number")
    if active_pr not in {29, None}:
        blockers.append("context_train.active_pr_not_pr29_or_closed")
    return blockers


def _context_decision_pack_blockers(context_decision_pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if context_decision_pack.get("artifact_type") != (
        "advanced_product_lab_context_engineering_decision_pack"
    ):
        blockers.append("context_decision_pack.unsupported_artifact_type")
    if context_decision_pack.get("status") != "pass":
        blockers.append("context_decision_pack.status_not_pass")
    if context_decision_pack.get("ready_for_recommendation_entry_contract") is not True:
        blockers.append("context_decision_pack.not_ready_for_recommendation_entry_contract")
    if context_decision_pack.get("mainline_activation_enabled") is True:
        blockers.append("context_decision_pack.mainline_activation_enabled")
    live_summary = context_decision_pack.get("live_grokfast_summary")
    if isinstance(live_summary, Mapping) and (
        live_summary.get("live_grokfast_diagnostic_pass") is not True
    ):
        blockers.append("context_decision_pack.live_grokfast_not_passed")
    return blockers


__all__ = [
    "LOGICAL_STAGE_BOUNDARIES",
    "NEXT_TRAIN_PLANNED_PR_COUNT",
    "PHYSICAL_NODE_ORDER",
    "build_recommendation_entry_contract",
]
