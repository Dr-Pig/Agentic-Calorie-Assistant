from __future__ import annotations

from dataclasses import dataclass, field

from app.shared.contracts.recommendation import RecommendationCandidate
from .candidate_spec import RecommendationCandidateSpec
from .candidate_retrieval import RecommendationCandidateRetrievalResult
from .context import RecommendationContextPacket


@dataclass(frozen=True)
class RecommendationRankingResult:
    ranked_candidates: list[RecommendationCandidate]
    top_pick: RecommendationCandidate | None
    backup_picks: list[RecommendationCandidate]
    ranking_explanation: str
    presentation_policy: dict[str, object] = field(default_factory=dict)
    filter_reasons: dict[str, list[str]] = field(default_factory=dict)
    candidate_spec_posture: str = ""


def _candidate_item_kind(candidate: RecommendationCandidate) -> str:
    return str(candidate.source_metadata.get("item_kind") or "").strip().lower()


def _candidate_staple_type(candidate: RecommendationCandidate) -> str:
    return str(candidate.source_metadata.get("staple_type") or "").strip().lower()


def _candidate_cuisine_family(candidate: RecommendationCandidate) -> str:
    return str(candidate.source_metadata.get("cuisine_family") or "").strip().lower()


def _candidate_store_name(candidate: RecommendationCandidate) -> str:
    return str(candidate.store_name or "").strip().lower()


def _candidate_time_pattern(candidate: RecommendationCandidate) -> str:
    return str(candidate.source_metadata.get("time_of_day") or "").strip().lower()


def _candidate_protein_posture(candidate: RecommendationCandidate) -> str:
    explicit = str(candidate.source_metadata.get("protein_posture") or "").strip().lower()
    if explicit:
        return explicit
    protein_g = int(candidate.protein_g or 0)
    if protein_g >= 25:
        return "high_protein"
    if protein_g <= 10:
        return "light_protein"
    return "neutral"


def _hard_budget_limit_kcal(context_packet: RecommendationContextPacket) -> int:
    return max(0, int(context_packet.hard_constraints.remaining_budget_kcal or 0))


def _passes_hard_constraints(
    *,
    candidate: RecommendationCandidate,
    context_packet: RecommendationContextPacket,
) -> tuple[bool, str | None]:
    limit_kcal = _hard_budget_limit_kcal(context_packet)
    estimated_kcal = int(candidate.estimated_kcal or 0)
    if limit_kcal <= 0:
        return False, "over_budget_posture"
    if estimated_kcal and estimated_kcal > limit_kcal:
        if context_packet.hard_constraints.rescue_active:
            return False, "exceeds_rescue_overlay_budget"
        return False, "exceeds_remaining_budget"
    return True, None


def _source_priority(candidate: RecommendationCandidate) -> int:
    retrieval_tier = str(candidate.source_metadata.get("retrieval_tier") or "").strip().lower()
    if retrieval_tier == "historical_match":
        return 40
    if retrieval_tier == "nearby":
        return 30
    if retrieval_tier == "golden_order":
        return 20
    if retrieval_tier == "safe_fallback":
        return 10
    return 0


def _soft_preference_score(
    *,
    candidate: RecommendationCandidate,
    context_packet: RecommendationContextPacket,
) -> int:
    score = _source_priority(candidate)
    soft = context_packet.soft_preferences

    if _candidate_item_kind(candidate) in {value.lower() for value in soft.preferred_item_kinds}:
        score += 12
    if _candidate_staple_type(candidate) in {value.lower() for value in soft.preferred_staple_types}:
        score += 10
    if _candidate_cuisine_family(candidate) in {value.lower() for value in soft.preferred_cuisine_families}:
        score += 10
    if _candidate_store_name(candidate) in {value.lower() for value in soft.preferred_store_names}:
        score += 14
    if _candidate_time_pattern(candidate) in {value.lower() for value in soft.time_of_day_patterns}:
        score += 6

    candidate_item_kind = _candidate_item_kind(candidate)
    if candidate_item_kind == "drink":
        score += int(max(0.0, soft.drink_preference_strength) * 8)

    preferred_protein_posture = str(soft.protein_posture_preference or "neutral").strip().lower()
    if preferred_protein_posture != "neutral" and preferred_protein_posture == _candidate_protein_posture(candidate):
        score += 10

    estimated_kcal = int(candidate.estimated_kcal or 0)
    remaining_kcal = max(0, int(context_packet.hard_constraints.remaining_budget_kcal or 0))
    if estimated_kcal > 0 and remaining_kcal > 0:
        distance = abs(remaining_kcal - estimated_kcal)
        score += max(0, 14 - (distance // 50))
        if context_packet.budget_posture in {"tight_budget", "over_budget"}:
            score += max(0, 8 - (estimated_kcal // 100))

    return score


def rank_recommendation_candidates(
    *,
    context_packet: RecommendationContextPacket,
    candidate_spec: RecommendationCandidateSpec,
    retrieval_result: RecommendationCandidateRetrievalResult,
    backup_limit: int = 2,
) -> RecommendationRankingResult:
    filter_reasons = {
        candidate_id: list(reasons)
        for candidate_id, reasons in retrieval_result.candidate_filter_reasons.items()
    }
    scored_candidates: list[tuple[int, RecommendationCandidate]] = []

    for candidate in retrieval_result.candidate_items:
        allowed, reason = _passes_hard_constraints(candidate=candidate, context_packet=context_packet)
        if not allowed:
            filter_reasons.setdefault(candidate.candidate_id, []).append(str(reason))
            continue
        score = _soft_preference_score(candidate=candidate, context_packet=context_packet)
        scored_candidates.append((score, candidate))

    scored_candidates.sort(
        key=lambda item: (
            -item[0],
            int(item[1].estimated_kcal or 0),
            (item[1].title or "").strip().lower(),
        )
    )
    ranked_candidates = [candidate for _, candidate in scored_candidates]
    top_pick = ranked_candidates[0] if ranked_candidates else None
    backup_picks = ranked_candidates[1 : 1 + max(0, backup_limit)]

    if top_pick is None:
        explanation = "No legal recommendation candidates remain after hard-constraint filtering."
    else:
        explanation = (
            "Hard constraints applied first, then soft preferences ranked by retrieval confidence, "
            "preference profile fit, and kcal fit against current remaining budget. "
            f"Candidate spec posture={candidate_spec.candidate_spec_posture}, "
            f"style={candidate_spec.desired_meal_style}, venue={candidate_spec.venue_posture}."
        )

    return RecommendationRankingResult(
        ranked_candidates=ranked_candidates,
        top_pick=top_pick,
        backup_picks=backup_picks,
        ranking_explanation=explanation,
        presentation_policy={
            "surface": "chat_only_v1",
            "show_top_pick": top_pick is not None,
            "backup_limit": max(0, backup_limit),
            "rescue_active": context_packet.hard_constraints.rescue_active,
            "candidate_spec_posture": candidate_spec.candidate_spec_posture,
        },
        filter_reasons=filter_reasons,
        candidate_spec_posture=candidate_spec.candidate_spec_posture,
    )


def build_recommendation_ranking_and_synthesis(
    *,
    context_packet: RecommendationContextPacket,
    candidate_spec: RecommendationCandidateSpec,
    retrieval_result: RecommendationCandidateRetrievalResult,
    backup_limit: int = 2,
) -> RecommendationRankingResult:
    return rank_recommendation_candidates(
        context_packet=context_packet,
        candidate_spec=candidate_spec,
        retrieval_result=retrieval_result,
        backup_limit=backup_limit,
    )
