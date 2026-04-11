"""
Evidence Retrieval - Local knowledge and exact item lookup.

Responsibilities:
- Resolve exact items from local database (FTS)
- Resolve ingredient anchors from nutrition knowledge base
- Merge and deduplicate evidence

Best Practices:
- All retrieval is bounded by query
- Quality scoring before passing to LLM
- No external API calls in this module
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...agent.knowledge_packets import resolve_exact_item, resolve_ingredient_anchors
from ...search.chain_retrieval import query_has_known_brand, resolve_chain_item
from ...application.evidence_assembly import (
    build_tool_result,
    merge_evidence_items,
    normalize_tool_evidence,
    retrieval_query_is_usable,
)


MAX_SELECTED_EVIDENCE_ITEMS = 3


@dataclass
class RetrievalResult:
    """Result from evidence retrieval."""
    retrieved_knowledge: list[dict[str, Any]] = field(default_factory=list)
    filtered_knowledge: list[dict[str, Any]] = field(default_factory=list)
    normalized_evidence: list[dict[str, Any]] = field(default_factory=list)
    executed_tool_calls: list[dict[str, Any]] = field(default_factory=list)
    retrieval_triggered: bool = False
    retrieval_query: str = ""


class EvidenceRetrieval:
    """
    Handles local evidence retrieval.

    Best Practices:
    - Bounded retrieval with clear quality signals
    - Evidence filtered and ranked before use
    - Full trace of retrieval decisions
    """

    def __init__(
        self,
        max_items: int = MAX_SELECTED_EVIDENCE_ITEMS,
    ):
        self.max_items = max_items

    def execute(
        self,
        retrieval_query: str,
        evidence_strategy: str,
        input_signals: dict[str, Any],
        user_input: str,
    ) -> RetrievalResult:
        """
        Execute evidence retrieval.

        Args:
            retrieval_query: The query to search for
            evidence_strategy: Strategy hint from planner
            input_signals: Parsed input signals from planner
            user_input: Original user input

        Returns:
            RetrievalResult with all evidence and metadata
        """
        result = RetrievalResult()
        result.retrieval_query = retrieval_query

        # Check if retrieval should run
        if evidence_strategy == "clarify_before_grounding":
            return result
        if not retrieval_query_is_usable(retrieval_query):
            return result

        result.retrieval_triggered = True

        # Get foods from input signals
        foods = list(dict.fromkeys(input_signals.get("foods") or [user_input]))
        portion_hints = input_signals.get("portion_clues", [])

        # Resolve exact items (FTS)
        exact_candidates = self._resolve_exact_candidates(retrieval_query)
        exact_tool_result = build_tool_result(
            tool_name="resolve_exact_item",
            status="executed",
            reason=(
                "Local exact-item resolver executed with branded-chain fast path."
                if query_has_known_brand(retrieval_query)
                else "Local exact-item resolver executed."
            ),
            result_count=len(exact_candidates),
            quality=self._quality_for_candidates(exact_candidates),
        )
        result.executed_tool_calls.append(exact_tool_result)

        # Resolve ingredient anchors
        anchor_candidates = resolve_ingredient_anchors(foods, portion_hints=portion_hints, limit=4)
        anchor_tool_result = build_tool_result(
            tool_name="resolve_ingredient_anchors",
            status="executed",
            reason="Ingredient anchor resolver executed.",
            result_count=len(anchor_candidates),
            quality="medium" if anchor_candidates else "low",
        )
        result.executed_tool_calls.append(anchor_tool_result)

        # Merge evidence
        result.retrieved_knowledge = merge_evidence_items(exact_candidates, anchor_candidates)

        result.filtered_knowledge = list(result.retrieved_knowledge[:self.max_items])

        # Normalize evidence for LLM
        result.normalized_evidence = normalize_tool_evidence(
            result.filtered_knowledge,
            source_type="local_retrieval",
            query=retrieval_query,
            limit=self.max_items,
        )

        return result

    def _quality_for_candidates(self, candidates: list[dict[str, Any]]) -> str:
        """Determine quality of candidates."""
        if not candidates:
            return "low"
        if any(c.get("identity_confidence") == "high" for c in candidates):
            return "high"
        if any(c.get("identity_confidence") == "medium" for c in candidates):
            return "medium"
        return "low"

    def _resolve_exact_candidates(self, retrieval_query: str) -> list[dict[str, Any]]:
        """Prefer local exact truth and strengthen branded queries before web fallback exists."""
        exact_candidates = resolve_exact_item(retrieval_query, limit=4)
        if not query_has_known_brand(retrieval_query):
            return exact_candidates

        chain_candidates = [
            {
                **candidate,
                "tool_name": "resolve_exact_item",
                "retrieval_lane": "exact_lane",
            }
            for candidate in resolve_chain_item(retrieval_query, limit=4)
        ]
        if not chain_candidates:
            return exact_candidates

        return merge_evidence_items(chain_candidates, exact_candidates)[:4]
