from __future__ import annotations

from typing import Any

from ...runtime.contracts.phase_a import (
    ConversationAtomicBlock,
    HistoryExpansionPolicy,
    HistoryExpansionRequest,
    HistoryExpansionResult,
    HistoryMealCandidate,
    TranscriptSnippet,
)


def default_history_expansion_policy() -> HistoryExpansionPolicy:
    return HistoryExpansionPolicy()


def build_history_expansion_request(
    *,
    reason: str,
    scope: str,
    policy: HistoryExpansionPolicy | None = None,
    max_results: int | None = None,
    max_atomic_blocks: int | None = None,
    max_transcript_snippets: int | None = None,
) -> HistoryExpansionRequest:
    effective_policy = policy or default_history_expansion_policy()
    return HistoryExpansionRequest(
        reason=reason,
        scope=scope,
        max_results=max_results or effective_policy.max_results,
        max_atomic_blocks=max_atomic_blocks or effective_policy.max_atomic_blocks,
        max_transcript_snippets=max_transcript_snippets or effective_policy.max_transcript_snippets,
    )


def build_history_expansion_result(
    *,
    meal_candidates: list[dict[str, Any]] | None = None,
    atomic_blocks: list[dict[str, Any]] | None = None,
    transcript_snippets: list[dict[str, Any]] | None = None,
    policy: HistoryExpansionPolicy | None = None,
) -> HistoryExpansionResult:
    effective_policy = policy or default_history_expansion_policy()
    return HistoryExpansionResult(
        meal_candidates=[
            HistoryMealCandidate.model_validate(item)
            for item in list(meal_candidates or [])[: effective_policy.max_results]
        ],
        atomic_blocks=[
            ConversationAtomicBlock.model_validate(item)
            for item in list(atomic_blocks or [])[: effective_policy.max_atomic_blocks]
        ],
        transcript_snippets=[
            TranscriptSnippet.model_validate(item)
            for item in list(transcript_snippets or [])[: effective_policy.max_transcript_snippets]
        ],
    )
