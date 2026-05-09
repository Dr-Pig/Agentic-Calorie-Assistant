from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "rescue.application.read_only_stage_promotion"
)

CAPABILITY = "rescue"
CURRENT_STAGE = "shadow"
TARGET_STAGE = "read_only_runtime"
PREFLIGHT_ARTIFACT = "rescue_read_only_runtime_preflight_report"
REVIEW_ARTIFACT = "rescue_read_only_runtime_stage_review_decision"
MEMORY_DEPENDENCY = "long_term_memory.read_only_runtime"
REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface", "run_id")
PREFLIGHT_NO_GO_FLAGS = (
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
REVIEW_NO_GO_FLAGS = (
    "mainline_runtime_activation_approved", "rescue_serving_approved",
    "rescue_proposal_approved", "rescue_commit_approved",
    "scheduler_delivery_approved", "manager_context_packet_change_approved",
    "route_or_api_activation_approved", "downstream_activation_approved",
    "mutation_approved",
)
FALSE_FLAGS = {
    **dict.fromkeys(
        (
            *PREFLIGHT_NO_GO_FLAGS,
            "mainline_runtime_connected",
            "durable_product_memory_written",
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
    "not_rescue_serving", "not_rescue_proposal_creation",
    "not_rescue_commit", "not_budget_or_ledger_mutation",
    "not_mainline_runtime_activation", "not_route_or_api_activation",
    "not_manager_context_packet_change", "not_scheduler_or_notification_delivery",
    "not_recommendation_read_only_runtime_promotion",
    "not_proactive_read_only_runtime_promotion",
]


def build_rescue_read_only_stage_promotion_decision(
    *,
    rescue_preflight_report: Mapping[str, Any],
    human_review_decision: Mapping[str, Any] | None,
) -> dict[str, Any]:
    report = _mapping(rescue_preflight_report)
    review = _mapping(human_review_decision)
    blockers = [*_preflight_blockers(report), *_review_blockers(human_review_decision)]
    status = _status(blockers, human_review_decision)
    return {
        "artifact_type": "rescue_read_only_runtime_stage_decision",
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
        "rescue_read_only_runtime_promoted": status == "approved",
        "human_review_required": True,
        "human_review_decision": _review_summary(review),
        "automatic_stage_promotion_allowed": False,
        "source_preflight_artifact_type": report.get("artifact_type"),
        "source_preflight_status": report.get("status"),
        "source_review_fixture_kind": review.get("fixture_kind"),
        "scope_keys": _scope_keys(review),
        "owner": "app/rescue",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_rescue_runtime_activation_plan",
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


def _preflight_blockers(report: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if report.get("artifact_type") != PREFLIGHT_ARTIFACT:
        blockers.append("rescue_preflight.unsupported_artifact_type")
    if report.get("status") != "pass":
        blockers.append("rescue_preflight.status_not_pass")
    if report.get("capability") != CAPABILITY:
        blockers.append("rescue_preflight.capability_mismatch")
    if report.get("current_stage") != CURRENT_STAGE:
        blockers.append("rescue_preflight.current_stage_mismatch")
    if report.get("target_stage") != TARGET_STAGE:
        blockers.append("rescue_preflight.target_stage_mismatch")
    if report.get("dependency_satisfied") != MEMORY_DEPENDENCY:
        blockers.append("rescue_preflight.memory_dependency_not_satisfied")
    if report.get("manual_promotion_review_allowed") is not True:
        blockers.append("rescue_preflight.manual_review_not_allowed")
    if report.get("automatic_stage_promotion_allowed") is True:
        blockers.append("rescue_preflight.automatic_promotion_allowed")
    if report.get("rescue_read_only_runtime_promoted") is True:
        blockers.append("rescue_preflight.already_promoted")
    if report.get("preflight_only") is not True:
        blockers.append("rescue_preflight.preflight_only_not_true")
    if report.get("real_artifact_input_required") is not True:
        blockers.append("rescue_preflight.real_artifact_input_not_required")
    for blocker in _string_list(report.get("blockers")):
        blockers.append(f"rescue_preflight.{blocker}")
    for flag in PREFLIGHT_NO_GO_FLAGS:
        if report.get(flag) is True:
            blockers.append(f"rescue_preflight.{flag}")
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
    scope = _mapping(review.get("scope_keys"))
    for key in REQUIRED_SCOPE_KEYS:
        if not scope.get(key):
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
