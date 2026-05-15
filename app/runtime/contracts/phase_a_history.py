from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from .phase_a_types import (
    AtomicBlockType,
    HistoryExpansionReason,
    HistoryExpansionScope,
    TranscriptSnippetRole,
)


class HistoryExpansionPolicy(BaseModel):
    max_calls: int = 1
    max_results: int = 5
    max_atomic_blocks: int = 5
    max_transcript_snippets: int = 2


class HistoryExpansionRequest(BaseModel):
    reason: HistoryExpansionReason
    scope: HistoryExpansionScope
    max_results: int = 5
    max_atomic_blocks: int = 5
    max_transcript_snippets: int = 2


class HistoryMealCandidate(BaseModel):
    meal_thread_id: str
    meal_version_id: str | None = None
    label: str = ""
    occurred_at: str | None = None
    reason: str = ""


class ConversationAtomicBlock(BaseModel):
    block_type: AtomicBlockType
    object_ref: dict[str, Any] = Field(default_factory=dict)
    summary: str
    timestamp: str | None = None
    raw_ref: str | None = None


class TranscriptSnippet(BaseModel):
    snippet_id: str
    content: str
    role: TranscriptSnippetRole = "support_only"
    timestamp: str | None = None


class HistoryExpansionResult(BaseModel):
    meal_candidates: list[HistoryMealCandidate] = Field(default_factory=list)
    atomic_blocks: list[ConversationAtomicBlock] = Field(default_factory=list)
    transcript_snippets: list[TranscriptSnippet] = Field(default_factory=list)


__all__ = [
    "ConversationAtomicBlock",
    "HistoryExpansionPolicy",
    "HistoryExpansionReason",
    "HistoryExpansionRequest",
    "HistoryExpansionResult",
    "HistoryExpansionScope",
    "HistoryMealCandidate",
    "TranscriptSnippet",
    "TranscriptSnippetRole",
]
