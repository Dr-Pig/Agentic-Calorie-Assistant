from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .common import RecommendationCandidateKind


class RecommendationCandidate(BaseModel):
    candidate_id: str
    candidate_kind: RecommendationCandidateKind
    title: str
    store_name: str | None = None
    estimated_kcal: int | None = None
    protein_g: int | None = None
    fit_summary: str = ""
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class HintPacket(BaseModel):
    candidate_id: str
    title: str
    store_name: str | None = None
    estimated_kcal: int | None = None
    protein_g: int | None = None
    source_metadata: dict[str, Any] = Field(default_factory=dict)


class RecommendationResponseResult(BaseModel):
    top_pick: RecommendationCandidate | None = None
    backup_picks: list[RecommendationCandidate] = Field(default_factory=list)
    hint_packet: HintPacket | None = None
    reply_text: str = ""
    quick_actions: list[dict[str, Any]] = Field(default_factory=list)
