from __future__ import annotations

from typing import Any, Mapping

from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_stage_promotion"
)

CAPABILITY = "long_term_memory"
CURRENT_STAGE = "shadow"
TARGET_STAGE = "read_only_runtime"
PACK_ARTIFACT = "runtime_lab_memory_read_only_runtime_lab_pack"
REVIEW_ARTIFACT = "runtime_lab_memory_stage_promotion_review_decision"
REQUIRED_SCOPE_KEYS = ("user_id", "workspace_id", "project_id", "surface", "run_id")
REQUIRED_STAGE_EVIDENCE = (
    "scope_isolation_check",
    "paired_baseline_comparison",
    "omission_trace_present",
    "latency_budget_observed",
    "no_commit_fallback",
)
PACK_NO_GO_FLAGS = (
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
REVIEW_NO_GO_FLAGS = (
    "mainline_runtime_activation_approved",
    "manager_context_packet_change_approved",
    "durable_memory_write_approved",
    "downstream_activation_approved",
)
FALSE_FLAGS = {
    **dict.fromkeys(
        (
            *PACK_NO_GO_FLAGS,
            "mainline_runtime_activation_approved",
            "notification_delivery_allowed",
            "production_db_migration_allowed",
            "route_or_api_activation_allowed",
        ),
        False,
    ),
    "runtime_connected": True,
    "lab_isolated": True,
}
NON_CLAIMS = [
    "not_mainline_runtime_activation",
    "not_manager_context_packet_memory_injection",
    "not_durable_product_memory_write",
    "not_user_facing_memory_activation",
    "not_canonical_mutation_authority",
    "not_recommendation_read_only_runtime_promotion",
    "not_rescue_read_only_runtime_promotion",
    "not_proactive_read_only_runtime_promotion",
]


def build_runtime_lab_memory_stage_promotion_decision(
    *,
    read_only_runtime_lab_pack: Mapping[str, Any],
    human_review_decision: Mapping[str, Any] | None,
) -> dict[str, Any]:
    pack = _mapping(read_only_runtime_lab_pack)
    review = _mapping(human_review_decision)
    pack_blockers = _pack_blockers(pack)
    review_blockers = _review_blockers(human_review_decision)
    blockers = [*pack_blockers, *review_blockers]
    status = _status(blockers, human_review_decision)
    return {
        "artifact_type": "runtime_lab_memory_stage_promotion_decision",
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
        "human_review_required": True,
        "human_review_decision": _review_summary(review),
        "automatic_stage_promotion_allowed": False,
        "source_read_only_runtime_pack_type": pack.get("artifact_type"),
        "source_artifacts": _string_list(pack.get("source_artifacts")),
        "source_pack_status": pack.get("status"),
        "scope_keys": _scope_keys(review),
        "owner": "MemoryRuntimeArchitecture",
        "consumer": "advanced_capability_activation_review",
        "retirement_trigger": "approved_product_runtime_activation_ledger_entries",
        "artifact_classification": "manual_promotion",
        "required_merge_check": False,
        "stage_evidence": {
            name: _mapping(pack.get("stage_evidence")).get(name) is True
            for name in REQUIRED_STAGE_EVIDENCE
        },
        "paired_baseline_evidence": dict(_mapping(pack.get("paired_baseline_evidence"))),
        "no_go_flags": {flag: False for flag in PACK_NO_GO_FLAGS},
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _status(blockers: list[str], review: Mapping[str, Any] | None) -> str:
    if not blockers:
        return "approved"
    if review is None and blockers == ["human_review_decision_missing"]:
        return "pending_review"
    return "blocked"


def _pack_blockers(pack: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if pack.get("artifact_type") != PACK_ARTIFACT:
        blockers.append("read_only_runtime_lab_pack.unsupported_artifact_type")
    if pack.get("status") != "pass":
        blockers.append("read_only_runtime_lab_pack.status_not_pass")
    if pack.get("capability") != CAPABILITY:
        blockers.append("read_only_runtime_lab_pack.capability_mismatch")
    if pack.get("current_stage") != CURRENT_STAGE:
        blockers.append("read_only_runtime_lab_pack.current_stage_mismatch")
    if pack.get("target_stage") != TARGET_STAGE:
        blockers.append("read_only_runtime_lab_pack.target_stage_mismatch")
    if pack.get("manual_promotion_review_allowed") is not True:
        blockers.append("read_only_runtime_lab_pack.manual_review_not_allowed")
    if pack.get("automatic_stage_promotion_allowed") is True:
        blockers.append("read_only_runtime_lab_pack.automatic_promotion_allowed")
    for blocker in _string_list(pack.get("blockers")):
        blockers.append(f"read_only_runtime_lab_pack.{blocker}")

    evidence = _mapping(pack.get("stage_evidence"))
    for name in REQUIRED_STAGE_EVIDENCE:
        if evidence.get(name) is not True:
            blockers.append(f"read_only_runtime_lab_pack.missing_{name}")

    for flag in PACK_NO_GO_FLAGS:
        if pack.get(flag) is True:
            blockers.append(f"read_only_runtime_lab_pack.{flag}")
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
    if review.get("reviewed_read_only_runtime_lab_pack") is not True:
        blockers.append("human_review_decision.pack_not_reviewed")

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
        "reviewed_read_only_runtime_lab_pack": review.get(
            "reviewed_read_only_runtime_lab_pack"
        )
        is True,
    }


def _scope_keys(review: Mapping[str, Any]) -> dict[str, str]:
    scope = _mapping(review.get("scope_keys"))
    return {
        key: str(scope[key])
        for key in REQUIRED_SCOPE_KEYS
        if scope.get(key) is not None
    }


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value] if isinstance(value, list) else []


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
