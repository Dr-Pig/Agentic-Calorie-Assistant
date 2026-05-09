from __future__ import annotations

from typing import Any

from app.nutrition.application.exact_item_lookup_port import (
    ExactItemLookupPort,
    default_exact_item_lookup_port,
)
from app.nutrition.application.retrieval_intent import build_raw_text_retrieval_hint
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
    lookup_port: ExactItemLookupPort | None = None,
) -> list[dict[str, Any]]:
    search_queries = _candidate_search_queries(query, active_brand_context=active_brand_context)
    exact_lookup = lookup_port or default_exact_item_lookup_port()
    for search_query in search_queries:
        raw_candidates = exact_lookup.resolve_exact_item_fts(search_query, limit=max(limit * 2, 6))
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
    return fallback_exact_candidates(search_query=search_queries[0], required_slots=required_slots, limit=limit)


def _candidate_search_queries(query: str, *, active_brand_context: str | None) -> list[str]:
    raw_query = str(query or "").strip()
    values: list[str] = []

    def _append(text: str | None) -> None:
        cleaned = str(text or "").strip()
        if cleaned and cleaned not in values:
            values.append(cleaned)

    if active_brand_context and active_brand_context not in raw_query:
        _append(f"{active_brand_context} {raw_query}")
    _append(raw_query)

    hint = build_raw_text_retrieval_hint(raw_query)
    _append(hint.base_dish)
    for alias in hint.aliases:
        _append(alias)
    if hint.brand_hint and hint.base_dish:
        _append(f"{hint.brand_hint}{hint.base_dish}")
        if hint.size_hint:
            _append(f"{hint.brand_hint}{hint.base_dish}{hint.size_hint}")
    return values or [raw_query]


def build_exact_item_lane_packet(
    query: str,
    *,
    active_brand_context: str | None = None,
    required_slots: list[str] | None = None,
    limit: int = 5,
    lookup_port: ExactItemLookupPort | None = None,
) -> dict[str, Any]:
    exact_candidates = resolve_exact_item(
        query,
        active_brand_context=active_brand_context,
        required_slots=required_slots,
        limit=limit,
        lookup_port=lookup_port,
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
