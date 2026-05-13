from __future__ import annotations

from typing import Any, Mapping


EXPECTED_TOOL_ENTRY = {
    "tool_name": "recommendation.run",
    "capability_id": "recommendation",
    "tool_mode": "candidate_context",
    "runtime_surface": "manager_tool_loop",
    "parallel_orchestration_allowed": False,
}
EXPECTED_PHYSICAL_NODE_ORDER = [
    "recommendation_planning",
    "candidate_retrieval_guard_scoring",
    "offer_synthesis",
]


def build_recommendation_parent_entry_gate(
    *,
    recommendation_train: Mapping[str, Any],
    context_train: Mapping[str, Any],
    entry_contract: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *_recommendation_train_blockers(recommendation_train),
        *_context_train_blockers(context_train),
        *_entry_contract_blockers(entry_contract),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_recommendation_parent_entry_gate",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/recommendation_parent_entry_gate.py",
        "consumer": "advanced_product_lab_recommendation_pr_train",
        "completed_pr_number": 1,
        "completed_slice_id": "recommendation_parent_entry_and_gate_alignment",
        "next_active_pr_number": 2 if status == "pass" else None,
        "dynamic_remaining_after_pr1": 23 if status == "pass" else 24,
        "manager_tool_entry": dict(_mapping(entry_contract.get("manager_tool_entry"))),
        "recommendation_graph": dict(_mapping(entry_contract.get("recommendation_graph"))),
        "mainline_activation_enabled": False,
        "served_to_mainline_user": False,
        "canonical_product_mutation_allowed": False,
        "blockers": blockers,
    }


def _recommendation_train_blockers(recommendation_train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if recommendation_train.get("artifact_type") != "advanced_product_lab_recommendation_pr_train":
        blockers.append("recommendation_train.unsupported_artifact_type")
    if int(recommendation_train.get("planned_pr_count") or 0) != 24:
        blockers.append("recommendation_train.planned_pr_count_not_24")
    progress = (
        int(recommendation_train.get("last_completed_pr_number") or 0),
        int(recommendation_train.get("active_pr_number") or 0),
    )
    if progress not in {(0, 1), (1, 2)}:
        blockers.append("recommendation_train.not_at_pr1_entry_or_pr1_complete")
    return blockers


def _context_train_blockers(context_train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if context_train.get("artifact_type") != "advanced_product_lab_context_engineering_pr_train":
        blockers.append("context_train.unsupported_artifact_type")
    if context_train.get("status") != "complete":
        blockers.append("context_train.status_not_complete")
    if _int_or_none(context_train.get("dynamic_remaining_pr_count")) != 0:
        blockers.append("context_train.remaining_not_zero")
    if int(context_train.get("last_completed_pr_number") or 0) != 29:
        blockers.append("context_train.pr29_not_complete")
    return blockers


def _entry_contract_blockers(entry_contract: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if entry_contract.get("artifact_type") != "advanced_product_lab_recommendation_entry_contract":
        blockers.append("entry_contract.unsupported_artifact_type")
    if entry_contract.get("status") != "pass":
        blockers.append("entry_contract.status_not_pass")
    if entry_contract.get("ready_for_recommendation_train") is not True:
        blockers.append("entry_contract.not_ready_for_recommendation_train")
    blockers.extend(_tool_entry_blockers(_mapping(entry_contract.get("manager_tool_entry"))))
    blockers.extend(_graph_blockers(_mapping(entry_contract.get("recommendation_graph"))))
    if entry_contract.get("mainline_activation_enabled") is True:
        blockers.append("entry_contract.mainline_activation_enabled")
    if entry_contract.get("served_to_mainline_user") is True:
        blockers.append("entry_contract.served_to_mainline_user")
    return blockers


def _tool_entry_blockers(tool_entry: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    for key, expected in EXPECTED_TOOL_ENTRY.items():
        if tool_entry.get(key) != expected:
            if expected is False:
                blockers.append(f"manager_tool_entry.{key}")
            else:
                blockers.append(f"manager_tool_entry.{key}_not_{expected}")
    return blockers


def _graph_blockers(graph: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if graph.get("physical_node_order") != EXPECTED_PHYSICAL_NODE_ORDER:
        blockers.append("recommendation_graph.physical_node_order_mismatch")
    if graph.get("legacy_five_node_runner_is_canonical") is not False:
        blockers.append("recommendation_graph.legacy_five_node_runner_is_canonical")
    return blockers


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


__all__ = ["build_recommendation_parent_entry_gate"]
