from __future__ import annotations

from typing import Any

from ..search.exact_item_lookup import resolve_exact_item_fts
from .knowledge_loader import _exact_item_cards
from .knowledge_lookup_normalizer import (
    _expand_aliases,
    _lookup_key,
    _normalize_lower,
    _normalize_tokens,
    _parse_kcal_band_value,
)
from .knowledge_scoring_policy import _score_doc


def _exact_card_to_candidate(card: dict[str, Any]) -> dict[str, Any]:
    kcal_value = _parse_kcal_band_value(card.get("kcal")) or _parse_kcal_band_value(card.get("label_kcal"))
    if kcal_value is None:
        kcal_value = _parse_kcal_band_value(card.get("kcal_band"))
    aliases = [str(item).strip() for item in card.get("aliases", []) if str(item).strip()]
    title = str(card.get("title") or "").strip()
    brand = str(card.get("brand") or "").strip()
    return {
        "item_id": str(card.get("card_id") or card.get("id") or card.get("item_id") or ""),
        "title": title,
        "aliases": _expand_aliases(title=title, aliases=aliases, brand=brand),
        "brand": brand,
        "label_kcal": kcal_value,
        "label_macros": {
            "protein_g": float(card.get("protein_g") or 0),
            "carb_g": float(card.get("carb_g") or 0),
            "fat_g": float(card.get("fat_g") or 0),
        },
        "serving_basis": str(card.get("serving_basis") or card.get("serving_size") or card.get("portion_notes") or ""),
        "match_confidence": "medium",
        "source": "exact_item_db",
        "source_type": str(card.get("source_type") or "exact_item_card"),
        "source_class": "exact_item_db",
        "evidence_role": "exact_truth",
        "record_role": "exact_item",
        "identity_confidence": "medium",
        "portion_basis_quality": "strong",
        "estimate_eligibility": "exact",
        "macro_completeness": "complete",
        "provenance": {
            "source_type": str(card.get("source_type") or "exact_item_card"),
            "source_name": title,
            "source_url": str(card.get("source_url") or ""),
        },
        "source_note": str(card.get("source_note") or ""),
        "protein_g": float(card.get("protein_g") or 0),
        "carb_g": float(card.get("carb_g") or 0),
        "fat_g": float(card.get("fat_g") or 0),
        "kcal": kcal_value,
    }


def _exact_query_alignment(*, query: str, title: str, aliases: list[str]) -> str:
    query_key = _lookup_key(query)
    title_key = _lookup_key(title)
    alias_keys = {_lookup_key(alias) for alias in aliases if _lookup_key(alias)}
    if query_key and title_key and query_key == title_key:
        return "exact_title"
    if query_key and query_key in alias_keys:
        return "exact_alias"
    if query_key and title_key and (query_key in title_key or title_key in query_key):
        return "partial_title"
    return "weak"


def _exact_variant_type(candidate: dict[str, Any]) -> str:
    title = _normalize_lower(str(candidate.get("title") or ""))
    source_note = _normalize_lower(str(candidate.get("source_note") or ""))
    source_url = _normalize_lower(str((candidate.get("provenance") or {}).get("source_url") or candidate.get("source_url") or ""))
    combined = " ".join([title, source_note, source_url])
    if any(token in combined for token in ("ml", "nutrition label", "foodtracer", "營養標示", "瓶", "罐", "pack", "packaged", "bottle", "can")):
        return "packaged_retail"
    if any(token in combined for token in ("焦糖", "草莓", "抹茶", "榛果", "香草", "太妃", "風味", "限定", "flavor", "flavored", "seasonal")):
        return "flavored_sibling"
    return "core_default"


def _exact_candidate_relationship(variant_type: str) -> str:
    if variant_type == "packaged_retail":
        return "retail_variant_of_generic_class"
    if variant_type == "flavored_sibling":
        return "sibling_of_core_item"
    return "default_same_item_candidate"


