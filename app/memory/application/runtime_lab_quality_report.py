from __future__ import annotations

from typing import Any, Mapping

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


def build_runtime_lab_memory_quality_report(
    *,
    suite: Mapping[str, Any],
    fixture_extraction: Mapping[str, Any],
    dogfood_extraction: Mapping[str, Any],
    dogfood_replay_review: Mapping[str, Any] | None = None,
    lifecycle: Mapping[str, Any],
    context_pack: Mapping[str, Any],
    injection: Mapping[str, Any],
    optional_live_run_invoked: bool = False,
) -> dict[str, Any]:
    blockers = _claim_boundary_blockers(
        [fixture_extraction, dogfood_extraction, lifecycle, context_pack, injection]
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
        "non_claims": [
            "not_product_activation_evidence",
            "not_private_self_use_approval",
            "not_mainline_manager_memory_context_injection",
            "not_durable_product_memory",
        ],
        "downstream_shadow_readiness": _downstream_readiness(status),
        "optional_live_run_invoked": optional_live_run_invoked,
        "live_evidence_required_for_merge": False,
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


def _downstream_readiness(status: str) -> dict[str, dict[str, str]]:
    value = (
        "ready_for_shadow_planning"
        if status == "pass"
        else "blocked_by_claim_boundary"
    )
    return {
        "recommendation_read_only": {"status": value},
        "rescue_read_only": {"status": value},
        "proactive_read_only": {"status": value},
    }


__all__ = [
    "SIDECAR_ACTIVATION_CONTRACT",
    "build_runtime_lab_memory_quality_report",
]
