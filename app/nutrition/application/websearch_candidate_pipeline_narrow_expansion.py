from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .websearch_candidate_pipeline import build_websearch_candidate_pipeline_diagnostic
from .websearch_candidate_pipeline_narrow_expansion_checks import (
    build_coverage_checkpoints,
    required_expansion_case_count,
)
from .websearch_grokfast_live_diagnostic_case_matrix import (
    build_websearch_grokfast_live_diagnostic_case_matrix_artifact,
)

_EXPECTED_PIPELINE_ARTIFACT = "accurate_intake_websearch_candidate_pipeline_v1"
_EXPECTED_LIVE_CASE_MATRIX = (
    "accurate_intake_websearch_grokfast_packet_live_diagnostic_case_matrix"
)
_NEXT_SLICE = "websearch_candidate_pipeline_narrow_expansion"
_CLEAR_SLICE = "inspect_websearch_status_packet"


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
    coverage, coverage_blockers, covered = build_coverage_checkpoints(pipeline_cases=pipeline_cases)
    blockers.extend(coverage_blockers)

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
            "required_expansion_case_count": required_expansion_case_count(),
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


__all__ = ["build_websearch_candidate_pipeline_narrow_expansion_artifact"]
