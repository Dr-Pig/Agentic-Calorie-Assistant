from __future__ import annotations

from typing import Any

from .knowledge_doc_factory import load_retrieval_documents
from .knowledge_lookup_normalizer import _normalize_tokens
from .knowledge_scoring_policy import _score_doc


def search_local_knowledge(
    query: str,
    *,
    user_input: str = "",
    risk_flags: list[str] | None = None,
    limit: int = 4,
) -> list[dict[str, Any]]:
    docs = load_retrieval_documents()
    query_tokens = _normalize_tokens(query)
    user_tokens = _normalize_tokens(user_input)
    flags = risk_flags or []

    scored: list[tuple[int, dict[str, Any]]] = []
    for doc in docs:
        score, match_meta = _score_doc(doc, query, user_input, query_tokens, user_tokens, flags)
        if score <= 0:
            continue
        scored.append((score, doc | match_meta))

    scored.sort(key=lambda item: item[0], reverse=True)
    normalized_results: list[dict[str, Any]] = []
    for score, doc in scored[:limit]:
        identity_confidence = str(doc.get("match_confidence") or "none")
        if doc.get("source_type") == "common_dish_prior" and identity_confidence == "none":
            title_hits = 0
            title = str(doc.get("title", "")).lower()
            aliases = [str(item).lower() for item in doc.get("aliases", [])]
            for token in query_tokens:
                if token == title or any(token == alias for alias in aliases):
                    title_hits += 2
                elif token in title or any(token in alias for alias in aliases):
                    title_hits += 1
            if title_hits >= 2:
                identity_confidence = "medium"
            elif title_hits == 1:
                identity_confidence = "low"
        normalized_results.append(
            doc
            | {
                "score": score,
                "identity_confidence": identity_confidence,
                "provenance": {
                    "source_type": doc.get("source_type"),
                    "source_url": doc.get("source_url"),
                    "source_name": doc.get("title"),
                },
                "conflict_status": "none" if identity_confidence != "none" else "shadowed",
                "selected": False,
                "drop_reason": None,
            }
        )
    return normalized_results


def resolve_ingredient_anchors(
    component_list: list[str],
    *,
    portion_hints: list[str] | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    query = " ".join(str(item).strip() for item in component_list if str(item).strip())
    anchors = search_local_knowledge(query, user_input=query, limit=limit)
    anchor_candidates: list[dict[str, Any]] = []
    for item in anchors:
        if item.get("evidence_role") not in {"ingredient_anchor", "dish_prior"}:
            continue
        anchor_candidates.append(
            item
            | {
                "tool_name": "resolve_ingredient_anchors",
                "portion_hints": list(portion_hints or []),
                "source_class": item.get("source_class", "base_nutrition_db"),
                "retrieval_lane": "anchor_lane",
            }
        )
    return anchor_candidates


__all__ = ["load_retrieval_documents", "search_local_knowledge", "resolve_ingredient_anchors"]
