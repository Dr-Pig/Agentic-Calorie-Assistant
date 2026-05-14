from __future__ import annotations

from typing import Any, Mapping


PLANNED_PR_COUNT = 24
REQUIRED_PROACTIVE_CASE_TYPES = {
    "wake_trigger",
    "deterministic_gate",
    "llm_send_skip",
    "quiet_hours",
    "cooldown",
    "dismiss_snooze_reopen_modify",
    "chat_first_delivery",
    "stay_silent",
    "permission_posture",
    "copy_safety",
    "feedback_suppression",
    "scheduler_activation_wall",
    "live_send_skip_seed",
    "live_feedback_seed",
}


def build_proactive_entry_contract(
    *,
    recommendation_train: Mapping[str, Any],
    proactive_golden_set: Mapping[str, Any],
) -> dict[str, Any]:
    blockers = [
        *_recommendation_train_blockers(recommendation_train),
        *_proactive_golden_set_blockers(proactive_golden_set),
    ]
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_proactive_entry_contract",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/proactive_entry_contract.py",
        "consumer": "advanced_product_lab_proactive_chat_first_pr_train",
        "readiness_scope": "proactive_train_entry_only",
        "ready_for_proactive_train": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "lab_chat_delivery_allowed": True,
        "lab_scheduler_simulation_allowed": True,
        "production_notification_delivery_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        "parent_recommendation_train": {
            "path": "docs/quality/advanced_product_lab_recommendation_pr_train.yaml",
            "closed_by_pr": 24,
            "decision_pack_required": True,
        },
        "wake_to_delivery_ladder": [
            "deterministic_trigger_gate",
            "contextual_send_skip_decision",
            "lab_chat_first_delivery",
            "control_feedback_projection",
        ],
        "autonomy_tier": {
            "starts_at": "observe_only",
            "maximum_without_explicit_user_action": "lab_chat_deliver_with_controls",
            "production_push_allowed": False,
        },
        "control_path_required": {
            "dismiss": True,
            "snooze": True,
            "reopen_or_modify": True,
            "next_signal_required": True,
            "user_facing_undo_label_allowed": False,
        },
        "dependency_status": {
            "memory": "completed",
            "context_engineering": "completed",
            "rescue_phase1": "completed",
            "recommendation": "completed",
        },
        "next_train": {
            "path": "docs/quality/advanced_product_lab_proactive_chat_first_pr_train.yaml",
            "planned_pr_count": PLANNED_PR_COUNT,
            "dynamic_remaining_pr_count": PLANNED_PR_COUNT - 1,
            "active_pr_number": 2,
        },
        "blockers": blockers,
    }


def _recommendation_train_blockers(train: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if train.get("artifact_type") != "advanced_product_lab_recommendation_pr_train":
        blockers.append("recommendation_train.unsupported_artifact_type")
    if train.get("status") != "completed":
        blockers.append("recommendation_train.status_not_completed")
    if _int(train.get("last_completed_pr_number")) != 24:
        blockers.append("recommendation_train.last_completed_pr_number_not_24")
    if _int(train.get("dynamic_remaining_pr_count")) != 0:
        blockers.append("recommendation_train.dynamic_remaining_pr_count_not_0")
    next_plan = train.get("next_capability_plan")
    if isinstance(next_plan, Mapping) and (
        next_plan.get("primary_next_train") != "advanced_product_lab_proactive_chat_first_integration"
    ):
        blockers.append("recommendation_train.next_capability_not_proactive")
    return blockers


def _proactive_golden_set_blockers(golden_set: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if golden_set.get("artifact_type") != "advanced_product_lab_proactive_golden_set":
        blockers.append("proactive_golden_set.unsupported_artifact_type")
    if golden_set.get("status") != "active_alignment_contract":
        blockers.append("proactive_golden_set.status_not_active_alignment_contract")
    suite_contract = golden_set.get("suite_contract")
    required_case_types = set()
    if isinstance(suite_contract, Mapping):
        required_case_types = {str(item) for item in suite_contract.get("required_case_types") or []}
    missing = sorted(REQUIRED_PROACTIVE_CASE_TYPES - required_case_types)
    if missing:
        blockers.append("proactive_golden_set.missing_case_types:" + ",".join(missing))
    return blockers


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


__all__ = [
    "PLANNED_PR_COUNT",
    "REQUIRED_PROACTIVE_CASE_TYPES",
    "build_proactive_entry_contract",
]
