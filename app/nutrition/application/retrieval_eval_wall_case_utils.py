from __future__ import annotations

from typing import Any


def status(checks: dict[str, bool]) -> str:
    return "pass" if checks and all(checks.values()) else "fail"


def top_candidate(retrieval_result: dict[str, Any]) -> dict[str, Any]:
    candidates = retrieval_result.get("accepted_candidates") or []
    return dict(candidates[0]) if candidates else {}


def ranking_projection(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "anchor_id": candidate.get("anchor_id"),
        "canonical_name": candidate.get("canonical_name"),
        "match_path": candidate.get("match_path"),
        "match_score": candidate.get("match_score"),
        "confidence": candidate.get("confidence"),
        "requires_manager_disambiguation": candidate.get("requires_manager_disambiguation"),
        "runtime_truth_allowed": candidate.get("runtime_truth_allowed"),
        "runtime_usage_boundary": candidate.get("runtime_usage_boundary"),
        "kcal_range": candidate.get("kcal_range"),
        "serving_basis": candidate.get("serving_basis"),
        "portion_basis_present": bool(candidate.get("portion_basis")),
        "followup_hints": list(candidate.get("followup_hints") or []),
        "modifier_compatibility": dict(candidate.get("modifier_compatibility") or {}),
        "ranking_reasons": list(candidate.get("ranking_reasons") or []),
    }


def websearch_classifications(websearch_pipeline: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        classification
        for case in websearch_pipeline.get("cases") or []
        for classification in case.get("candidate_classifications") or []
        if isinstance(classification, dict)
    ]


def websearch_runtime_truth_allowed_count(websearch_pipeline: dict[str, Any]) -> int:
    return sum(
        1
        for classification in websearch_classifications(websearch_pipeline)
        if classification.get("runtime_truth_allowed") is True
    )
