from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Callable

from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_grokfast_live_diagnostic_case_matrix import (
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)

_EXPECTED_PIPELINE_ARTIFACT = "accurate_intake_websearch_candidate_pipeline_v1"
_EXPECTED_LIVE_CASE_MATRIX = (
    "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix"
)
_NEXT_SLICE = "websearch_candidate_pipeline_narrow_expansion"
_CLEAR_SLICE = "inspect_websearch_status_packet"
_CHECKPOINTS: tuple[
    tuple[str, str, Callable[[dict[str, Any]], list[str]]],
    ...,
] = (
    (
        "official_brand_positive.large_size_preferred",
        "pipeline_large_size_preferred",
        lambda case: _expect_selected_extract(case),
    ),
    (
        "official_brand_positive.modifier_same_candidate",
        "pipeline_modifier_match_preferred",
        lambda case: _expect_selected_extract(case),
    ),
    (
        "negative_mismatch.serving_size_not_listed",
        "pipeline_serving_size_not_listed",
        lambda case: _expect_blocked(case, reason="serving_basis_missing"),
    ),
    (
        "negative_mismatch.size_unknown_requires_followup",
        "pipeline_size_unknown_requires_followup",
        lambda case: _expect_no_extract(case, candidate_class="near_exact_size_unknown_candidate"),
    ),
    (
        "source_quality.brand_page_without_nutrition",
        "pipeline_missing_kcal",
        lambda case: _expect_blocked(case, reason="kcal_missing"),
    ),
    (
        "source_quality.third_party_blog_snippet",
        "pipeline_third_party_weak",
        lambda case: _expect_no_extract(case, candidate_class="weak_or_unusable_candidate"),
    ),
    (
        "source_quality.all_candidates_blocked_source_policy",
        "pipeline_all_candidates_blocked",
        lambda case: _expect_all_blocked(case),
    ),
)


def build_websearch_candidate_pipeline_narrow_expansion_artifact(
    *,
    candidate_pipeline_artifact: dict[str, Any] | None = None,
    live_case_matrix_artifact: dict[str, Any] | None = None,
) -> dict[str, Any]:
    pipeline = (
        build_websearch_candidate_pipeline_diagnostic()
        if candidate_pipeline_artifact is None
        else candidate_pipeline_artifact
    )
    live_case_matrix = (
        build_websearch_grokfast_live_diagnostic_case_matrix_artifact()
        if live_case_matrix_artifact is None
        else live_case_matrix_artifact
    )
    blockers = _artifact_blockers(pipeline, live_case_matrix)
    pipeline_cases = {
        str(case.get("case_id") or ""): case for case in list(pipeline.get("cases") or []) if isinstance(case, dict)
    }
    coverage = []
    covered = 0
    for checkpoint_id, pipeline_case_id, validator in _CHECKPOINTS:
        case = pipeline_cases.get(pipeline_case_id)
        if case is None:
            blockers.append(f"missing_pipeline_case.{pipeline_case_id}")
            coverage.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "pipeline_case_id": pipeline_case_id,
                    "status": "missing",
                    "blockers": [f"missing_pipeline_case.{pipeline_case_id}"],
                }
            )
            continue
        case_blockers = validator(case)
        if case_blockers:
            blockers.extend(f"{pipeline_case_id}.{blocker}" for blocker in case_blockers)
            coverage.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "pipeline_case_id": pipeline_case_id,
                    "status": "blocked",
                    "blockers": case_blockers,
                }
            )
            continue
        covered += 1
        coverage.append(
            {
                "checkpoint_id": checkpoint_id,
                "pipeline_case_id": pipeline_case_id,
                "status": "pass",
                "candidate_class": _candidate_class(case),
                "selected_extract_packet_id": _selected_extract_packet_id(case),
            }
        )

    status = "pass" if not blockers else "blocked"
    return {
        "artifact_type": "accurate_intake_websearch_candidate_pipeline_narrow_expansion_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        "track": "FDB",
        "classification": "deterministic_websearch_candidate_pipeline_narrow_expansion_only",
        "claim_scope": "websearch_candidate_pipeline_later_live_case_alignment",
        "status": status,
        "blockers": sorted(set(blockers)),
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "shared_contract_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "summary": {
            "pipeline_case_count": int(dict(pipeline.get("summary") or {}).get("case_count") or 0),
            "live_case_matrix_case_count": int(
                dict(live_case_matrix.get("summary") or {}).get("case_count") or 0
            ),
            "required_expansion_case_count": len(_CHECKPOINTS),
            "covered_expansion_case_count": covered,
            "exact_review_candidate_count": int(
                dict(pipeline.get("summary") or {}).get("exact_review_candidate_count") or 0
            ),
            "disambiguation_candidate_count": int(
                dict(pipeline.get("summary") or {}).get("disambiguation_candidate_count") or 0
            ),
            "blocked_candidate_count": int(
                dict(pipeline.get("summary") or {}).get("blocked_candidate_count") or 0
            ),
            "weak_candidate_count": int(
                dict(pipeline.get("summary") or {}).get("weak_candidate_count") or 0
            ),
        },
        "coverage_checkpoints": coverage,
        "next_required_slice": _CLEAR_SLICE if status == "pass" else _NEXT_SLICE,
        "non_claims": [
            "no_live_websearch_call",
            "no_live_provider_call",
            "no_websearch_runtime_truth",
            "no_exact_card_truth_promotion",
            "no_runtime_mutation",
            "no_shared_contract_change",
            "no_manager_context_change",
            "no_readiness_claim",
        ],
    }


