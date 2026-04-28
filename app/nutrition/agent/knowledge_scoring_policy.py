from __future__ import annotations

from typing import Any

from .knowledge_doc_factory import load_retrieval_documents
from .knowledge_exact_item_signals import _exact_item_brand_keys, _exact_item_signal_tokens
from .knowledge_lookup_normalizer import _lookup_key, _normalize_tokens


_MODIFIER_TOKENS = {
    "冰",
    "熱",
    "冷",
    "大杯",
    "中杯",
    "小杯",
    "去冰",
    "微冰",
    "少冰",
    "正常冰",
    "無糖",
    "微糖",
    "半糖",
    "少糖",
    "全糖",
    "珍珠",
    "奶蓋",
}


def _match_metadata(doc: dict[str, Any], query: str, user_input: str, query_tokens: list[str]) -> dict[str, Any]:
    query_key = _lookup_key(query)
    user_key = _lookup_key(user_input)
    title_key = _lookup_key(str(doc.get("title", "")))
    alias_keys = {_lookup_key(item) for item in doc.get("aliases", []) if _lookup_key(item)}
    brand_key = _lookup_key(str(doc.get("brand", "")))
    exact_brand_keys = _exact_item_brand_keys()
    query_token_keys = [_lookup_key(t) for t in query_tokens if len(_lookup_key(t)) >= 2]
    user_token_keys = [_lookup_key(t) for t in (_normalize_tokens(user_input) if user_input else []) if len(_lookup_key(t)) >= 2]
    query_brand_keys = {
        key
        for key in exact_brand_keys
        if key
        and (
            key in query_key
            or key in user_key
            or any(len(token) >= 2 and token in key for token in query_token_keys)
            or any(len(token) >= 2 and token in key for token in user_token_keys)
        )
    }
    brand_in_query = bool(
        brand_key
        and (
            brand_key in query_key
            or brand_key in user_key
            or any(len(token) >= 2 and token in brand_key for token in query_token_keys)
            or any(len(token) >= 2 and token in brand_key for token in user_token_keys)
        )
    )

    if title_key and (query_key == title_key or user_key == title_key):
        return {"match_confidence": "high", "match_path": "exact_title", "brand_conflict": False}
    if (query_key and query_key in alias_keys) or (user_key and user_key in alias_keys):
        return {"match_confidence": "high", "match_path": "exact_alias", "brand_conflict": False}

    if doc.get("source_type") == "exact_item_card" and query_brand_keys and not brand_in_query:
        return {"match_confidence": "none", "match_path": "brand_conflict", "brand_conflict": True}

    title_and_alias_pool = {title_key, *alias_keys}
    title_and_alias_pool.discard("")
    for key in title_and_alias_pool:
        if key and len(key) >= 4 and (
            (query_key and key in query_key)
            or (user_key and key in user_key)
            or (query_key and query_key in key)
            or (user_key and user_key in key)
        ):
            if brand_in_query:
                return {"match_confidence": "high", "match_path": "brand_plus_alias_partial", "brand_conflict": False}
            return {"match_confidence": "medium", "match_path": "alias_partial", "brand_conflict": False}

    if brand_in_query and title_key and any(token and token in title_key for token in query_token_keys):
        return {"match_confidence": "medium", "match_path": "brand_plus_core_token", "brand_conflict": False}

    if query_tokens and any(token in " ".join(doc.get("aliases", [])).lower() for token in query_tokens):
        return {"match_confidence": "low", "match_path": "token_overlap", "brand_conflict": False}

    return {"match_confidence": "none", "match_path": "no_match", "brand_conflict": False}


def _modifier_alignment_score(*, query: str, user_input: str, doc: dict[str, Any]) -> int:
    haystack = " ".join(
        [
            str(doc.get("title", "")),
            " ".join(str(item) for item in doc.get("aliases", []) if str(item).strip()),
        ]
    )
    query_text = f"{query} {user_input}"
    score = 0
    query_has_ice = any(token in query_text for token in ("冰", "iced", "cold"))
    query_has_hot = any(token in query_text for token in ("熱", "hot"))
    doc_has_ice = any(token in haystack for token in ("冰", "iced", "cold"))
    doc_has_hot = any(token in haystack for token in ("熱", "hot"))

    if query_has_ice and doc_has_ice:
        score += 10
    if query_has_hot and doc_has_hot:
        score += 10
    if query_has_ice and doc_has_hot and not doc_has_ice:
        score -= 12
    if query_has_hot and doc_has_ice and not doc_has_hot:
        score -= 12

    for token in _MODIFIER_TOKENS:
        if token in query_text and token in haystack:
            score += 2
    return score


def _score_doc(
    doc: dict[str, Any],
    query: str,
    user_input: str,
    query_tokens: list[str],
    user_tokens: list[str],
    risk_flags: list[str],
) -> tuple[int, dict[str, Any]]:
    haystack = " ".join(
        [
            str(doc.get("title", "")),
            " ".join(doc.get("aliases", [])),
            str(doc.get("brand", "")),
            str(doc.get("category", "")),
            str(doc.get("content", "")),
            " ".join(doc.get("common_components", [])),
            str(doc.get("portion_notes", "")),
            str(doc.get("kcal_band", "")),
        ]
    ).lower()
    score = 0
    title = str(doc.get("title", "")).lower()
    aliases = [item.lower() for item in doc.get("aliases", [])]
    title_alias_query_hits = 0
    exact_title_alias_hits = 0
    query_has_exact_item_signal = any(token in _exact_item_signal_tokens() for token in query_tokens)
    match_meta = _match_metadata(doc, query, user_input, query_tokens)

    for token in query_tokens:
        if token == title or any(token == alias for alias in aliases):
            score += 20
            title_alias_query_hits += 1
            exact_title_alias_hits += 1
        elif token in title:
            score += 10
            title_alias_query_hits += 1
        elif any(token in alias for alias in aliases):
            score += 8
            title_alias_query_hits += 1
        elif token in haystack:
            score += 3

    for token in user_tokens:
        if token in title:
            score += 4
        elif token in haystack:
            score += 1

    if doc.get("source_type") == "exact_item_card":
        if match_meta["brand_conflict"]:
            return 0, match_meta
        confidence_score = {"high": 24, "medium": 12, "low": 1, "none": -8}
        score += confidence_score.get(str(match_meta["match_confidence"]), 0)
        if match_meta["match_confidence"] == "none":
            return 0, match_meta
        if query_has_exact_item_signal:
            score += 8
    elif doc.get("source_type") == "base_nutrition":
        score += 5
        if exact_title_alias_hits:
            score += 8
        if query_has_exact_item_signal and not title_alias_query_hits:
            score -= 10
    elif doc.get("source_type") == "common_dish_prior":
        score += 8
        if exact_title_alias_hits:
            score += 12
        elif title_alias_query_hits:
            score += 6
    elif query_has_exact_item_signal and doc.get("source_type") in {"convenience_archetype", "ramen_shop_profile"}:
        score -= 4

    if doc.get("evidence_role") == "exact_truth":
        score += 6
        score += _modifier_alignment_score(query=query, user_input=user_input, doc=doc)
    if doc.get("category") in risk_flags:
        score += 3
    if doc.get("confidence") == "high":
        score += 2
    return score, match_meta


__all__ = ["load_retrieval_documents", "_match_metadata", "_modifier_alignment_score", "_score_doc"]
