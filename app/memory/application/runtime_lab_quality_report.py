from __future__ import annotations

from typing import Any, Mapping

from app.memory.application.runtime_lab_downstream_boundary import (
    ACTIVATION_BOUNDARIES,
    consumer_summary_projection_blockers,
    downstream_shadow_readiness,
    next_allowed_downstream_slices,
)
from app.shared.contracts.sidecar_activation import offline_sidecar_contract


SIDECAR_ACTIVATION_CONTRACT = offline_sidecar_contract(
    "memory.application.runtime_lab_quality_report"
)

CLAIM_BOUNDARY_FLAGS = (
    "manager_context_packet_changed",
    "durable_product_memory_written",
    "user_facing_behavior_changed",
    "canonical_mutation_changed",
)
READ_ONLY_RUNTIME_SOURCE_ARTIFACTS = [
    "runtime_lab_memory_edd_suite",
    "runtime_lab_memory_candidate_extraction",
    "runtime_lab_memory_lifecycle_decision",
    "shadow_memory_context_pack",
    "runtime_lab_manager_memory_injection_comparison",
    "runtime_lab_memory_consumer_summary_projection",
]
READ_ONLY_RUNTIME_NON_CLAIMS = [
    "not_stage_promotion_decision",
    "not_mainline_runtime_activation",
    "not_manager_context_packet_memory_injection",
    "not_durable_memory_write",
    "not_downstream_recommendation_rescue_or_proactive_behavior",
]


def build_runtime_lab_memory_quality_report(
    *,
    suite: Mapping[str, Any],
    fixture_extraction: Mapping[str, Any],
    dogfood_extraction: Mapping[str, Any],
    dogfood_replay_review: Mapping[str, Any] | None = None,
    lifecycle: Mapping[str, Any],
    context_pack: Mapping[str, Any],
    injection: Mapping[str, Any],
    consumer_summary_projection: Mapping[str, Any] | None = None,
    optional_live_run_invoked: bool = False,
) -> dict[str, Any]:
    projection_blockers = consumer_summary_projection_blockers(
        consumer_summary_projection or {}
    )
    read_only_runtime_lab_pack = _read_only_runtime_lab_pack(
        context_pack=context_pack,
        injection=injection,
        consumer_summary_projection=consumer_summary_projection or {},
        projection_blockers=projection_blockers,
    )
    blockers = _claim_boundary_blockers(
        [fixture_extraction, dogfood_extraction, lifecycle, context_pack, injection]
    )
    blockers.extend(projection_blockers)
    if consumer_summary_projection:
        blockers.extend(
            f"read_only_runtime_lab_pack.{blocker}"
            for blocker in read_only_runtime_lab_pack["blockers"]
        )
    status = "blocked" if blockers else "pass"
    return {
        "artifact_type": "runtime_lab_memory_shadow_quality_report",
        "status": status,
        "blockers": blockers,
        "coverage": _coverage(
            suite,
            dogfood_extraction,
            injection,
            dogfood_replay_review or {},
            consumer_summary_projection or {},
        ),
        "activation_ladder": _activation_ladder(
            suite,
            fixture_extraction,
            dogfood_extraction,
            lifecycle,
            context_pack,
            injection,
        ),
        "claim_boundaries": {
            "product_activation_ready": False,
            "private_self_use_approval": False,
            "manager_context_packet_changed": False,
            "durable_product_memory_written": False,
            "user_facing_behavior_changed": False,
            "canonical_mutation_changed": False,
        },
        "activation_boundaries": dict(ACTIVATION_BOUNDARIES),
        "non_claims": [
            "not_product_activation_evidence",
            "not_private_self_use_approval",
            "not_mainline_manager_memory_context_injection",
            "not_durable_product_memory",
        ],
        "downstream_shadow_readiness": downstream_shadow_readiness(
            status,
            consumer_summary_projection or {},
        ),
        "next_allowed_downstream_slices": next_allowed_downstream_slices(
            status,
            consumer_summary_projection or {},
        ),
        "optional_live_run_invoked": optional_live_run_invoked,
        "live_evidence_required_for_merge": False,
        "read_only_runtime_lab_pack": read_only_runtime_lab_pack,
        "runtime_connected": True,
        "lab_isolated": True,
        "runtime_effect_allowed": False,
        "shadow_memory_context_pack_used": bool(
            injection.get("shadow_memory_context_pack_used")
        ),
    }


