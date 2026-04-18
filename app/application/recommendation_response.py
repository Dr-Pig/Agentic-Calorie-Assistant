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
        {"action": "recommendation_refresh", "label": "換一個"},
        {"action": "recommendation_filter_low_kcal", "label": "看低熱量"},
        {"action": "recommendation_filter_high_protein", "label": "看高蛋白"},
    ]
    if location_required:
        actions.append({"action": "recommendation_filter_nearby", "label": "看附近店家"})
    if top_pick is not None and hint_packet is not None:
        actions.append(
            {
                "action": "recommendation_intake_handoff",
                "label": "幫我記這個",
                "hint_packet": hint_packet.model_dump(mode="json"),
            }
        )
    return actions


def _render_candidate_line(candidate: RecommendationCandidate) -> str:
    store = f"（{candidate.store_name}）" if candidate.store_name else ""
    kcal = f"{int(candidate.estimated_kcal or 0)} kcal" if candidate.estimated_kcal is not None else "熱量待估"
    return f"{candidate.title}{store}，約 {kcal}"


def _empty_reply(context_packet: RecommendationContextPacket) -> str:
    if context_packet.recommendation_mode == "cold_start":
        return "我先給你保守選項，但你目前的偏好資料還很少，所以這輪先以安全 fallback 為主。"
    if context_packet.hard_constraints.location_required:
        return "我目前沒有足夠的附近候選可推薦，你可以先放寬地點條件，或直接告訴我想吃哪一類。"
    return "我現在找不到合適的候選，你可以改說想吃的類型，或直接要我看低熱量/高蛋白選項。"


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
            },
        )

    top_line = _render_candidate_line(top_pick)
    backup_lines = "；備選：" + "、".join(_render_candidate_line(candidate) for candidate in backup_picks) if backup_picks else ""
    rescue_note = (
        "現在 rescue 還在作用中，所以我先只保留不超過目前可用預算的選項。 "
        if context_packet.hard_constraints.rescue_active
        else ""
    )
    reply_text = f"{rescue_note}我首推你這餐吃 {top_line}。{backup_lines}".strip()

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
        },
    )
