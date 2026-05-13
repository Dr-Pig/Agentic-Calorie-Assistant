from __future__ import annotations

from typing import Any, Mapping


def summarize_recommendation_offer_live_diagnostic(
    artifact: Mapping[str, Any],
) -> dict[str, Any]:
    response = _mapping(artifact.get("recommendation_response"))
    flags = _mapping(artifact.get("activation_flags"))
    blockers = [
        *_source_blockers(artifact),
        *_response_blockers(response),
        *_activation_blockers(flags),
    ]
    provider_used = _offer_synthesis_provider_used(artifact)
    return {
        "artifact_type": "recommendation_offer_grokfast_live_diagnostic_summary",
        "status": "blocked" if blockers else "pass",
        "source_artifact_type": str(artifact.get("artifact_type") or ""),
        "provider_mode": str(artifact.get("provider_mode") or ""),
        "live_grokfast_offer_diagnostic_pass": (
            not blockers
            and artifact.get("live_provider_invoked") is True
            and provider_used
        ),
        "offer_synthesis_provider_used": provider_used,
        "deterministic_guard_replayed": artifact.get("deterministic_guard_replayed") is True,
        "selected_candidate_id": str(response.get("candidate_id") or ""),
        "recommendation_served": response.get("recommendation_served") is True,
        "intake_committed": response.get("intake_commit_requested") is True,
        "canonical_product_mutation_allowed": (
            flags.get("canonical_product_mutation_allowed") is True
        ),
        "mainline_runtime_connected": flags.get("mainline_runtime_connected") is True,
        "user_facing_behavior_changed": flags.get("user_facing_behavior_changed") is True,
        "semantic_quality_claimed": False,
        "blockers": blockers,
    }


def _source_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != "recommendation_three_node_live_diagnostic":
        blockers.append("source_artifact_type.unsupported")
    if artifact.get("status") != "pass":
        blockers.append("source_artifact.status_not_pass")
    if artifact.get("live_provider_invoked") is not True:
        blockers.append("source_artifact.live_provider_not_invoked")
    if _mapping(artifact.get("node_status_by_physical_node")).get("offer_synthesis") != "pass":
        blockers.append("offer_synthesis_node.status_not_pass")
    if artifact.get("deterministic_guard_replayed") is not True:
        blockers.append("deterministic_guard_not_replayed")
    return blockers


def _response_blockers(response: Mapping[str, Any]) -> list[str]:
    blockers: list[str] = []
    if not str(response.get("candidate_id") or ""):
        blockers.append("recommendation_response.candidate_id_missing")
    if response.get("recommendation_served") is True:
        blockers.append("recommendation_response.recommendation_served_true")
    if response.get("intake_commit_requested") is True:
        blockers.append("recommendation_response.intake_commit_requested_true")
    if response.get("is_canonical_truth") is True:
        blockers.append("recommendation_response.is_canonical_truth_true")
    return blockers


def _activation_blockers(flags: Mapping[str, Any]) -> list[str]:
    return [
        f"activation_flags.{name}_true"
        for name in (
            "mainline_runtime_connected",
            "canonical_product_mutation_allowed",
            "user_facing_behavior_changed",
        )
        if flags.get(name) is True
    ]


def _offer_synthesis_provider_used(artifact: Mapping[str, Any]) -> bool:
    used_by_node = _mapping(artifact.get("node_provider_used_by_physical_node"))
    return used_by_node.get("offer_synthesis") is True


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


__all__ = ["summarize_recommendation_offer_live_diagnostic"]
