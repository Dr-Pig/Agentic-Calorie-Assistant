from __future__ import annotations

from typing import Any, Callable

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


def build_coverage_checkpoints(
    *,
    pipeline_cases: dict[str, dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[str], int]:
    coverage: list[dict[str, Any]] = []
    blockers: list[str] = []
    covered = 0
    for checkpoint_id, pipeline_case_id, validator in _CHECKPOINTS:
        case = pipeline_cases.get(pipeline_case_id)
        if case is None:
            blocker = f"missing_pipeline_case.{pipeline_case_id}"
            blockers.append(blocker)
            coverage.append(
                {
                    "checkpoint_id": checkpoint_id,
                    "pipeline_case_id": pipeline_case_id,
                    "status": "missing",
                    "blockers": [blocker],
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
    return coverage, blockers, covered


def required_expansion_case_count() -> int:
    return len(_CHECKPOINTS)


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


def _expect_no_extract(case: dict[str, Any], *, candidate_class: str) -> list[str]:
    blockers: list[str] = []
    if _candidate_class(case) != candidate_class:
        blockers.append(f"candidate_class_not_{candidate_class}")
    if _selected_extract_packet_id(case):
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


__all__ = ["build_coverage_checkpoints", "required_expansion_case_count"]
