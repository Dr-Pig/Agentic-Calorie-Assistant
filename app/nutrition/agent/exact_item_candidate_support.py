from __future__ import annotations

from typing import Any

from .knowledge_loader import _exact_item_cards
from .knowledge_lookup_normalizer import (
    _expand_aliases,
    _lookup_key,
    _normalize_lower,
    _normalize_tokens,
    _parse_kcal_band_value,
)
from .knowledge_scoring_policy import _score_doc


def exact_card_to_candidate(card: dict[str, Any]) -> dict[str, Any]:
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


def exact_query_alignment(*, query: str, title: str, aliases: list[str]) -> str:
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


def exact_variant_type(candidate: dict[str, Any]) -> str:
    title = _normalize_lower(str(candidate.get("title") or ""))
    source_note = _normalize_lower(str(candidate.get("source_note") or ""))
    source_url = _normalize_lower(str((candidate.get("provenance") or {}).get("source_url") or candidate.get("source_url") or ""))
    combined = " ".join([title, source_note, source_url])
    combined_tokens = set(_normalize_tokens(combined))
    if any(token in combined for token in ("ml", "nutrition label", "foodtracer", "packaged", "bottle")) or "can" in combined_tokens:
        return "packaged_retail"
    if any(token in combined for token in ("flavor", "flavored", "seasonal", "限定", "風味", "口味")):
        return "flavored_sibling"
    return "core_default"


def exact_candidate_relationship(variant_type: str) -> str:
    if variant_type == "packaged_retail":
        return "retail_variant_of_generic_class"
    if variant_type == "flavored_sibling":
        return "sibling_of_core_item"
    return "default_same_item_candidate"


def fallback_exact_query_score(candidate: dict[str, Any], *, query: str) -> int:
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


def exact_identity_gate(candidate: dict[str, Any], *, query: str) -> bool:
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
    if variant_type == "packaged_retail" and not any(
        token in query_text for token in ("ml", "罐", "瓶", "pack", "bottle", "can")
    ):
        return query_alignment in {"exact_title", "exact_alias", "partial_title"} and any(
            token in query_text for token in ("7-11", "全家", "familymart", "星巴克", "starbucks", "mcdonald", "mos")
        )
    return True


def augment_exact_candidate(candidate: dict[str, Any], *, query: str, required_slots: list[str] | None = None) -> dict[str, Any]:
    title = str(candidate.get("title") or "")
    aliases = [str(item) for item in candidate.get("aliases", []) if str(item).strip()]
    query_alignment = exact_query_alignment(query=query, title=title, aliases=aliases)
    variant_type = exact_variant_type(candidate)
    identity_confidence = str(candidate.get("identity_confidence") or candidate.get("match_confidence") or "none")
    if query_alignment in {"exact_title", "exact_alias"} and identity_confidence == "medium":
        identity_confidence = "high"
    return candidate | {
        "query_alignment": query_alignment,
        "variant_type": variant_type,
        "candidate_relationship": exact_candidate_relationship(variant_type),
        "identity_confidence": identity_confidence,
        "tool_name": "resolve_exact_item",
        "required_slots": list(required_slots or []),
        "retrieval_lane": "exact_lane",
    }


def fallback_exact_candidates(*, search_query: str, required_slots: list[str] | None, limit: int) -> list[dict[str, Any]]:
    query_tokens = _normalize_tokens(search_query)
    fallback_scored: list[tuple[int, dict[str, Any]]] = []
    for card in _exact_item_cards():
        candidate = exact_card_to_candidate(card)
        score, match_meta = _score_doc(candidate, search_query, search_query, query_tokens, query_tokens, [])
        if score <= 0:
            score = fallback_exact_query_score(candidate, query=search_query)
            if score > 0:
                match_meta = {
                    "match_confidence": "medium" if score >= 40 else "low",
                    "match_path": "fallback_alias_contains",
                    "brand_conflict": False,
                }
        if score <= 0:
            continue
        augmented = augment_exact_candidate(
            candidate | match_meta,
            query=search_query,
            required_slots=required_slots,
        )
        if not exact_identity_gate(augmented, query=search_query):
            continue
        fallback_scored.append((score, augmented))
    query_text = _normalize_lower(search_query)

    def _rank(entry: tuple[int, dict[str, Any]]) -> tuple[int, int, int]:
        score, candidate = entry
        brand = _normalize_lower(str(candidate.get("brand") or ""))
        brand_match = 1 if brand and brand in query_text else 0
        exact_alignment = 1 if str(candidate.get("query_alignment") or "") in {"exact_title", "exact_alias"} else 0
        return (exact_alignment, brand_match, score)

    fallback_scored.sort(key=_rank, reverse=True)
    return [item for _, item in fallback_scored[:limit]]
