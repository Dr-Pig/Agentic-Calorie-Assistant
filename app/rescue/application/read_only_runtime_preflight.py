from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.read_only_runtime_preflight"
)

MEMORY_STAGE_DECISION = "runtime_lab_memory_stage_promotion_decision"
RESCUE_CONTEXT = "rescue_shadow_summary_context_projection"
NO_COMMIT_VIABILITY = "rescue_no_commit_viability_shadow_packet"
REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface", "run_id")
MEMORY_DEPENDENCY = "long_term_memory.read_only_runtime"
MEMORY_STAGE_NO_GO_FLAGS = (
    "mainline_runtime_connected",
    "manager_context_packet_changed",
    "manager_context_injected",
    "durable_product_memory_written",
    "user_facing_behavior_changed",
    "canonical_mutation_changed",
    "mutation_changed",
    "runtime_effect_allowed",
    "recommendation_served",
    "rescue_proposal_committed",
    "proactive_sent",
    "scheduler_enabled",
)
RESCUE_FALSE_FLAGS = (
    "runtime_effect_allowed",
    "rescue_proposal_committed",
    "rescue_committed",
    "proposal_committed",
    "ledger_entry_created",
    "day_budget_mutated",
    "body_plan_mutated",
    "meal_thread_mutated",
    "durable_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
    "user_facing_behavior_changed",
    "canonical_mutation_changed",
    "proactive_sent",
    "recommendation_served",
    "scheduler_enabled",
)
NON_CLAIMS = [
    "not_rescue_stage_promotion_decision",
    "not_rescue_proposal",
    "not_rescue_commit",
    "not_budget_or_ledger_mutation",
    "not_mainline_runtime_activation",
    "not_manager_context_packet_change",
    "not_scheduler_or_notification_delivery",
]


def build_rescue_read_only_runtime_preflight_report(
    *,
    memory_stage_promotion_decision: Mapping[str, Any],
    rescue_context_projection: Mapping[str, Any],
    no_commit_viability_packet: Mapping[str, Any],
) -> dict[str, Any]:
    memory_decision = _mapping(memory_stage_promotion_decision)
    context = _mapping(rescue_context_projection)
    viability = _mapping(no_commit_viability_packet)
    blockers = [
        *_memory_stage_blockers(memory_decision),
        *_context_blockers(context),
        *_viability_blockers(viability),
    ]
    status = "pass" if not blockers else "blocked"
    report = {
        "artifact_type": "rescue_read_only_runtime_preflight_report",
        "status": status,
        "blockers": blockers,
        "capability": "rescue",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "dependency_satisfied": MEMORY_DEPENDENCY if status == "pass" else None,
        "source_stage_promotion_artifact_type": memory_decision.get("artifact_type"),
        "source_stage_promotion_fixture_kind": memory_decision.get("fixture_kind"),
        "source_rescue_context_artifact_type": context.get("artifact_type"),
        "source_no_commit_viability_artifact_type": viability.get("artifact_type"),
        "manual_promotion_review_allowed": status == "pass",
        "automatic_stage_promotion_allowed": False,
        "rescue_read_only_runtime_promoted": False,
        "preflight_only": True,
        "real_artifact_input_required": True,
        "artifact_classification": "manual_promotion",
        "required_merge_check": False,
        "owner": "app/rescue",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
        "evidence": _evidence(memory_decision, context, viability, blockers),
        "non_claims": list(NON_CLAIMS),
    }
    report.update({flag: False for flag in RESCUE_FALSE_FLAGS})
    return report


def _memory_stage_blockers(decision: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if decision.get("artifact_type") != MEMORY_STAGE_DECISION:
        blockers.append("memory_stage_promotion.unsupported_artifact_type")
    if decision.get("status") != "approved":
        blockers.append("memory_stage_promotion.status_not_approved")
    if decision.get("capability") != "long_term_memory":
        blockers.append("memory_stage_promotion.capability_not_long_term_memory")
    if decision.get("activation_stage_after_decision") != "read_only_runtime":
        blockers.append("memory_stage_promotion.activation_stage_not_read_only_runtime")
    if decision.get("manual_promotion_approved") is not True:
        blockers.append("memory_stage_promotion.manual_promotion_not_approved")
    if decision.get("stage_change_recorded") is not True:
        blockers.append("memory_stage_promotion.stage_change_not_recorded")
    if decision.get("automatic_stage_promotion_allowed") is True:
        blockers.append("memory_stage_promotion.automatic_promotion_allowed")
    for key in REQUIRED_SCOPE_KEYS:
        if not _mapping(decision.get("scope_keys")).get(key):
            blockers.append(f"memory_stage_promotion.scope_keys_missing:{key}")
    for flag in MEMORY_STAGE_NO_GO_FLAGS:
        if decision.get(flag) is True:
            blockers.append(f"memory_stage_promotion.{flag}")
    for flag, value in _mapping(decision.get("no_go_flags")).items():
        if value is True:
            blockers.append(f"memory_stage_promotion.no_go_flag_true:{flag}")
    return blockers


def _context_blockers(context: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if context.get("artifact_type") != RESCUE_CONTEXT:
        blockers.append("rescue_context_projection.unsupported_artifact_type")
    if context.get("status") != "pass":
        blockers.append("rescue_context_projection.status_not_pass")
    if context.get("memory_summary_projection_used") is not True:
        blockers.append("rescue_context_projection.memory_summary_not_used")
    for blocker in _string_list(context.get("blockers")):
        blockers.append(f"rescue_context_projection.existing_blocker:{blocker}")
    blockers.extend(_true_flag_blockers("rescue_context_projection", context))
    return blockers


def _viability_blockers(viability: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if viability.get("artifact_type") != NO_COMMIT_VIABILITY:
        blockers.append("no_commit_viability_packet.unsupported_artifact_type")
    if viability.get("status") != "pass":
        blockers.append("no_commit_viability_packet.status_not_pass")
    if viability.get("rescue_context_projection_used") is not True:
        blockers.append("no_commit_viability_packet.context_not_used")
    if viability.get("recovery_viability") not in {"viable", "strained"}:
        blockers.append("no_commit_viability_packet.not_viable_for_preflight")
    if viability.get("proposal_card") is not None:
        blockers.append("no_commit_viability_packet.proposal_card_present")
    if viability.get("candidate_copy") is not None:
        blockers.append("no_commit_viability_packet.candidate_copy_present")
    if viability.get("send_or_skip") is not None:
        blockers.append("no_commit_viability_packet.send_or_skip_present")
    if viability.get("primary_actions") not in (None, []):
        blockers.append("no_commit_viability_packet.primary_actions_present")
    for blocker in _string_list(viability.get("blockers")):
        blockers.append(f"no_commit_viability_packet.existing_blocker:{blocker}")
    blockers.extend(_true_flag_blockers("no_commit_viability_packet", viability))
    return blockers


def _true_flag_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [
        f"{prefix}.{flag}"
        for flag in RESCUE_FALSE_FLAGS
        if artifact.get(flag) is True
    ]


def _evidence(
    decision: Mapping[str, Any],
    context: Mapping[str, Any],
    viability: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "memory_dependency_artifact_type": decision.get("artifact_type"),
        "memory_dependency_stage": decision.get("activation_stage_after_decision"),
        "rescue_context_artifact_type": context.get("artifact_type"),
        "no_commit_viability_artifact_type": viability.get("artifact_type"),
        "recovery_viability": viability.get("recovery_viability"),
        "preflight_blocker_count": len(blockers),
    }


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
