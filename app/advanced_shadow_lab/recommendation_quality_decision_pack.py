from __future__ import annotations

from typing import Any, Mapping

from app.advanced_shadow_lab.e2e_fixture_chain_policy import FALSE_FLAGS
from app.advanced_shadow_lab.recommendation_quality_decision_pack_policy import (
    build_recommendation_quality_evidence_summary,
    recommendation_quality_best_practice_evidence,
    recommendation_quality_blockers,
)


def build_recommendation_quality_decision_pack(
    *,
    pr_train: Mapping[str, Any],
    recommendation_runtime_artifact: Mapping[str, Any],
    holdout_pack: Mapping[str, Any],
    offer_live_diagnostic_summary: Mapping[str, Any],
    paired_lab_e2e_artifact: Mapping[str, Any],
    latency_cost_omission_trace: Mapping[str, Any],
) -> dict[str, Any]:
    evidence_summary = build_recommendation_quality_evidence_summary(
        recommendation_runtime_artifact=recommendation_runtime_artifact,
        holdout_pack=holdout_pack,
        offer_live_diagnostic_summary=offer_live_diagnostic_summary,
        paired_lab_e2e_artifact=paired_lab_e2e_artifact,
        latency_cost_omission_trace=latency_cost_omission_trace,
    )
    blockers = recommendation_quality_blockers(
        recommendation_runtime_artifact=recommendation_runtime_artifact,
        holdout_pack=holdout_pack,
        offer_live_diagnostic_summary=offer_live_diagnostic_summary,
        paired_lab_e2e_artifact=paired_lab_e2e_artifact,
        latency_cost_omission_trace=latency_cost_omission_trace,
    )
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "advanced_product_lab_recommendation_quality_decision_pack",
        "artifact_schema_version": "1.0",
        "status": status,
        "owner": "app/advanced_shadow_lab/recommendation_quality_decision_pack.py",
        "consumer": "advanced_product_lab_recommendation_mainline_dormancy_gate",
        "planned_pr_count": int(pr_train.get("planned_pr_count") or 0),
        "last_completed_pr_number": int(pr_train.get("last_completed_pr_number") or 0),
        "dynamic_remaining_pr_count_before_pack": int(
            pr_train.get("dynamic_remaining_pr_count") or 0
        ),
        "evidence_summary": evidence_summary,
        "readiness_scope": "recommendation_train_quality_gate_only",
        "ready_for_recommendation_mainline_dormancy_gate": status == "pass",
        "ready_for_downstream_shadow_consumers": status == "pass",
        "ready_for_mainline_activation": False,
        "mainline_activation_enabled": False,
        "mainline_runtime_connected": False,
        "self_use_v1_affected": False,
        "canonical_product_mutation_allowed": False,
        "durable_product_memory_written": False,
        "manager_context_packet_changed": False,
        "production_scheduler_delivery_allowed": False,
        "semantic_quality_claimed": False,
        "best_practice_evidence": recommendation_quality_best_practice_evidence(),
        "blockers": blockers,
        **dict(FALSE_FLAGS),
    }


__all__ = ["build_recommendation_quality_decision_pack"]
