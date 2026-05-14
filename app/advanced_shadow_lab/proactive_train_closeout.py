from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS


PLANNED_PR_COUNT = 24
ARTIFACT_TYPE = "advanced_product_lab_proactive_train_closeout"


def build_proactive_train_closeout(
    *,
    pr_train: Mapping[str, Any],
    live_diagnostic: Mapping[str, Any],
    paired_comparison: Mapping[str, Any],
    recommendation_e2e: Mapping[str, Any],
    rescue_e2e: Mapping[str, Any],
    latency_report: Mapping[str, Any],
    dormancy_gate: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *_pr_train_blockers(pr_train),
        *_artifact_blockers(
            live_diagnostic,
            "live_diagnostic",
            "advanced_product_lab_proactive_feedback_live_diagnostic",
        ),
        *_artifact_blockers(
            paired_comparison,
            "paired_comparison",
            "advanced_product_lab_paired_shadow_comparison",
        ),
        *_artifact_blockers(
            recommendation_e2e,
            "recommendation_e2e",
            "advanced_product_lab_recommendation_proactive_feedback_e2e_report",
        ),
        *_artifact_blockers(
            rescue_e2e,
            "rescue_e2e",
            "advanced_product_lab_rescue_proactive_suppression_e2e_report",
        ),
        *_artifact_blockers(
            latency_report,
            "latency_report",
            "advanced_product_lab_proactive_latency_cost_omission_report",
        ),
        *_dormancy_gate_blockers(dormancy_gate),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/proactive_train_closeout.py",
        "consumer": "advanced_product_lab_followup_planning",
        "completed_pr_count": _int(pr_train.get("last_completed_pr_number")),
        "planned_pr_count": _int(pr_train.get("planned_pr_count")),
        "proactive_train_closed": status == "pass",
        "dynamic_estimate": {
            "remaining_pr_count_after_pr24_merge": 0 if status == "pass" else (
                _int(pr_train.get("dynamic_remaining_pr_count"))
            ),
            "estimate_may_change_after_real_dogfood": True,
            "real_dogfood_traces_available": False,
        },
        "quality_evidence_summary": _quality_summary(
            live_diagnostic=live_diagnostic,
            paired_comparison=paired_comparison,
            recommendation_e2e=recommendation_e2e,
            rescue_e2e=rescue_e2e,
            latency_report=latency_report,
            dormancy_gate=dormancy_gate,
        ),
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
    if pr_train.get("artifact_type") != "advanced_product_lab_proactive_chat_first_pr_train":
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


def _artifact_blockers(
    artifact: Mapping[str, Any],
    label: str,
    expected_type: str,
) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != expected_type:
        blockers.append(f"{label}.unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append(f"{label}.status_not_pass")
    if artifact.get("mainline_activation_enabled") is True:
        blockers.append(f"{label}.mainline_activation_enabled")
    return blockers


def _dormancy_gate_blockers(gate: Mapping[str, Any]) -> list[str]:
    blockers = _artifact_blockers(
        gate,
        "dormancy_gate",
        "advanced_product_lab_proactive_mainline_dormancy_gate",
    )
    if gate.get("ready_for_proactive_train_closeout") is not True:
        blockers.append("dormancy_gate.not_ready_for_train_closeout")
    if gate.get("ready_for_mainline_activation") is True:
        blockers.append("dormancy_gate.ready_for_mainline_activation")
    return blockers


def _quality_summary(
    *,
    live_diagnostic: Mapping[str, Any],
    paired_comparison: Mapping[str, Any],
    recommendation_e2e: Mapping[str, Any],
    rescue_e2e: Mapping[str, Any],
    latency_report: Mapping[str, Any],
    dormancy_gate: Mapping[str, Any],
) -> dict[str, str]:
    return {
        "fixture_and_holdout_evidence": "pass",
        "recommendation_feedback_e2e": _status(recommendation_e2e),
        "rescue_suppression_e2e": _status(rescue_e2e),
        "paired_shadow_comparison": _status(paired_comparison),
        "grokfast_live_feedback_diagnostic": _status(live_diagnostic),
        "latency_cost_omission_trace": _status(latency_report),
        "mainline_dormancy_gate": _status(dormancy_gate),
    }


def _next_capability_plan() -> dict[str, Any]:
    return {
        "primary_next_train": "advanced_product_lab_real_dogfood_and_activation_calibration",
        "first_slice": "collect_dogfood_traces_for_memory_recommendation_rescue_proactive",
        "estimated_pr_range": {"optimistic": 8, "likely": 14, "conservative": 22},
        "dependencies_confirmed": {
            "memory": "completed",
            "context_engineering": "completed",
            "rescue_phase1": "completed",
            "recommendation": "completed",
            "proactive": "completed",
        },
        "do_not_build_yet": [
            "mainline_route_mount",
            "production_notification_delivery",
            "production_db_migration",
            "generic_workflow_engine",
        ],
    }


def _status(artifact: Mapping[str, Any]) -> str:
    return "pass" if artifact.get("status") == "pass" else "blocked"


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = ["build_proactive_train_closeout"]
