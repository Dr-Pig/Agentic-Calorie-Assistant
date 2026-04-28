from __future__ import annotations

from typing import Any

from app.nutrition.infrastructure.web_search.exact_item_lookup import resolve_exact_item_fts
from .exact_item_candidate_support import (
    augment_exact_candidate,
    exact_identity_gate,
    fallback_exact_candidates,
)


def resolve_exact_item(
    query: str,
    *,
    active_brand_context: str | None = None,
    required_slots: list[str] | None = None,
    limit: int = 5,
) -> list[dict[str, Any]]:
    search_query = query.strip()
    if active_brand_context and active_brand_context not in search_query:
        search_query = f"{active_brand_context} {search_query}".strip()

    raw_candidates = resolve_exact_item_fts(search_query, limit=max(limit * 2, 6))
    exact_candidates: list[dict[str, Any]] = []
    for candidate in raw_candidates:
        merged_aliases = [str(item) for item in candidate.get("aliases", []) if str(item).strip()]
        if not merged_aliases:
            merged_aliases = [str(candidate.get("title") or "")]
        augmented = augment_exact_candidate(
            candidate | {"aliases": merged_aliases},
            query=search_query,
            required_slots=required_slots,
        )
        if not exact_identity_gate(augmented, query=search_query):
            continue
        exact_candidates.append(augmented)
        if len(exact_candidates) >= limit:
            break
    if exact_candidates:
        return exact_candidates
    return fallback_exact_candidates(search_query=search_query, required_slots=required_slots, limit=limit)


def build_exact_item_lane_packet(
    query: str,
    *,
    active_brand_context: str | None = None,
    required_slots: list[str] | None = None,
    limit: int = 5,
) -> dict[str, Any]:
    exact_candidates = resolve_exact_item(
        query,
        active_brand_context=active_brand_context,
        required_slots=required_slots,
        limit=limit,
    )
    exact_lane_count = len(exact_candidates)
    top_exact_candidate = exact_candidates[0] if exact_candidates else None
    return {
        "query": str(query or "").strip(),
        "active_brand_context": str(active_brand_context or "").strip() or None,
        "exact_candidates": exact_candidates,
        "exact_lane_count": exact_lane_count,
        "local_exact_truth_present": exact_lane_count > 0,
        "exact_truth_available": exact_lane_count > 0,
        "top_exact_candidate": top_exact_candidate,
        "should_skip_web_fallback": exact_lane_count > 0,
    }
