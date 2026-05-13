from __future__ import annotations

from typing import Any, Mapping

_ACTIVATION_FLAGS = (
    "mainline_activation_enabled",
    "mainline_runtime_connected",
    "served_to_mainline_user",
    "canonical_product_mutation_allowed",
    "durable_product_memory_written",
    "manager_context_packet_changed",
    "production_scheduler_delivery_allowed",
)


def build_recommendation_quality_evidence_summary(
    *,
    recommendation_runtime_artifact: Mapping[str, Any],
    holdout_pack: Mapping[str, Any],
    offer_live_diagnostic_summary: Mapping[str, Any],
    paired_lab_e2e_artifact: Mapping[str, Any],
    latency_cost_omission_trace: Mapping[str, Any],
) -> dict[str, Any]:
    holdout_summary = _mapping(holdout_pack.get("summary"))
    retry = _mapping(latency_cost_omission_trace.get("no_retry_expansion_trace"))
    return {
        "recommendation_runtime_passed": (
            recommendation_runtime_artifact.get("status") == "pass"
        ),
        "holdout_pack_passed": holdout_pack.get("status") == "pass",
        "holdout_case_count": int(holdout_summary.get("case_count") or 0),
        "live_grokfast_offer_diagnostic_pass": (
            offer_live_diagnostic_summary.get("live_grokfast_offer_diagnostic_pass")
            is True
        ),
        "paired_lab_e2e_passed": paired_lab_e2e_artifact.get("status") == "pass",
        "latency_cost_omission_trace_passed": (
            latency_cost_omission_trace.get("status") == "pass"
        ),
        "no_retry_expansion_enforced": (
            retry.get("retry_expansion_allowed") is False
            and retry.get("retry_expansion_attempted") is False
            and retry.get("expanded_context_after_budget_exceeded") is False
        ),
    }


def recommendation_quality_blockers(
    *,
    recommendation_runtime_artifact: Mapping[str, Any],
    holdout_pack: Mapping[str, Any],
    offer_live_diagnostic_summary: Mapping[str, Any],
    paired_lab_e2e_artifact: Mapping[str, Any],
    latency_cost_omission_trace: Mapping[str, Any],
) -> list[str]:
    return [
        *_recommendation_runtime_blockers(recommendation_runtime_artifact),
        *_holdout_blockers(holdout_pack),
        *_live_blockers(offer_live_diagnostic_summary),
        *_paired_blockers(paired_lab_e2e_artifact),
        *_latency_blockers(latency_cost_omission_trace),
    ]


def recommendation_quality_best_practice_evidence() -> dict[str, Any]:
    return {
        "required": True,
        "sources_checked": [
            "OpenAI evaluation best practices",
            "OpenAI agent evals trace grading guidance",
            "OpenAI Agents SDK tool guardrails guidance",
        ],
        "adopted_guidance": [
            "aggregate reproducible fixture, holdout, live, and paired traces",
            "keep quality decision separate from runtime activation",
            "block activation or mutation flags even when quality evidence passes",
        ],
        "rejected_guidance": [
            "do not treat one live diagnostic as product readiness",
            "do not add a generic workflow engine for one recommendation report",
        ],
    }


def _recommendation_runtime_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = _artifact_blockers(
        artifact,
        expected_type="advanced_product_lab_recommendation_runtime_artifact",
        prefix="recommendation_runtime",
    )
    if artifact.get("recommendation_served_to_lab") is not True:
        blockers.append("recommendation_runtime.not_served_to_lab")
    return blockers


def _holdout_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = _artifact_blockers(
        artifact,
        expected_type="advanced_product_lab_recommendation_holdout_pack",
        prefix="holdout_pack",
    )
    if int(_mapping(artifact.get("summary")).get("blocked_count") or 0) > 0:
        blockers.append("holdout_pack.blocked_cases_present")
    return blockers


def _live_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = _artifact_blockers(
        artifact,
        expected_type="recommendation_offer_grokfast_live_diagnostic_summary",
        prefix="offer_live_diagnostic",
    )
    if artifact.get("live_grokfast_offer_diagnostic_pass") is not True:
        blockers.append("offer_live_diagnostic.live_grokfast_not_passed")
    if artifact.get("semantic_quality_claimed") is True:
        blockers.append("offer_live_diagnostic.semantic_quality_claimed")
    return blockers


def _paired_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = _artifact_blockers(
        artifact,
        expected_type="advanced_product_lab_recommendation_paired_e2e",
        prefix="paired_lab_e2e",
    )
    comparison = _mapping(artifact.get("comparison"))
    for field in ("recommendation_tool_added", "pending_intake_handoff_added"):
        if comparison.get(field) is not True:
            blockers.append(f"paired_lab_e2e.{field}_false")
    for field in (
        "canonical_mutation_changed",
        "mainline_activation_changed",
        "manager_context_packet_changed",
    ):
        if comparison.get(field) is True:
            blockers.append(f"paired_lab_e2e.{field}")
    return blockers


def _latency_blockers(artifact: Mapping[str, Any]) -> list[str]:
    blockers = _artifact_blockers(
        artifact,
        expected_type="recommendation_latency_cost_omission_trace",
        prefix="latency_cost_omission_trace",
    )
    retry = _mapping(artifact.get("no_retry_expansion_trace"))
    if retry.get("retry_expansion_attempted") is True:
        blockers.append("latency_cost_omission_trace.retry_expansion_attempted")
    if retry.get("expanded_context_after_budget_exceeded") is True:
        blockers.append("latency_cost_omission_trace.context_expansion_attempted")
    return blockers


def _artifact_blockers(
    artifact: Mapping[str, Any],
    *,
    expected_type: str,
    prefix: str,
) -> list[str]:
    blockers: list[str] = []
    if artifact.get("artifact_type") != expected_type:
        blockers.append(f"{prefix}.unsupported_artifact_type")
    if artifact.get("status") != "pass":
        blockers.append(f"{prefix}.status_not_pass")
    return [*blockers, *_activation_blockers(prefix, artifact)]


def _activation_blockers(prefix: str, artifact: Mapping[str, Any]) -> list[str]:
    return [
        f"{prefix}.{flag}"
        for flag in _ACTIVATION_FLAGS
        if artifact.get(flag) is True
    ]


def _mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}
