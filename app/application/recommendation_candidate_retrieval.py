from __future__ import annotations

from dataclasses import dataclass, field

from ..schemas import RecommendationCandidate
from .recommendation_context import RecommendationContextPacket


@dataclass(frozen=True)
class RecommendationCandidateRetrievalResult:
    candidate_items: list[RecommendationCandidate]
    candidate_source_summary: dict[str, int]
    candidate_filter_reasons: dict[str, list[str]]
    candidate_count: int
    coverage_gaps: list[str] = field(default_factory=list)


def _candidate_key(candidate: RecommendationCandidate) -> str:
    return f"{(candidate.title or '').strip().lower()}::{(candidate.store_name or '').strip().lower()}"


def _annotate_candidate(
    candidate: RecommendationCandidate,
    *,
    retrieval_tier: str,
) -> RecommendationCandidate:
    metadata = dict(candidate.source_metadata or {})
    metadata["retrieval_tier"] = retrieval_tier
    metadata.setdefault("source_type", retrieval_tier)
    return candidate.model_copy(update={"source_metadata": metadata})


def _filter_by_budget(
    *,
    candidate: RecommendationCandidate,
    remaining_budget_kcal: int,
) -> tuple[bool, str | None]:
    estimated_kcal = candidate.estimated_kcal
    if remaining_budget_kcal <= 0:
        return False, "over_budget_posture"
    if estimated_kcal is not None and estimated_kcal > remaining_budget_kcal:
        return False, "exceeds_remaining_budget"
    return True, None


def build_recommendation_candidates(
    *,
    context_packet: RecommendationContextPacket,
    historical_matches: list[RecommendationCandidate] | None = None,
    nearby_candidates: list[RecommendationCandidate] | None = None,
    golden_orders: list[RecommendationCandidate] | None = None,
    safe_defaults: list[RecommendationCandidate] | None = None,
) -> RecommendationCandidateRetrievalResult:
    source_order = (
        ("historical_match", historical_matches or []),
        ("nearby", nearby_candidates or []),
        ("golden_order", golden_orders or []),
        ("safe_fallback", safe_defaults or []),
    )
    remaining_budget_kcal = context_packet.hard_constraints.remaining_budget_kcal
    seen_keys: set[str] = set()
    candidate_items: list[RecommendationCandidate] = []
    source_summary = {name: 0 for name, _ in source_order}
    filter_reasons: dict[str, list[str]] = {}

    for retrieval_tier, candidates in source_order:
        for candidate in candidates:
            key = _candidate_key(candidate)
            if key in seen_keys:
                filter_reasons.setdefault(candidate.candidate_id, []).append("duplicate_candidate")
                continue
            allowed, reason = _filter_by_budget(
                candidate=candidate,
                remaining_budget_kcal=remaining_budget_kcal,
            )
            if not allowed:
                filter_reasons.setdefault(candidate.candidate_id, []).append(str(reason))
                continue
            annotated = _annotate_candidate(candidate, retrieval_tier=retrieval_tier)
            candidate_items.append(annotated)
            seen_keys.add(key)
            source_summary[retrieval_tier] += 1

    coverage_gaps: list[str] = []
    if not candidate_items:
        coverage_gaps.append("no_candidates_after_filtering")
    if not historical_matches:
        coverage_gaps.append("missing_historical_matches")
    if context_packet.recommendation_mode == "cold_start":
        coverage_gaps.append("cold_start")
    if context_packet.hard_constraints.location_required and not nearby_candidates:
        coverage_gaps.append("location_candidates_unavailable")

    return RecommendationCandidateRetrievalResult(
        candidate_items=candidate_items,
        candidate_source_summary=source_summary,
        candidate_filter_reasons=filter_reasons,
        candidate_count=len(candidate_items),
        coverage_gaps=coverage_gaps,
    )