def _coverage(
    suite: Mapping[str, Any],
    dogfood_extraction: Mapping[str, Any],
    injection: Mapping[str, Any],
    dogfood_replay_review: Mapping[str, Any],
    consumer_summary_projection: Mapping[str, Any],
) -> dict[str, Any]:
    return {
        "split_counts": dict(suite.get("split_counts", {})),
        "fixture_case_count": int(suite.get("case_count") or 0),
        "case_types": list(suite.get("case_types", [])),
        "dogfood_replay_candidate_count": int(
            dogfood_extraction.get("candidate_count") or 0
        ),
        "lab_injection_compared": injection.get("artifact_type")
        == "runtime_lab_manager_memory_injection_comparison",
        "dogfood_reviewed_case_count": int(
            dogfood_replay_review.get("reviewed_case_count") or 0
        ),
        "dogfood_reviewed_proposed_split_counts": dict(
            dogfood_replay_review.get("proposed_split_counts") or {}
        ),
        "consumer_summary_projection_present": bool(consumer_summary_projection),
        "consumer_summary_projection_artifact_type": (
            consumer_summary_projection.get("artifact_type")
            if consumer_summary_projection
            else None
        ),
    }


def _activation_ladder(
    suite: Mapping[str, Any],
    fixture_extraction: Mapping[str, Any],
    dogfood_extraction: Mapping[str, Any],
    lifecycle: Mapping[str, Any],
    context_pack: Mapping[str, Any],
    injection: Mapping[str, Any],
) -> list[dict[str, str]]:
    return [
        _stage("contract", suite.get("status") == "pass"),
        _stage("fixture_fake", fixture_extraction.get("status") == "pass"),
        _stage("live_diagnostic", dogfood_extraction.get("runtime_connected") is True),
        _stage("isolated_shadow_store", lifecycle.get("status") == "pass"),
        _stage("lab_only_context_injection", context_pack.get("status") == "pass"),
        _stage(
            "shadow_comparison",
            injection.get("artifact_type")
            == "runtime_lab_manager_memory_injection_comparison",
        ),
    ]


def _stage(name: str, complete: bool) -> dict[str, str]:
    return {"stage": name, "status": "complete" if complete else "incomplete"}


def _claim_boundary_blockers(artifacts: list[Mapping[str, Any]]) -> list[str]:
    blockers: list[str] = []
    for artifact in artifacts:
        for flag in CLAIM_BOUNDARY_FLAGS:
            if artifact.get(flag) is True and flag not in blockers:
                blockers.append(flag)
    return blockers


