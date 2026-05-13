from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.product_lab_rescue_phase1_decision_policy import (
    accept_dismiss_summary,
    claim_drift_blockers,
    golden_set_blockers,
    journey_statuses,
    milestone_blockers,
    milestone_statuses,
    pr_train_blockers,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "advanced_shadow_lab.product_lab_rescue_phase1_decision_pack"
)
ARTIFACT_TYPE = "advanced_product_lab_rescue_phase1_e2e_decision_pack"


def build_rescue_phase1_e2e_decision_pack(
    *,
    pr_train: Mapping[str, Any],
    golden_set: Mapping[str, Any],
    replay_artifacts: list[Mapping[str, Any]],
    live_diagnostic_artifacts: list[Mapping[str, Any]],
) -> dict[str, Any]:
    journeys = journey_statuses(replay_artifacts)
    accept_dismiss = accept_dismiss_summary(replay_artifacts)
    milestones = milestone_statuses(
        golden_set=golden_set,
        replay_artifacts=replay_artifacts,
        live_diagnostic_artifacts=live_diagnostic_artifacts,
        journey_statuses=journeys,
        accept_dismiss=accept_dismiss,
    )
    blockers = [
        *pr_train_blockers(pr_train),
        *golden_set_blockers(golden_set),
        *milestone_blockers(milestones),
        *claim_drift_blockers(replay_artifacts, live_diagnostic_artifacts),
    ]
    status = "blocked" if blockers else "pass"
    remaining_before = int(pr_train.get("dynamic_remaining_pr_count") or 0)
    return {
        "artifact_type": ARTIFACT_TYPE,
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/product_lab_rescue_phase1_decision_pack.py",
        "consumer": "advanced_product_lab_followup_planning",
        "planned_pr_count": int(pr_train.get("planned_pr_count") or 0),
        "last_completed_pr_number": int(pr_train.get("last_completed_pr_number") or 0),
        "dynamic_estimate": {
            "remaining_pr_count_before_this_pr": remaining_before,
            "remaining_pr_count_after_pr24_merge": 0 if status == "pass" else remaining_before,
            "estimate_may_change_after_real_dogfood": True,
            "real_dogfood_traces_available": False,
        },
        "milestone_statuses": milestones,
        "journey_statuses": journeys,
        "lab_accept_dismiss_e2e": accept_dismiss,
        "best_practice_evidence": _best_practice_evidence(),
        "blockers": blockers,
        "next_allowed_slices": _next_allowed_slices(status),
        "lab_enabled": True,
        "lab_product_loop_complete": status == "pass",
        "ready_for_lab_dogfood_feedback": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "durable_product_memory_written": False,
        "canonical_product_mutation_allowed": False,
        "production_scheduler_delivery_allowed": False,
        "production_db_migration_allowed": False,
        **dict(FALSE_FLAGS),
    }


def _next_allowed_slices(status: str) -> list[str]:
    if status != "pass":
        return []
    return ["operator_dogfood_trace_collection", "separate_mainline_activation_planning"]


def _best_practice_evidence() -> dict[str, Any]:
    return {
        "required": True,
        "sources_checked": [
            "OpenAI evaluation best practices",
            "OpenAI agent evals",
            "OpenAI Agents SDK guardrails",
        ],
        "adopted_guidance": [
            "close with reproducible fixture evidence and live diagnostic milestones",
            "keep lab completion separate from mainline activation",
            "keep provider output advisory behind deterministic validators",
        ],
        "rejected_guidance": ["do not use live provider pass as production activation"],
    }


__all__ = ["SIDECAR_ACTIVATION_CONTRACT", "build_rescue_phase1_e2e_decision_pack"]
