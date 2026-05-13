from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


EXPECTED_MANAGER_TOOL_ORDER = ["memory.search", "reusable_meal.search", "rescue.run"]


def build_context_engineering_decision_pack(
    *,
    pr_train: Mapping[str, Any],
    baseline_runtime_artifact: Mapping[str, Any],
    manager_runtime_artifact: Mapping[str, Any],
    live_grokfast_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    comparison = _comparison(
        baseline_runtime_artifact=baseline_runtime_artifact,
        manager_runtime_artifact=manager_runtime_artifact,
    )
    live_summary = _live_grokfast_summary(live_grokfast_artifact)
    blockers = [
        *_runtime_blockers("baseline_runtime", baseline_runtime_artifact),
        *_runtime_blockers("manager_runtime", manager_runtime_artifact),
        *_manager_path_blockers(manager_runtime_artifact),
        *_live_blockers(live_grokfast_artifact),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_context_engineering_decision_pack",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/context_engineering_decision_pack.py",
        "consumer": "advanced_product_lab_recommendation_entry_planning",
        "planned_pr_count": int(pr_train.get("planned_pr_count") or 0),
        "last_completed_pr_number": int(pr_train.get("last_completed_pr_number") or 0),
        "dynamic_remaining_pr_count_before_pack": int(
            pr_train.get("dynamic_remaining_pr_count") or 0
        ),
        "comparison": comparison,
        "live_grokfast_summary": live_summary,
        "readiness_scope": "recommendation_entry_contract_only",
        "ready_for_recommendation_entry_contract": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "production_scheduler_delivery_allowed": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _comparison(
    *,
    baseline_runtime_artifact: Mapping[str, Any],
    manager_runtime_artifact: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "baseline_runtime_passed": baseline_runtime_artifact.get("status") == "pass",
        "manager_runtime_passed": manager_runtime_artifact.get("status") == "pass",
        "baseline_manager_tool_loop_enabled": (
            baseline_runtime_artifact.get("manager_tool_loop_enabled") is True
        ),
        "manager_tool_loop_enabled": (
            manager_runtime_artifact.get("manager_tool_loop_enabled") is True
        ),
        "manager_tool_order": _tool_order(manager_runtime_artifact),
        "manager_memory_selected": bool(
            manager_runtime_artifact.get("manager_selected_memory_context_adapter")
        ),
        "manager_reusable_meal_selected": bool(
            manager_runtime_artifact.get("manager_selected_reusable_meal_artifact")
        ),
        "manager_rescue_selected": bool(
            manager_runtime_artifact.get("manager_selected_rescue_artifact")
        ),
        "lab_only_behavior_delta": "manager_tools_returned_context_without_mainline_activation",
    }


def _live_grokfast_summary(artifact: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_type": str(artifact.get("artifact_type") or ""),
        "status": str(artifact.get("status") or ""),
        "diagnostic_evidence_class": str(artifact.get("diagnostic_evidence_class") or ""),
        "live_invoked": artifact.get("live_invoked") is True,
        "provider_invoked": artifact.get("provider_invoked") is True,
        "live_provider_used": artifact.get("live_provider_used") is True,
        "live_grokfast_diagnostic_pass": artifact.get("live_grokfast_diagnostic_pass") is True,
        "source_manager_tool_order": [str(item) for item in artifact.get("source_manager_tool_order") or []],
    }


def _runtime_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    blockers = []
    if artifact.get("artifact_type") != "advanced_product_lab_turn_artifact":
        blockers.append(f"{prefix}.unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append(f"{prefix}.status_not_pass")
    for flag in (
        "mainline_runtime_connected",
        "canonical_product_mutation_allowed",
        "durable_product_memory_written",
        "manager_context_packet_changed",
    ):
        if artifact.get(flag) is True:
            blockers.append(f"{prefix}.{flag}")
    return blockers


def _manager_path_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = []
    if artifact.get("manager_tool_loop_enabled") is not True:
        blockers.append("manager_runtime.manager_tool_loop_not_enabled")
    if _tool_order(artifact) != EXPECTED_MANAGER_TOOL_ORDER:
        blockers.append("manager_runtime.tool_order_mismatch")
    for key in (
        "manager_selected_memory_context_adapter",
        "manager_selected_reusable_meal_artifact",
        "manager_selected_rescue_artifact",
    ):
        if not artifact.get(key):
            blockers.append(f"manager_runtime.{key}_missing")
    return blockers


def _live_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = []
    if artifact.get("artifact_type") != "advanced_product_lab_manager_turn_grokfast_diagnostic":
        blockers.append("live_grokfast.unsupported_artifact_type")
    if artifact.get("live_grokfast_diagnostic_pass") is not True:
        blockers.append("live_grokfast.not_passed")
    if [str(item) for item in artifact.get("source_manager_tool_order") or []] != EXPECTED_MANAGER_TOOL_ORDER:
        blockers.append("live_grokfast.tool_order_mismatch")
    return blockers


def _tool_order(artifact: Mapping[str, Any]) -> list[str]:
    return [
        str(ref).split(":")[-1]
        for ref in artifact.get("manager_tool_loop_source_refs") or []
    ]


__all__ = ["build_context_engineering_decision_pack"]
