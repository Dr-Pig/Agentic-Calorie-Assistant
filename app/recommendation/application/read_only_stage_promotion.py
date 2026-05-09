from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "recommendation.application.read_only_stage_promotion"
)

CAPABILITY = "recommendation"
CURRENT_STAGE = "shadow"
TARGET_STAGE = "read_only_runtime"
PREFLIGHT_REPORT = "recommendation_shadow_summary_consumer_quality_report"
PREFLIGHT_ARTIFACT = "recommendation_read_only_runtime_preflight"
REVIEW_ARTIFACT = "recommendation_read_only_runtime_stage_review_decision"
MEMORY_DEPENDENCY = "long_term_memory.read_only_runtime"
REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface", "run_id")
PREFLIGHT_NO_GO_FLAGS = (
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
REVIEW_NO_GO_FLAGS = (
    "mainline_runtime_activation_approved", "recommendation_serving_approved",
    "live_search_approved", "ranking_llm_approved",
    "live_search_or_ranking_llm_approved", "intake_handoff_approved",
    "manager_context_packet_change_approved", "scheduler_delivery_approved",
    "route_or_api_activation_approved", "downstream_activation_approved",
    "mutation_approved",
)
FALSE_FLAGS = {
    **dict.fromkeys(
        (
            *PREFLIGHT_NO_GO_FLAGS,
            "mainline_runtime_connected",
            "user_facing_behavior_changed",
            "canonical_mutation_changed",
            "durable_product_memory_written",
            "scheduler_enabled",
            "notification_delivery_allowed",
            "route_or_api_activation_allowed",
            "production_db_migration_allowed",
            "product_readiness_claimed",
        ),
        False,
    ),
    "lab_isolated": True,
}
NON_CLAIMS = [
    "not_recommendation_serving", "not_mainline_runtime_activation",
    "not_route_or_api_activation", "not_live_search_or_ranking_llm",
    "not_intake_handoff", "not_manager_context_packet_change",
    "not_scheduler_or_notification_delivery", "not_canonical_mutation_authority",
    "not_rescue_read_only_runtime_promotion",
    "not_proactive_read_only_runtime_promotion",
]


def build_recommendation_read_only_stage_promotion_decision(
    *,
    recommendation_preflight_report: Mapping[str, Any],
    human_review_decision: Mapping[str, Any] | None,
) -> dict[str, Any]:
    report = _mapping(recommendation_preflight_report)
    preflight = _mapping(report.get("read_only_runtime_preflight"))
    review = _mapping(human_review_decision)
    blockers = [
        *_preflight_blockers(report, preflight),
        *_review_blockers(human_review_decision),
    ]
    status = _status(blockers, human_review_decision)
    return {
        "artifact_type": "recommendation_read_only_runtime_stage_decision",
        "status": status,
        "blockers": blockers,
        "capability": CAPABILITY,
        "current_stage": CURRENT_STAGE,
        "target_stage": TARGET_STAGE,
        "activation_stage_after_decision": TARGET_STAGE
        if status == "approved"
        else CURRENT_STAGE,
        "stage_change_recorded": status == "approved",
        "manual_promotion_approved": status == "approved",
        "recommendation_read_only_runtime_promoted": status == "approved",
        "human_review_required": True,
        "human_review_decision": _review_summary(review),
        "automatic_stage_promotion_allowed": False,
        "source_report_artifact_type": report.get("artifact_type"),
        "source_preflight_artifact_type": preflight.get("artifact_type"),
        "source_preflight_status": preflight.get("status"),
        "source_review_fixture_kind": review.get("fixture_kind"),
        "scope_keys": _scope_keys(review),
        "owner": "app/recommendation",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_recommendation_runtime_activation_plan",
        "artifact_classification": "manual_promotion",
        "required_merge_check": False,
        "real_artifact_input_required": True,
        "no_go_flags": {flag: False for flag in PREFLIGHT_NO_GO_FLAGS},
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _status(blockers: list[str], review: Mapping[str, Any] | None) -> str:
    if not blockers:
        return "approved"
    if review is None and blockers == ["human_review_decision_missing"]:
        return "pending_review"
    return "blocked"


def _preflight_blockers(
    report: Mapping[str, Any],
    preflight: Mapping[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != PREFLIGHT_REPORT:
        blockers.append("recommendation_preflight.report.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("recommendation_preflight.report.status_not_pass")
    if preflight.get("artifact_type") != PREFLIGHT_ARTIFACT:
        blockers.append("recommendation_preflight.unsupported_artifact_type")
    if preflight.get("status") != "pass":
        blockers.append("recommendation_preflight.status_not_pass")
    if preflight.get("capability") != CAPABILITY:
        blockers.append("recommendation_preflight.capability_mismatch")
    if preflight.get("current_stage") != CURRENT_STAGE:
        blockers.append("recommendation_preflight.current_stage_mismatch")
    if preflight.get("target_stage") != TARGET_STAGE:
        blockers.append("recommendation_preflight.target_stage_mismatch")
    if preflight.get("dependency_satisfied") != MEMORY_DEPENDENCY:
        blockers.append("recommendation_preflight.memory_dependency_not_satisfied")
    if preflight.get("manual_promotion_review_allowed") is not True:
        blockers.append("recommendation_preflight.manual_review_not_allowed")
    if preflight.get("automatic_stage_promotion_allowed") is True:
        blockers.append("recommendation_preflight.automatic_promotion_allowed")
    if preflight.get("recommendation_read_only_runtime_promoted") is True:
        blockers.append("recommendation_preflight.already_promoted")
    if preflight.get("preflight_only") is not True:
        blockers.append("recommendation_preflight.preflight_only_not_true")
    if preflight.get("real_artifact_input_required") is not True:
        blockers.append("recommendation_preflight.real_artifact_input_not_required")
    for blocker in _string_list(report.get("blockers")):
        blockers.append(f"recommendation_preflight.report.{blocker}")
    for blocker in _string_list(preflight.get("blockers")):
        blockers.append(f"recommendation_preflight.{blocker}")
    for flag in PREFLIGHT_NO_GO_FLAGS:
        if report.get(flag) is True:
            blockers.append(f"recommendation_preflight.report.{flag}")
        if preflight.get(flag) is True:
            blockers.append(f"recommendation_preflight.{flag}")
    return blockers


def _review_blockers(review_value: Mapping[str, Any] | None) -> list[str]:
    if review_value is None:
        return ["human_review_decision_missing"]
    review = _mapping(review_value)
    blockers: list[str] = []
    if review.get("artifact_type") != REVIEW_ARTIFACT:
        blockers.append("human_review_decision.unsupported_artifact_type")
    if review.get("decision") != "approved":
        blockers.append("human_review_decision.decision_not_approved")
    if review.get("capability") != CAPABILITY:
        blockers.append("human_review_decision.capability_mismatch")
    if review.get("current_stage") != CURRENT_STAGE:
        blockers.append("human_review_decision.current_stage_mismatch")
    if review.get("target_stage") != TARGET_STAGE:
        blockers.append("human_review_decision.target_stage_mismatch")
    if review.get("reviewed_read_only_runtime_preflight") is not True:
        blockers.append("human_review_decision.preflight_not_reviewed")
    for key in REQUIRED_SCOPE_KEYS:
        if not _mapping(review.get("scope_keys")).get(key):
            blockers.append(f"human_review_decision.scope_keys_missing:{key}")
    for flag in REVIEW_NO_GO_FLAGS:
        if review.get(flag) is True:
            blockers.append(f"human_review_decision.{flag}")
    return blockers


def _review_summary(review: Mapping[str, Any]) -> dict[str, Any]:
    if not review:
        return {}
    return {
        "artifact_type": review.get("artifact_type"),
        "decision": review.get("decision"),
        "reviewer_id": review.get("reviewer_id"),
        "reviewed_at": review.get("reviewed_at"),
        "reviewed_read_only_runtime_preflight": review.get(
            "reviewed_read_only_runtime_preflight"
        ) is True,
    }


def _scope_keys(review: Mapping[str, Any]) -> dict[str, str]:
    scope = _mapping(review.get("scope_keys"))
    return {key: str(scope[key]) for key in REQUIRED_SCOPE_KEYS if scope.get(key)}


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
