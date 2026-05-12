from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_live_edd_decision_pack_blockers import (
    build_blockers,
)
from app.advanced_shadow_lab.product_lab_live_edd_decision_pack_policy import (
    NON_CLAIMS,
    failure_taxonomy_summary,
    live_edd_milestone_statuses,
    next_allowed_slices,
    supporting_diagnostic_statuses,
    wall_regression_summary,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_live_edd_decision_pack"
)
ARTIFACT_TYPE = "advanced_product_lab_live_edd_decision_pack"


def build_live_edd_decision_pack(
    *,
    pr_train: Mapping[str, Any],
    diagnostic_artifacts: list[Mapping[str, Any]],
    failure_taxonomy_report: Mapping[str, Any],
    activation_wall_audit: Mapping[str, Any],
) -> dict[str, Any]:
    milestone_statuses = live_edd_milestone_statuses(
        pr_train=pr_train,
        diagnostic_artifacts=diagnostic_artifacts,
        failure_taxonomy_report=failure_taxonomy_report,
        activation_wall_audit=activation_wall_audit,
    )
    supporting_statuses = supporting_diagnostic_statuses(diagnostic_artifacts)
    blockers = build_blockers(
        pr_train=pr_train,
        diagnostic_artifacts=diagnostic_artifacts,
        failure_taxonomy_report=failure_taxonomy_report,
        activation_wall_audit=activation_wall_audit,
        milestone_statuses=milestone_statuses,
        supporting_statuses=supporting_statuses,
    )
    status = "blocked" if blockers else "pass"
    remaining_before = int(pr_train.get("dynamic_remaining_pr_count") or 0)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_live_edd_decision_pack.py",
        "consumer": "advanced_product_lab_followup_planning",
        "planned_pr_count": int(pr_train.get("planned_pr_count") or 0),
        "last_completed_pr_number": int(pr_train.get("last_completed_pr_number") or 0),
        "dynamic_estimate": {
            "remaining_pr_count_before_this_pr": remaining_before,
            "remaining_pr_count_after_pr14_merge": 0 if status == "pass" else remaining_before,
            "estimate_may_change_after_real_dogfood": True,
            "real_dogfood_traces_available": False,
        },
        "milestone_statuses": milestone_statuses,
        "supporting_diagnostic_statuses": supporting_statuses,
        "failure_taxonomy_summary": failure_taxonomy_summary(failure_taxonomy_report),
        "activation_wall_regression": wall_regression_summary(activation_wall_audit),
        "best_practice_evidence": _best_practice_evidence(),
        "blockers": blockers,
        "next_allowed_slices": next_allowed_slices(status),
        "lab_enabled": True,
        "lab_live_edd_complete": status == "pass",
        "lab_product_runtime_loop_complete": status == "pass",
        "ready_for_lab_dogfood_feedback": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "kimi_live_calls_allowed": False,
        "non_claims": list(NON_CLAIMS),
        **dict(FALSE_FLAGS),
    }


def _best_practice_evidence() -> dict[str, Any]:
    return {
        "required": True,
        "sources_checked": [
            "OpenAI evaluation best practices",
            "OpenAI agent evals trace grading guidance",
            "OpenAI Agents SDK guardrails and memory separation guidance",
        ],
        "adopted_guidance": [
            "close live EDD through trace-backed milestones instead of vibe checks",
            "keep memory evidence separate from session/runtime activation",
            "use explicit guard artifacts before any activation claim",
        ],
        "rejected_guidance": [
            "do not treat a live diagnostic pass as mainline activation approval"
        ],
        "how_the_design_changed": (
            "The pack separates lab completion, dogfood readiness, and mainline "
            "activation into independent fields."
        ),
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_live_edd_decision_pack"]
