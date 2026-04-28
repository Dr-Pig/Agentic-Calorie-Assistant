from __future__ import annotations

from dataclasses import dataclass, field

from app.shared.contracts.recommendation import RecommendationCandidate
from .candidate_spec import RecommendationCandidateSpec
from .context import RecommendationContextPacket


@dataclass(frozen=True)
class RecommendationCandidateRetrievalResult:
    candidate_items: list[RecommendationCandidate]
    candidate_source_summary: dict[str, int]
    candidate_filter_reasons: dict[str, list[str]]
    candidate_count: int
    candidate_spec_used: dict[str, object] = field(default_factory=dict)
    coverage_gaps: list[str] = field(default_factory=list)


def _candidate_key(candidate: RecommendationCandidate) -> str:
    return f"{(candidate.title or '').strip().lower()}::{(candidate.store_name or '').strip().lower()}"


def _candidate_metadata_text(candidate: RecommendationCandidate) -> str:
    metadata = dict(candidate.source_metadata or {})
    parts = [
        str(candidate.title or "").strip().lower(),
        str(candidate.store_name or "").strip().lower(),
        str(metadata.get("item_kind") or "").strip().lower(),
        str(metadata.get("staple_type") or "").strip().lower(),
        str(metadata.get("cuisine_family") or "").strip().lower(),
        str(metadata.get("venue_type") or "").strip().lower(),
    ]
    return " ".join(part for part in parts if part)


def _annotate_candidate(
    candidate: RecommendationCandidate,
    *,
    retrieval_tier: str,
    candidate_spec_posture: str,
) -> RecommendationCandidate:
    metadata = dict(candidate.source_metadata or {})
    metadata["retrieval_tier"] = retrieval_tier
    metadata.setdefault("source_type", retrieval_tier)
    metadata["candidate_spec_posture"] = candidate_spec_posture
    return candidate.model_copy(update={"source_metadata": metadata})


def _filter_by_budget(
    *,
    candidate: RecommendationCandidate,
    candidate_spec: RecommendationCandidateSpec,
) -> tuple[bool, str | None]:
    remaining_budget_kcal = max(0, int(candidate_spec.target_kcal_max or 0))
    estimated_kcal = candidate.estimated_kcal
    if remaining_budget_kcal <= 0:
        return False, "over_budget_posture"
    if estimated_kcal is not None and estimated_kcal > remaining_budget_kcal:
        return False, "exceeds_remaining_budget"
    return True, None


def _filter_by_candidate_spec(
    *,
    candidate: RecommendationCandidate,
    candidate_spec: RecommendationCandidateSpec,
) -> tuple[bool, str | None]:
    metadata = dict(candidate.source_metadata or {})
    item_kind = str(metadata.get("item_kind") or "").strip().lower()
    cuisine_family = str(metadata.get("cuisine_family") or "").strip().lower()
    store_name = str(candidate.store_name or "").strip().lower()
    venue_type = str(metadata.get("venue_type") or "").strip().lower()
    candidate_text = _candidate_metadata_text(candidate)

    if item_kind and item_kind in set(candidate_spec.excluded_item_kinds):
        return False, "excluded_by_candidate_spec"

    if candidate_spec.desired_store_names and store_name not in set(candidate_spec.desired_store_names):
        if "nearby" not in set(candidate_spec.retrieval_terms):
            return False, "store_not_in_candidate_spec"

    if candidate_spec.desired_cuisine_families and cuisine_family:
        if cuisine_family not in set(candidate_spec.desired_cuisine_families):
            return False, "cuisine_not_in_candidate_spec"

    if candidate_spec.desired_item_kinds and item_kind:
        if item_kind not in set(candidate_spec.desired_item_kinds):
            return False, "item_kind_not_in_candidate_spec"

    if candidate_spec.venue_posture != "any" and venue_type:
        if venue_type != candidate_spec.venue_posture:
            return False, "venue_not_in_candidate_spec"

    for pattern in candidate_spec.excluded_item_patterns:
        if pattern.lower() in candidate_text:
            return False, f"excluded_by_candidate_spec:{pattern.lower()}"

    return True, None


def build_recommendation_candidates(
    *,
    context_packet: RecommendationContextPacket,
    candidate_spec: RecommendationCandidateSpec,
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
                candidate_spec=candidate_spec,
            )
            if not allowed:
                filter_reasons.setdefault(candidate.candidate_id, []).append(str(reason))
                continue
            allowed, reason = _filter_by_candidate_spec(
                candidate=candidate,
                candidate_spec=candidate_spec,
            )
            if not allowed:
                filter_reasons.setdefault(candidate.candidate_id, []).append(str(reason))
                continue
            annotated = _annotate_candidate(
                candidate,
                retrieval_tier=retrieval_tier,
                candidate_spec_posture=candidate_spec.candidate_spec_posture,
            )
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
        candidate_spec_used={
            "desired_meal_style": candidate_spec.desired_meal_style,
            "target_kcal_min": candidate_spec.target_kcal_min,
            "target_kcal_max": candidate_spec.target_kcal_max,
            "venue_posture": candidate_spec.venue_posture,
            "candidate_spec_posture": candidate_spec.candidate_spec_posture,
        },
        coverage_gaps=coverage_gaps,
    )


def retrieve_recommendation_candidates(
    *,
    context_packet: RecommendationContextPacket,
    candidate_spec: RecommendationCandidateSpec,
    historical_matches: list[RecommendationCandidate] | None = None,
    nearby_candidates: list[RecommendationCandidate] | None = None,
    golden_orders: list[RecommendationCandidate] | None = None,
    safe_defaults: list[RecommendationCandidate] | None = None,
) -> RecommendationCandidateRetrievalResult:
    return build_recommendation_candidates(
        context_packet=context_packet,
        candidate_spec=candidate_spec,
        historical_matches=historical_matches,
        nearby_candidates=nearby_candidates,
        golden_orders=golden_orders,
        safe_defaults=safe_defaults,
    )
