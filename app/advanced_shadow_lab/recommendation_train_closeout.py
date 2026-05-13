from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


PLANNED_PR_COUNT = 24
ARTIFACT_TYPE = "advanced_product_lab_recommendation_train_closeout"


def build_recommendation_train_closeout(
    *,
    pr_train: Mapping[str, Any],
    quality_decision_pack: Mapping[str, Any],
    dormancy_gate: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *_pr_train_blockers(pr_train),
        *_quality_pack_blockers(quality_decision_pack),
        *_dormancy_gate_blockers(dormancy_gate),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/recommendation_train_closeout.py",
        "consumer": "advanced_product_lab_followup_planning",
        "completed_pr_count": _int(pr_train.get("last_completed_pr_number")),
        "planned_pr_count": _int(pr_train.get("planned_pr_count")),
        "recommendation_train_closed": status == "pass",
        "dynamic_estimate": {
            "remaining_pr_count_after_pr24_merge": 0 if status == "pass" else (
                _int(pr_train.get("dynamic_remaining_pr_count"))
            ),
            "estimate_may_change_after_real_dogfood": True,
            "real_dogfood_traces_available": False,
        },
        "manager_tool_entry": {
            "tool_name": "recommendation.run",
            "capability_id": "recommendation",
            "runtime_surface": "manager_tool_loop",
        },
        "recommendation_graph": {
            "physical_node_order": [
                "recommendation_planning",
                "candidate_retrieval_guard_scoring",
                "offer_synthesis",
            ],
            "legacy_five_node_runner_is_canonical": False,
        },
        "next_capability_plan": _next_capability_plan(),
        "ready_for_next_capability_planning": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "generic_workflow_engine_required": False,
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


def _pr_train_blockers(pr_train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pr_train.get("artifact_type") != "advanced_product_lab_recommendation_pr_train":
        blockers.append("pr_train.unsupported_artifact_type")
    if pr_train.get("status") != "completed":
        blockers.append("pr_train.status_not_completed")
    if _int(pr_train.get("planned_pr_count")) != PLANNED_PR_COUNT:
        blockers.append("pr_train.planned_pr_count_not_24")
    if _int(pr_train.get("last_completed_pr_number")) != PLANNED_PR_COUNT:
        blockers.append("pr_train.last_completed_pr_number_not_24")
    if _int(pr_train.get("dynamic_remaining_pr_count")) != 0:
        blockers.append("pr_train.dynamic_remaining_pr_count_not_0")
    if pr_train.get("active_pr_number") is not None:
        blockers.append("pr_train.active_pr_number_not_null")
    return blockers


def _quality_pack_blockers(pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pack.get("artifact_type") != (
        "advanced_product_lab_recommendation_quality_decision_pack"
    ):
        blockers.append("quality_decision_pack.unsupported_artifact_type")
    if pack.get("status") != "pass":
        blockers.append("quality_decision_pack.status_not_pass")
    if pack.get("ready_for_mainline_activation") is True:
        blockers.append("quality_decision_pack.ready_for_mainline_activation")
    if pack.get("mainline_activation_enabled") is True:
        blockers.append("quality_decision_pack.mainline_activation_enabled")
    return blockers


def _dormancy_gate_blockers(gate: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if gate.get("artifact_type") != (
        "advanced_product_lab_recommendation_mainline_dormancy_gate"
    ):
        blockers.append("dormancy_gate.unsupported_artifact_type")
    if gate.get("status") != "pass":
        blockers.append("dormancy_gate.status_not_pass")
    if gate.get("ready_for_recommendation_train_closeout") is not True:
        blockers.append("dormancy_gate.not_ready_for_train_closeout")
    if gate.get("ready_for_mainline_activation") is True:
        blockers.append("dormancy_gate.ready_for_mainline_activation")
    if gate.get("mainline_activation_enabled") is True:
        blockers.append("dormancy_gate.mainline_activation_enabled")
    return blockers


def _next_capability_plan() -> dict[str, Any]:
    return {
        "primary_next_train": "advanced_product_lab_proactive_chat_first_integration",
        "first_slice": "proactive_entry_contract_from_memory_rescue_recommendation_outputs",
        "estimated_pr_range": {"optimistic": 18, "likely": 24, "conservative": 30},
        "why_next": (
            "Memory, rescue, context engineering, and recommendation now have manager-style "
            "lab evidence, so proactive can become the chat-first coordinator of those outputs."
        ),
        "dependencies_confirmed": {
            "memory": "completed",
            "context_engineering": "completed",
            "rescue_phase1": "completed",
            "recommendation": "completed",
        },
        "do_not_build_yet": [
            "mainline_route_mount",
            "production_notification_delivery",
            "production_db_migration",
            "generic_workflow_engine",
        ],
    }


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["build_recommendation_train_closeout"]