def _read_only_runtime_lab_pack(
    *,
    context_pack: Mapping[str, Any],
    injection: Mapping[str, Any],
    consumer_summary_projection: Mapping[str, Any],
    projection_blockers: list[str],
) -> dict[str, Any]:
    evidence = {
        "scope_isolation_check": _scope_isolation_check(context_pack, injection),
        "paired_baseline_comparison": _paired_baseline_comparison(injection),
        "omission_trace_present": isinstance(context_pack.get("omission_trace"), list),
        "latency_budget_observed": _latency_budget_observed(injection),
        "no_commit_fallback": _no_commit_fallback(injection),
    }
    blockers = list(projection_blockers)
    if not consumer_summary_projection:
        blockers.append("consumer_summary_projection_missing")
    blockers.extend(
        f"missing_{name}"
        for name, complete in evidence.items()
        if complete is not True
    )
    status = "pass" if not blockers else "incomplete"
    if consumer_summary_projection and blockers:
        status = "blocked"
    return {
        "artifact_type": "runtime_lab_memory_read_only_runtime_lab_pack",
        "status": status,
        "capability": "long_term_memory",
        "current_stage": "shadow",
        "target_stage": "read_only_runtime",
        "source_artifacts": list(READ_ONLY_RUNTIME_SOURCE_ARTIFACTS),
        "reviewed_memory_pack_loaded": bool(
            consumer_summary_projection and not projection_blockers
        ),
        "stage_evidence": evidence,
        "paired_baseline_evidence": _paired_baseline_evidence(injection),
        "blockers": blockers,
        "manual_promotion_review_allowed": status == "pass",
        "automatic_stage_promotion_allowed": False,
        "runtime_connected": True,
        "lab_isolated": True,
        "mainline_runtime_connected": False,
        "mainline_runtime_connected_allowed": False,
        "manager_context_packet_changed": False,
        "manager_context_packet_changed_in_mainline": False,
        "manager_context_injected": False,
        "durable_product_memory_written": False,
        "user_facing_behavior_changed": False,
        "canonical_mutation_changed": False,
        "mutation_changed": False,
        "runtime_effect_allowed": False,
        "recommendation_served": False,
        "rescue_proposal_committed": False,
        "proactive_sent": False,
        "scheduler_enabled": False,
        "non_claims": list(READ_ONLY_RUNTIME_NON_CLAIMS),
    }


def _scope_isolation_check(
    context_pack: Mapping[str, Any],
    injection: Mapping[str, Any],
) -> bool:
    return (
        context_pack.get("runtime_connected") is True
        and context_pack.get("lab_isolated") is True
        and context_pack.get("manager_context_packet_changed") is False
        and context_pack.get("manager_context_injected") is False
        and injection.get("lab_isolated") is True
        and injection.get("manager_context_packet_changed") is False
        and injection.get("manager_context_injected") is False
    )


def _paired_baseline_comparison(injection: Mapping[str, Any]) -> bool:
    return (
        injection.get("artifact_type")
        == "runtime_lab_manager_memory_injection_comparison"
        and isinstance(injection.get("baseline_run"), Mapping)
        and isinstance(injection.get("memory_context_run"), Mapping)
    )


def _latency_budget_observed(injection: Mapping[str, Any]) -> bool:
    latency = injection.get("latency_comparison")
    return (
        isinstance(latency, Mapping)
        and latency.get("baseline_ms") is not None
        and latency.get("memory_context_ms") is not None
    )


def _no_commit_fallback(injection: Mapping[str, Any]) -> bool:
    return (
        injection.get("tool_calls_blocked") is True
        and injection.get("mutation_attempts_blocked") is True
        and injection.get("durable_product_memory_written") is False
        and injection.get("canonical_mutation_changed") is False
        and injection.get("user_facing_behavior_changed") is False
    )


def _paired_baseline_evidence(injection: Mapping[str, Any]) -> dict[str, Any]:
    baseline = injection.get("baseline_run")
    memory_context = injection.get("memory_context_run")
    baseline_run = baseline if isinstance(baseline, Mapping) else {}
    memory_context_run = memory_context if isinstance(memory_context, Mapping) else {}
    return {
        "baseline_run_type": baseline_run.get("run_type"),
        "memory_context_run_type": memory_context_run.get("run_type"),
        "final_response_changed": bool(injection.get("final_response_changed")),
        "shadow_memory_context_pack_used": bool(
            injection.get("shadow_memory_context_pack_used")
        ),
        "tool_calls_blocked": bool(injection.get("tool_calls_blocked")),
        "mutation_attempts_blocked": bool(
            injection.get("mutation_attempts_blocked")
        ),
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_runtime_lab_memory_quality_report",
]