def _artifact_blockers(pipeline: dict[str, Any], live_case_matrix: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    if str(pipeline.get("artifact_type") or "") != _EXPECTED_PIPELINE_ARTIFACT:
        return ["unsupported_candidate_pipeline_artifact"]
    if str(live_case_matrix.get("artifact_type") or "") != _EXPECTED_LIVE_CASE_MATRIX:
        return ["unsupported_live_case_matrix_artifact"]
    for artifact, prefix in ((pipeline, "candidate_pipeline"), (live_case_matrix, "live_case_matrix")):
        if artifact.get("runtime_truth_changed") is True:
            blockers.append(f"{prefix}.runtime_truth_changed")
        if artifact.get("live_provider_used") is True or artifact.get("live_provider_invoked") is True:
            blockers.append(f"{prefix}.live_provider_used")
        if artifact.get("live_websearch_used") is True or artifact.get("websearch_invoked") is True:
            blockers.append(f"{prefix}.live_websearch_used")
        if artifact.get("readiness_claimed") is True or artifact.get("product_readiness_claimed") is True:
            blockers.append(f"{prefix}.readiness_claimed")
    later_candidates = dict(live_case_matrix.get("later_expansion_candidates") or {})
    expected_candidates = {
        "official_brand_positive": ["large_size_preferred", "modifier_same_candidate"],
        "negative_mismatch": ["serving_size_not_listed", "size_unknown_requires_followup"],
        "source_quality": [
            "brand_page_without_nutrition",
            "third_party_blog_snippet",
            "all_candidates_blocked_source_policy",
        ],
    }
    for key, expected in expected_candidates.items():
        observed = list(later_candidates.get(key) or [])
        if observed != expected:
            blockers.append(f"live_case_matrix_later_expansion_mismatch.{key}")
    return blockers


def _expect_selected_extract(case: dict[str, Any]) -> list[str]:
    blockers: list[str] = []
    selected_id = _selected_extract_packet_id(case)
    if not selected_id:
        blockers.append("selected_extract_missing")
    packet_ids = {str(packet.get("packet_id") or "") for packet in list(case.get("candidate_packets") or [])}
    if selected_id and selected_id not in packet_ids:
        blockers.append("selected_extract_not_in_candidate_packets")
    classifications = list(case.get("candidate_classifications") or [])
    if not any(
        str(classification.get("candidate_class") or "") == "exact_candidate_for_extract_review"
        for classification in classifications
    ):
        blockers.append("exact_candidate_for_extract_review_missing")
    return blockers


def _expect_no_extract(case: dict[str, Any], *, candidate_class: str, expect_selected: bool = False) -> list[str]:
    blockers: list[str] = []
    if _candidate_class(case) != candidate_class:
        blockers.append(f"candidate_class_not_{candidate_class}")
    selected_id = _selected_extract_packet_id(case)
    if expect_selected and not selected_id:
        blockers.append("selected_extract_missing")
    if not expect_selected and selected_id:
        blockers.append("selected_extract_unexpected")
    return blockers


def _expect_blocked(case: dict[str, Any], *, reason: str) -> list[str]:
    blockers = _expect_no_extract(case, candidate_class="blocked_source_policy_candidate")
    reasons = list(dict(case.get("selected_extract_decision") or {}).get("source_policy_block_reasons") or [])
    if reason not in reasons:
        blockers.append(f"missing_source_policy_block_reason.{reason}")
    return blockers


def _expect_all_blocked(case: dict[str, Any]) -> list[str]:
    blockers = _expect_blocked(case, reason="license_unknown")
    reasons = list(dict(case.get("selected_extract_decision") or {}).get("source_policy_block_reasons") or [])
    if "robots_blocked" not in reasons:
        blockers.append("missing_source_policy_block_reason.robots_blocked")
    if str(dict(case.get("selected_extract_decision") or {}).get("extract_reason") or "") != (
        "source_policy_blocked_selected_extract"
    ):
        blockers.append("extract_reason_not_source_policy_blocked_selected_extract")
    return blockers


def _candidate_class(case: dict[str, Any]) -> str:
    classifications = list(case.get("candidate_classifications") or [])
    if not classifications:
        return ""
    return str(dict(classifications[0]).get("candidate_class") or "")


def _selected_extract_packet_id(case: dict[str, Any]) -> str:
    return str(dict(case.get("selected_extract_decision") or {}).get("selected_search_packet_id") or "")


__all__ = ["build_websearch_candidate_pipeline_narrow_expansion_artifact"]
