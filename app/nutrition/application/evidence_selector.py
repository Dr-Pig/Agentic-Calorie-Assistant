from __future__ import annotations
from typing import Any
from .evidence_normalizer import (
    source_class_for_item, infer_source_officialness, split_evidence_lanes,
    retrieval_lane_for_item, _NUTRITION_SIGNAL_HINTS
)
from ..agent.local_knowledge_selector import search_local_knowledge
from .context_normalizer import lookup_key, lookup_tokens


def summarize_selected_evidence(items: list[dict[str, Any]], *, limit: int = 3) -> list[dict[str, Any]]:
    return [
        {
            "title": str(item.get("title") or ""),
            "brand": str(item.get("brand") or ""),
            "source_class": source_class_for_item(item),
            "retrieval_lane": retrieval_lane_for_item(item),
            "identity_confidence": str(item.get("identity_confidence") or item.get("match_confidence") or "none"),
            "evidence_role": str(item.get("evidence_role") or "unknown"),
            "serving_basis": str(item.get("serving_basis") or item.get("portion_basis") or item.get("serving_size") or ""),
            "kcal": item.get("label_kcal") or item.get("kcal"),
            "match_path": str(item.get("match_path") or ""),
            "aliases": [str(alias) for alias in item.get("aliases", []) if str(alias).strip()][:5],
        }
        for item in items[:limit]
    ]

def retrieve_local_knowledge(query: str, *, user_input: str, risk_flags: list[str], limit: int = 4) -> list[dict[str, Any]]:
    del risk_flags
    return search_local_knowledge(query, user_input=user_input, limit=limit)

def retrieval_query_is_usable(query: str) -> bool:
    return bool(lookup_tokens(query)) or bool(lookup_key(query))

def search_result_quality(query: str, results: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    query_key = lookup_key(query)
    query_tokens = set(lookup_tokens(query))
    filtered: list[dict[str, Any]] = []
    official_hits = 0
    identity_hits = 0
    strong_hits = 0
    for item in results:
        if not any(
            str(item.get(field) or "").strip()
            for field in ("title", "name", "snippet", "url", "source_class", "source_type")
        ):
            continue
        haystack = lookup_key(
            " ".join(
                [
                    str(item.get("title") or item.get("name") or ""),
                    str(item.get("snippet") or item.get("summary") or ""),
                    str(item.get("url") or ""),
                ]
            )
        )
        officialness = infer_source_officialness(item, query=query)
        if officialness == "official":
            official_hits += 1
        has_nutrition_signal = any(token in haystack for token in _NUTRITION_SIGNAL_HINTS)
        token_overlap = len(query_tokens.intersection(set(lookup_tokens(str(item.get("title") or item.get("name") or "")))))
        has_identity = (query_key and query_key in haystack) or token_overlap >= 2
        if has_identity:
            identity_hits += 1
        if officialness == "official" and (has_identity or has_nutrition_signal):
            strong_hits += 1
        filtered.append(item)

    if not filtered:
        return "low", []
    if strong_hits > 0:
        return "high", filtered
    if official_hits > 0 or identity_hits > 0:
        return "medium", filtered
    return "low", filtered

def summarize_retrieved_evidence(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "title": str(item.get("title") or item.get("name") or ""),
            "source_class": source_class_for_item(item),
            "evidence_role": str(item.get("evidence_role") or "unknown"),
            "match_confidence": str(item.get("match_confidence") or item.get("identity_confidence") or "none"),
        }
        for item in items[:5]
    ]

def db_hit_type(*, retrieved_knowledge: list[dict[str, Any]], meal_template: dict[str, Any] | None) -> str:
    lanes = split_evidence_lanes(retrieved_knowledge)
    if lanes["exact_lane"]:
        return "exact_truth"
    if lanes["anchor_lane"]:
        return "anchor_truth"
    if meal_template:
        return "meal_template"
    if lanes["template_lane"]:
        return "template_hit"
    if retrieved_knowledge:
        return "retrieved_knowledge"
    return "none"

