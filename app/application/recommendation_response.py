from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ..schemas import HintPacket, RecommendationCandidate, RecommendationResponseResult
from .recommendation_context import RecommendationContextPacket
from .recommendation_ranking import RecommendationRankingResult


@dataclass(frozen=True)
class RecommendationResponsePacket:
    response: RecommendationResponseResult
    asked_follow_up: bool
    ui_hints: dict[str, Any] = field(default_factory=dict)


def _build_hint_packet(candidate: RecommendationCandidate) -> HintPacket:
    return HintPacket(
        candidate_id=candidate.candidate_id,
        title=candidate.title,
        store_name=candidate.store_name,
        estimated_kcal=candidate.estimated_kcal,
        protein_g=candidate.protein_g,
        source_metadata=dict(candidate.source_metadata or {}),
    )


def _build_quick_actions(
    *,
    top_pick: RecommendationCandidate | None,
    hint_packet: HintPacket | None,
    location_required: bool,
) -> list[dict[str, Any]]:
    actions: list[dict[str, Any]] = [
        {"action": "recommendation_refresh", "label": "Show another"},
        {"action": "recommendation_filter_low_kcal", "label": "Lower kcal"},
        {"action": "recommendation_filter_high_protein", "label": "Higher protein"},
    ]
    if location_required:
        actions.append({"action": "recommendation_filter_nearby", "label": "Nearby only"})
    if top_pick is not None and hint_packet is not None:
        actions.append(
            {
                "action": "recommendation_intake_handoff",
                "label": "Log this meal",
                "hint_packet": hint_packet.model_dump(mode="json"),
            }
        )
    return actions


def _render_candidate_line(candidate: RecommendationCandidate) -> str:
    store = f" ({candidate.store_name})" if candidate.store_name else ""
    kcal = f"{int(candidate.estimated_kcal or 0)} kcal" if candidate.estimated_kcal is not None else "kcal unknown"
    return f"{candidate.title}{store} - {kcal}"


def _empty_reply(context_packet: RecommendationContextPacket) -> str:
    if context_packet.recommendation_mode == "cold_start":
        return (
            "I do not have enough preference history yet, so I only have fallback options right now. "
            "Log a few meals and I can make better recommendations."
        )
    if context_packet.hard_constraints.location_required:
        return (
            "I do not have enough legal nearby candidates for this request yet. "
            "Try broadening the ask or let me suggest a lower-friction fallback."
        )
    return (
        "I do not have a legal recommendation candidate right now under the current constraints. "
        "You can loosen the ask or ask for a different style."
    )


def build_recommendation_response(
    *,
    context_packet: RecommendationContextPacket,
    ranking_result: RecommendationRankingResult,
) -> RecommendationResponsePacket:
    top_pick = ranking_result.top_pick
    backup_picks = list(ranking_result.backup_picks)
    hint_packet = _build_hint_packet(top_pick) if top_pick is not None else None
    quick_actions = _build_quick_actions(
        top_pick=top_pick,
        hint_packet=hint_packet,
        location_required=context_packet.hard_constraints.location_required,
    )

    if top_pick is None:
        response = RecommendationResponseResult(
            top_pick=None,
            backup_picks=[],
            hint_packet=None,
            reply_text=_empty_reply(context_packet),
            quick_actions=quick_actions,
        )
        return RecommendationResponsePacket(
            response=response,
            asked_follow_up=False,
            ui_hints={
                "mode": "recommendation_no_candidates",
                "delivery": "chat_only",
                "non_mutating": True,
                "candidate_spec_posture": ranking_result.candidate_spec_posture,
            },
        )

    top_line = _render_candidate_line(top_pick)
    backup_lines = ""
    if backup_picks:
        backup_lines = " Backups: " + "; ".join(_render_candidate_line(candidate) for candidate in backup_picks)
    rescue_note = (
        "Rescue is active, so these picks stay inside the tighter budget window. "
        if context_packet.hard_constraints.rescue_active
        else ""
    )
    reply_text = f"{rescue_note}Top pick: {top_line}.{backup_lines}".strip()

    response = RecommendationResponseResult(
        top_pick=top_pick,
        backup_picks=backup_picks,
        hint_packet=hint_packet,
        reply_text=reply_text,
        quick_actions=quick_actions,
    )
    return RecommendationResponsePacket(
        response=response,
        asked_follow_up=False,
        ui_hints={
            "mode": "recommendation_chat_response",
            "delivery": "chat_only",
            "non_mutating": True,
            "candidate_count": len(ranking_result.ranked_candidates),
            "candidate_spec_posture": ranking_result.candidate_spec_posture,
        },
    )
