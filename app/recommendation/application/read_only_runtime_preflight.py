from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.read_only_runtime_preflight"
)

SUMMARY_REPORT = "recommendation_shadow_summary_consumer_quality_report"
MEMORY_STAGE_DECISION = "runtime_lab_memory_stage_promotion_decision"
MEMORY_DEPENDENCY = "long_term_memory.read_only_runtime"
RECOMMENDATION_SOURCE_ARTIFACT = "recommendation_five_node_lab_runner_artifact"
REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface", "run_id")
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
RECOMMENDATION_NO_GO_FLAGS = (
    "runtime_connected",
    "recommendation_served",
    "proactive_sent",
    "live_search_used",
    "ranking_llm_invoked",
    "intake_handoff_created",
    "mutation_changed",
    "meal_thread_mutated",
    "day_budget_mutated",
    "body_plan_mutated",
    "durable_memory_written",
    "manager_context_packet_changed",
    "manager_context_injected",
)
NON_CLAIMS = [
    "not_recommendation_serving",
    "not_recommendation_stage_promotion_decision",
    "not_live_search_or_ranking_llm",
    "not_intake_handoff",
    "not_mainline_runtime_activation",
    "not_manager_context_packet_change",
    "not_scheduler_or_notification_delivery",
]


def build_recommendation_read_only_runtime_preflight_report(
    *,
    memory_stage_promotion_decision: Mapping[str, Any],
    recommendation_summary_report: Mapping[str, Any],
) -> dict[str, Any]:
    memory_decision = _mapping(memory_stage_promotion_decision)
    summary_report = dict(recommendation_summary_report)
    blockers = [
        *_memory_stage_blockers(memory_decision),
        *_recommendation_report_blockers(summary_report),
    ]
    preflight_status = "pass" if not blockers else "blocked"
    prefixed_blockers = [f"read_only_runtime_preflight.{item}" for item in blockers]
    result = {
        **summary_report,
        "status": "blocked"
        if prefixed_blockers or _string_list(summary_report.get("blockers"))
        else "pass",
        "blockers": [*_string_list(summary_report.get("blockers")), *prefixed_blockers],
        "read_only_runtime_preflight": {
            "artifact_type": "recommendation_read_only_runtime_preflight",
            "status": preflight_status,
            "blockers": blockers,
            "capability": "recommendation",
            "current_stage": "shadow",
            "target_stage": "read_only_runtime",
            "dependency_satisfied": MEMORY_DEPENDENCY if not blockers else None,
            "source_stage_promotion_artifact_type": memory_decision.get("artifact_type"),
            "source_stage_promotion_fixture_kind": memory_decision.get("fixture_kind"),
            "source_recommendation_artifact_type": summary_report.get(
                "source_recommendation_artifact_type"
            ),
            "manual_promotion_review_allowed": preflight_status == "pass",
            "automatic_stage_promotion_allowed": False,
            "recommendation_read_only_runtime_promoted": False,
            "preflight_only": True,
            "real_artifact_input_required": True,
            "artifact_classification": "manual_promotion",
            "required_merge_check": False,
            "owner": "app/recommendation",
            "consumer": "advanced_capability_activation_review",
            "retirement_trigger": "approved recommendation_runtime_activation_plan",
            "evidence": _evidence(memory_decision, summary_report, blockers),
            "non_claims": list(NON_CLAIMS),
        },
        "recommendation_read_only_runtime_promoted": False,
        "product_readiness_claimed": False,
    }
    for flag in RECOMMENDATION_NO_GO_FLAGS:
        result[flag] = False
    return result


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


def _recommendation_report_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != SUMMARY_REPORT:
        blockers.append("recommendation_summary_report.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("recommendation_summary_report.status_not_pass")
    if report.get("memory_summary_projection_used") is not True:
        blockers.append("recommendation_summary_report.memory_summary_not_used")
    if report.get("source_recommendation_artifact_type") != RECOMMENDATION_SOURCE_ARTIFACT:
        blockers.append("recommendation_summary_report.source_recommendation_missing")
    if int(report.get("candidate_count") or 0) <= 0:
        blockers.append("recommendation_summary_report.no_candidate_evidence")
    for blocker in _string_list(report.get("blockers")):
        blockers.append(f"recommendation_summary_report.existing_blocker:{blocker}")
    for flag in RECOMMENDATION_NO_GO_FLAGS:
        if report.get(flag) is True:
            blockers.append(f"recommendation_summary_report.{flag}")
    return blockers


def _evidence(
    decision: Mapping[str, Any],
    report: Mapping[str, Any],
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "memory_dependency_artifact_type": decision.get("artifact_type"),
        "memory_dependency_stage": decision.get("activation_stage_after_decision"),
        "recommendation_summary_artifact_type": report.get("artifact_type"),
        "candidate_count": int(report.get("candidate_count") or 0),
        "preflight_blocker_count": len(blockers),
        "no_runtime_effect": not any(
            report.get(flag) is True for flag in RECOMMENDATION_NO_GO_FLAGS
        ),
    }


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
