"""
Grounding Pipeline - Search and tool-based evidence enhancement.

Responsibilities:
- Execute external search when needed
- Integrate search results with local evidence
- Maintain evidence chain for auditability

Best Practices:
- Search is conditional (not always used)
- Results merged with local evidence
- Full trace maintained
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from ...application.evidence_assembly import (
    build_tool_result,
    compose_decision_lookup_query,
    execute_primary_tool_request,
    merge_evidence_items,
    normalize_tool_evidence,
)


@dataclass
class GroundingResult:
    """Result from grounding pipeline."""
    sources: list[dict[str, Any]] = field(default_factory=list)
    used_search: bool = False
    search_query: str | None = None
    search_quality: str | None = None
    executed_tool_calls: list[dict[str, Any]] = field(default_factory=list)


class GroundingPipeline:
    """
    Handles search and tool-based grounding.

    Best Practices:
    - Search only when decision pass requests it
    - Results merged with existing sources
    - Quality assessed before use
    """

    async def execute(
        self,
        decision_result: Any,
        retrieval_query: str,
        planner_result: Any,
        request: Any,
        search_adapter: Any | None,
        canonical_meal_state: Any | None,
        task_meal_link_result: Any,
        existing_sources: list[dict[str, Any]] | None = None,
        existing_filtered: list[dict[str, Any]] | None = None,
        executed_tool_calls: list[dict[str, Any]] | None = None,
    ) -> GroundingResult:
        """
        Execute grounding pipeline.

        Returns:
            GroundingResult with search results and metadata
        """
        result = GroundingResult()
        existing_sources = existing_sources or []
        existing_filtered = existing_filtered or []
        executed_tool_calls = executed_tool_calls or []

        # Check if tool lookup is needed
        needs_lookup = (
            decision_result.next_action == "run_tool_lookup"
            and decision_result.tool_plan != "none"
        )
        if not needs_lookup:
            return result

        # Compose lookup query
        lookup_query = compose_decision_lookup_query(
            current_user_input=planner_result.normalized_user_input
            if hasattr(planner_result, "normalized_user_input")
            else "",
            meal_title=(
                canonical_meal_state.meal_title
                if canonical_meal_state
                else None
            ),
            meal_link_action=task_meal_link_result.meal_link_action,
            resolved_query=planner_result.resolved_query
            if hasattr(planner_result, "resolved_query")
            else "",
            retrieval_query=retrieval_query,
        )

        # Execute tool request
        tool_evidence, search_sources, sq, sq_meta = await execute_primary_tool_request(
            tool_request=decision_result.tool_plan,
            tool_reason="Decision pass requested tool lookup.",
            retrieval_query=lookup_query,
            resolved_query=lookup_query,
            planner_result=planner_result,
            request=request,
            search_adapter=search_adapter,
            executed_tool_calls=executed_tool_calls,
            build_tool_result=build_tool_result,
        )

        # Update sources
        if search_sources:
            result.used_search = True
            result.sources = merge_evidence_items(existing_sources, search_sources)
        else:
            result.sources = list(existing_sources)

        result.search_query = sq
        result.search_quality = sq_meta

        # Merge evidence into filtered knowledge
        if tool_evidence:
            existing_filtered = merge_evidence_items(existing_filtered, tool_evidence)

        return result

    def _assess_search_quality(self, sources: list[dict[str, Any]]) -> str:
        """Assess quality of search results."""
        if not sources:
            return "low"
        # Check for official sources
        official_count = sum(
            1 for s in sources
            if "official" in s.get("source_url", "").lower()
            or ".gov" in s.get("source_url", "").lower()
        )
        if official_count > 0:
            return "high"
        if len(sources) >= 3:
            return "medium"
        return "low"