def _fallback_exact_query_score(candidate: dict[str, Any], *, query: str) -> int:
    query_text = _normalize_lower(query)
    title = _normalize_lower(str(candidate.get("title") or ""))
    aliases = [_normalize_lower(str(item)) for item in candidate.get("aliases", []) if str(item).strip()]
    brand = _normalize_lower(str(candidate.get("brand") or ""))

    score = 0
    if title and title in query_text:
        score += 40
    for alias in aliases:
        if alias and alias in query_text:
            score += 50
        elif alias and query_text in alias:
            score += 20
    if brand and brand in query_text:
        score += 20
    if "冰" in query_text and any(token in " ".join([title, *aliases]) for token in ("冰", "iced", "cold")):
        score += 10
    if "熱" in query_text and any(token in " ".join([title, *aliases]) for token in ("熱", "hot")):
        score += 10
    if "大杯" in query_text and any(token in " ".join([title, *aliases]) for token in ("大杯", "grande", "large")):
        score += 8
    if "中杯" in query_text and any(token in " ".join([title, *aliases]) for token in ("中杯", "tall", "medium")):
        score += 8
    return score


def _exact_identity_gate(candidate: dict[str, Any], *, query: str) -> bool:
    query_alignment = str(candidate.get("query_alignment") or "weak")
    identity_confidence = str(candidate.get("identity_confidence") or candidate.get("match_confidence") or "none")
    variant_type = str(candidate.get("variant_type") or "core_default")
    if query_alignment not in {"exact_title", "exact_alias", "partial_title"}:
        return False
    if variant_type == "packaged_retail" and query_alignment == "weak":
        return False
    if identity_confidence == "none":
        return False

    query_text = _normalize_lower(query)
    if variant_type == "packaged_retail" and not any(token in query_text for token in ("ml", "瓶", "罐", "包", "pack", "bottle", "can")):
        return query_alignment in {"exact_title", "exact_alias", "partial_title"} and any(
            token in query_text for token in ("7-11", "全家", "familymart", "超商", "starbucks", "mcdonald", "mos")
        )
    return True


def _augment_exact_candidate(candidate: dict[str, Any], *, query: str, required_slots: list[str] | None = None) -> dict[str, Any]:
    title = str(candidate.get("title") or "")
    aliases = [str(item) for item in candidate.get("aliases", []) if str(item).strip()]
    query_alignment = _exact_query_alignment(query=query, title=title, aliases=aliases)
    variant_type = _exact_variant_type(candidate)
    identity_confidence = str(candidate.get("identity_confidence") or candidate.get("match_confidence") or "none")
    if query_alignment in {"exact_title", "exact_alias"} and identity_confidence == "medium":
        identity_confidence = "high"
    return candidate | {
        "query_alignment": query_alignment,
        "variant_type": variant_type,
        "candidate_relationship": _exact_candidate_relationship(variant_type),
        "identity_confidence": identity_confidence,
        "tool_name": "resolve_exact_item",
        "required_slots": list(required_slots or []),
        "retrieval_lane": "exact_lane",
    }


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
    if not raw_candidates:
        query_tokens = _normalize_tokens(search_query)
        fallback_scored: list[tuple[int, dict[str, Any]]] = []
        for card in _exact_item_cards():
            candidate = _exact_card_to_candidate(card)
            score, match_meta = _score_doc(candidate, search_query, search_query, query_tokens, query_tokens, [])
            if score <= 0:
                score = _fallback_exact_query_score(candidate, query=search_query)
                if score > 0:
                    match_meta = {
                        "match_confidence": "medium" if score >= 40 else "low",
                        "match_path": "fallback_alias_contains",
                        "brand_conflict": False,
                    }
            if score <= 0:
                continue
            fallback_scored.append((score, candidate | match_meta))
        fallback_scored.sort(key=lambda item: item[0], reverse=True)
        raw_candidates = [item for _, item in fallback_scored[: max(limit * 2, 6)]]

    exact_candidates: list[dict[str, Any]] = []
    for candidate in raw_candidates:
        merged_aliases = [str(item) for item in candidate.get("aliases", []) if str(item).strip()]
        if not merged_aliases:
            merged_aliases = [str(candidate.get("title") or "")]
        augmented = _augment_exact_candidate(
            candidate | {"aliases": merged_aliases},
            query=search_query,
            required_slots=required_slots,
        )
        if not _exact_identity_gate(augmented, query=search_query):
            continue
        exact_candidates.append(augmented)
        if len(exact_candidates) >= limit:
            break
    return exact_candidates


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
