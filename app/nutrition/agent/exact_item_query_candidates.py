from __future__ import annotations

from app.nutrition.application.retrieval_intent import build_raw_text_retrieval_hint


def candidate_search_queries(query: str, *, active_brand_context: str | None) -> list[str]:
    raw_query = str(query or "").strip()
    values: list[str] = []

    def append(text: str | None) -> None:
        cleaned = str(text or "").strip()
        if cleaned and cleaned not in values:
            values.append(cleaned)

    if active_brand_context and active_brand_context not in raw_query:
        append(f"{active_brand_context} {raw_query}")
    append(raw_query)

    hint = build_raw_text_retrieval_hint(raw_query)
    append(hint.base_dish)
    for alias in hint.aliases:
        append(alias)
    if hint.brand_hint and hint.base_dish:
        append(f"{hint.brand_hint}{hint.base_dish}")
        if hint.size_hint:
            append(f"{hint.brand_hint}{hint.base_dish}{hint.size_hint}")
    return values or [raw_query]


__all__ = ["candidate_search_queries"]
