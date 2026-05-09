from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "runtime.application.proactive_read_only_runtime_preflight"
)

CAPABILITY = "proactive"
CURRENT_STAGE = "shadow"
TARGET_STAGE = "read_only_runtime"
REC_STAGE = "recommendation_read_only_runtime_stage_decision"
RESCUE_STAGE = "rescue_read_only_runtime_stage_decision"
NO_SEND_PACK = "proactive_no_send_decision_pack"
EXPECTED_PACK_BLOCKERS = {
    "human_review_required_before_live_delivery",
    "live_scheduler_not_enabled",
    "no_send_shadow_only",
}
REC_FLAGS = (
    "recommendation_served",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "manager_context_packet_changed",
    "manager_context_injected",
    "mutation_changed",
    "durable_memory_written",
    "proactive_sent",
    "scheduler_enabled",
)
RESCUE_FLAGS = (
    "rescue_proposal_committed",
    "rescue_committed",
    "proposal_committed",
    "ledger_entry_created",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "manager_context_packet_changed",
    "manager_context_injected",
    "mutation_changed",
    "durable_memory_written",
    "proactive_sent",
    "scheduler_enabled",
)
OUTPUT_FALSE_FLAGS = (
    "runtime_effect_allowed",
    "real_runtime_effect",
    "proactive_sent",
    "scheduler_enabled",
    "live_delivery_allowed",
    "scheduler_activation_allowed",
    "manager_context_packet_changed",
    "manager_context_injected",
    "recommendation_served",
    "rescue_committed",
    "proposal_committed",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "mutation_changed",
    "user_facing_behavior_changed",
    "product_readiness_claimed",
)
NON_CLAIMS = [
    "not_proactive_stage_promotion_decision",
    "not_scheduler_activation",
    "not_live_delivery",
    "not_notification_delivery",
    "not_user_facing_proactive",
    "not_runtime_mutation",
    "not_manager_context_packet_change",
]


def build_proactive_read_only_runtime_preflight_report(
    *,
    recommendation_stage_decision: Mapping[str, Any],
    rescue_stage_decision: Mapping[str, Any],
    no_send_decision_pack: Mapping[str, Any],
) -> dict[str, Any]:
    recommendation = _mapping(recommendation_stage_decision)
    rescue = _mapping(rescue_stage_decision)
    pack = _mapping(no_send_decision_pack)
    blockers = [
        *_stage_blockers(
            "recommendation_stage",
            recommendation,
            REC_STAGE,
            "recommendation",
            REC_FLAGS,
            "recommendation_read_only_runtime_promoted",
        ),
        *_stage_blockers(
            "rescue_stage",
            rescue,
            RESCUE_STAGE,
            "rescue",
            RESCUE_FLAGS,
            "rescue_read_only_runtime_promoted",
        ),
        *_pack_blockers(pack),
    ]
    status = "pass" if not blockers else "blocked"
    return {
        "artifact_type": "proactive_read_only_runtime_preflight_report",
        "status": status,
        "blockers": blockers,
        "capability": CAPABILITY,
        "current_stage": CURRENT_STAGE,
        "target_stage": TARGET_STAGE,
        "dependency_satisfied": [
            "recommendation.read_only_runtime",
            "rescue.read_only_runtime",
        ]
        if status == "pass"
        else [],
        "source_recommendation_stage_artifact_type": recommendation.get("artifact_type"),
        "source_rescue_stage_artifact_type": rescue.get("artifact_type"),
        "source_no_send_decision_pack_artifact_type": pack.get("artifact_type"),
        "manual_promotion_review_allowed": status == "pass",
        "automatic_stage_promotion_allowed": False,
        "proactive_read_only_runtime_promoted": False,
        "preflight_only": True,
        "real_artifact_input_required": True,
        "artifact_classification": "manual_promotion",
        "required_merge_check": False,
        "owner": "app/runtime",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_proactive_scheduler_runtime_activation_plan",
        "no_go_flags": {flag: False for flag in OUTPUT_FALSE_FLAGS},
        "non_claims": list(NON_CLAIMS),
        **dict.fromkeys(OUTPUT_FALSE_FLAGS, False),
    }


def _stage_blockers(
    prefix: str,
    artifact: Mapping[str, Any],
    expected_type: str,
    expected_capability: str,
    false_flags: tuple[str, ...],
    promoted_flag: str,
) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != expected_type:
        blockers.append(f"{prefix}.unsupported_artifact_type")
    if artifact.get("status") != "approved":
        blockers.append(f"{prefix}.status_not_approved")
    if artifact.get("capability") != expected_capability:
        blockers.append(f"{prefix}.capability_mismatch")
    if artifact.get("activation_stage_after_decision") != TARGET_STAGE:
        blockers.append(f"{prefix}.activation_stage_not_read_only_runtime")
    if artifact.get("manual_promotion_approved") is not True:
        blockers.append(f"{prefix}.manual_promotion_not_approved")
    if artifact.get("stage_change_recorded") is not True:
        blockers.append(f"{prefix}.stage_change_not_recorded")
    if artifact.get("automatic_stage_promotion_allowed") is True:
        blockers.append(f"{prefix}.automatic_promotion_allowed")
    if artifact.get(promoted_flag) is not True:
        blockers.append(f"{prefix}.read_only_runtime_not_promoted")
    for blocker in _string_list(artifact.get("blockers")):
        blockers.append(f"{prefix}.{blocker}")
    for flag in false_flags:
        if artifact.get(flag) is True:
            blockers.append(f"{prefix}.{flag}")
    for flag, value in _mapping(artifact.get("no_go_flags")).items():
        if value is True:
            blockers.append(f"{prefix}.no_go_flag_true:{flag}")
    return blockers


def _pack_blockers(pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pack.get("artifact_type") != NO_SEND_PACK:
        blockers.append("no_send_decision_pack.unsupported_artifact_type")
    if pack.get("shadow_mode") is not True:
        blockers.append("no_send_decision_pack.shadow_mode_not_true")
    for flag in ("live_delivery_allowed", "scheduler_activation_allowed", "promotion_allowed"):
        if pack.get(flag) is True:
            blockers.append(f"no_send_decision_pack.{flag}")
    integrity = _mapping(pack.get("input_integrity"))
    if integrity.get("passed") is not True:
        blockers.append("no_send_decision_pack.input_integrity_failed")
    for blocker in _string_list(integrity.get("blockers")):
        blockers.append(f"no_send_decision_pack.{blocker}")
    summary = _mapping(pack.get("summary"))
    if int(summary.get("clean_run_count") or 0) < 3:
        blockers.append("no_send_decision_pack.minimum_clean_shadow_runs_not_met")
    if int(summary.get("copy_suppressed_count") or 0) > 0:
        blockers.append("no_send_decision_pack.copy_review_issues_present")
    gate = _mapping(pack.get("promotion_gate"))
    if gate.get("repeated_clean_shadow_evidence") is not True:
        blockers.append("no_send_decision_pack.repeated_clean_shadow_evidence_missing")
    unexpected = set(_string_list(gate.get("promotion_blockers"))) - EXPECTED_PACK_BLOCKERS
    for blocker in sorted(unexpected):
        blockers.append(f"no_send_decision_pack.{blocker}")
    guardrails = _mapping(pack.get("activation_guardrails"))
    for flag, value in guardrails.items():
        if value is True:
            blockers.append(f"no_send_decision_pack.activation_guardrail:{flag}")
    return blockers


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
