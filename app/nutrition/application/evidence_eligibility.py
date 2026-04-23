from __future__ import annotations

from typing import Any

from .context_normalizer import lookup_key, lookup_tokens, normalize_text


HIGH_VARIANCE_FAMILY_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("generic_milk_tea", ("珍珠奶茶", "奶茶", "bubble tea", "milk tea")),
    ("dumpling_count_required", ("蒸餃", "鍋貼", "水餃", "煎餃", "dumpling", "gyoza")),
    ("luwei", ("滷味", "卤味", "luwei")),
    ("poke", ("poke", "波奇", "波奇碗")),
    ("home_cooked_mixed", ("家常菜", "合菜", "熱炒", "快炒")),
    ("buffet", ("自助餐", "buffet", "便當自助")),
)

PACKAGED_RETAIL_TOKENS = (
    "7-11",
    "7-eleven",
    "familymart",
    "family mart",
    "city cafe",
    "bottle",
    "bottled",
    "can",
    "canned",
    "ml",
)

HANDMADE_DRINK_TOKENS = (
    "大杯",
    "中杯",
    "小杯",
    "半糖",
    "全糖",
    "微糖",
    "無糖",
    "去冰",
    "少冰",
    "正常冰",
    "large",
    "medium",
    "small",
)


def classify_query_family(query: str) -> str | None:
    lowered = normalize_text(query).lower()
    for family, tokens in HIGH_VARIANCE_FAMILY_RULES:
        if any(token.lower() in lowered for token in tokens):
            return family
    return None


def is_high_variance_family(query: str) -> bool:
    return classify_query_family(query) is not None


def _brand_channel_present(text: str) -> bool:
    lowered = normalize_text(text).lower()
    return any(token in lowered for token in PACKAGED_RETAIL_TOKENS)


def _customization_present(text: str) -> bool:
    lowered = normalize_text(text).lower()
    return any(token in lowered for token in HANDMADE_DRINK_TOKENS)


def _identity_confidence_score(value: str) -> int:
    normalized = str(value or "").strip().lower()
    if normalized == "high":
        return 3
    if normalized == "medium":
        return 2
    if normalized == "low":
        return 1
    return 0


def _name_alignment(query: str, title: str) -> str:
    query_key = lookup_key(query)
    title_key = lookup_key(title)
    if not query_key or not title_key:
        return "weak"
    if query_key == title_key:
        return "exact"
    if query_key in title_key or title_key in query_key:
        return "partial"
    overlap = len(set(lookup_tokens(query)).intersection(set(lookup_tokens(title))))
    if overlap >= 2:
        return "partial"
    return "weak"


def evaluate_candidate_eligibility(item: dict[str, Any], *, query: str) -> dict[str, Any]:
    title = str(item.get("title") or item.get("name") or "")
    url = str(item.get("url") or "")
    snippet = str(item.get("snippet") or item.get("summary") or "")
    source_class = str(item.get("source_class") or item.get("source_type") or "unknown")
    source_officialness = str(item.get("source_officialness") or item.get("officialness") or "unknown")
    brand_hint = str(item.get("brand_hint") or item.get("brand_detected") or "").strip()
    serving_basis = str(item.get("serving_basis") or item.get("portion_basis") or "").strip()
    query_alignment = str(item.get("query_alignment") or _name_alignment(query, title))
    identity_confidence = str(item.get("identity_confidence") or item.get("match_confidence") or "unknown")
    query_text = normalize_text(query)
    combined = normalize_text(" ".join([title, snippet, url, brand_hint]))
    family = classify_query_family(query_text)
    high_variance = family is not None
    query_has_packaged_cue = _brand_channel_present(query_text)
    query_has_customization = _customization_present(query_text)
    candidate_packaged = _brand_channel_present(combined)
    candidate_customization = _customization_present(combined)
    packaged_channel_mismatch = high_variance and candidate_packaged and not query_has_packaged_cue
    serving_basis_aligned = bool(serving_basis) or candidate_customization or not high_variance
    customization_slots_present = list(item.get("customization_slots_present") or [])
    customization_aligned = (
        bool(customization_slots_present)
        or candidate_customization
        or not high_variance
        or query_has_customization
    )

    why_not_exact: list[str] = []
    if query_alignment not in {"exact", "partial"}:
        why_not_exact.append("name_alignment_weak")
    if packaged_channel_mismatch:
        why_not_exact.append("packaged_vs_handmade_channel_mismatch")
    if not serving_basis_aligned:
        why_not_exact.append("serving_basis_unknown")
    if not customization_aligned:
        why_not_exact.append("customization_missing")
    if high_variance and source_officialness != "official" and source_class != "exact_item_db":
        why_not_exact.append("high_variance_family_requires_stronger_evidence")

    exact_eligible = (
        source_officialness == "official"
        and not packaged_channel_mismatch
        and _identity_confidence_score(identity_confidence) >= 2
        and query_alignment == "exact"
        and serving_basis_aligned
        and customization_aligned
    ) or (
        source_class == "exact_item_db"
        and not packaged_channel_mismatch
        and _identity_confidence_score(identity_confidence) >= 2
        and query_alignment in {"exact", "partial"}
        and serving_basis_aligned
    )

    if exact_eligible:
        eligibility = "exact"
    elif high_variance and packaged_channel_mismatch:
        eligibility = "generic"
    elif _identity_confidence_score(identity_confidence) >= 2 and query_alignment in {"exact", "partial"}:
        eligibility = "near-exact"
    elif source_class in {"base_nutrition_db", "meal_template_db", "web_search_nonexact", "web_search_official"}:
        eligibility = "generic"
    else:
        eligibility = "unusable"

    applicability_confidence = "high"
    if packaged_channel_mismatch or not customization_aligned:
        applicability_confidence = "low"
    elif eligibility in {"near-exact", "generic"}:
        applicability_confidence = "medium"

    return {
        "eligibility": eligibility,
        "evidence_tier": eligibility,
        "identity_confidence": identity_confidence,
        "identity_confidence_score": _identity_confidence_score(identity_confidence),
        "applicability_confidence": applicability_confidence,
        "high_variance_family": high_variance,
        "family_rule": family,
        "brand_detected": brand_hint,
        "query_alignment": query_alignment,
        "channel_mismatch": packaged_channel_mismatch,
        "serving_basis_aligned": serving_basis_aligned,
        "customization_aligned": customization_aligned,
        "blocking_customization_slots": [] if customization_aligned else ["size_or_sugar_or_ice"],
        "why_not_exact": why_not_exact,
        "stop_reason": "eligibility_resolved" if eligibility in {"exact", "near-exact", "generic"} else "unusable_candidate",
    }


def summarize_eligibility_results(items: list[dict[str, Any]], *, query: str) -> dict[str, Any]:
    evaluated = [evaluate_candidate_eligibility(item, query=query) for item in items]
    exact_count = sum(1 for item in evaluated if item["eligibility"] == "exact")
    near_exact_count = sum(1 for item in evaluated if item["eligibility"] == "near-exact")
    generic_count = sum(1 for item in evaluated if item["eligibility"] == "generic")
    top = evaluated[0] if evaluated else {
        "eligibility": "unusable",
        "why_not_exact": ["no_candidates"],
        "high_variance_family": is_high_variance_family(query),
        "family_rule": classify_query_family(query),
    }
    return {
        "candidate_count": len(evaluated),
        "exact_count": exact_count,
        "near_exact_count": near_exact_count,
        "generic_count": generic_count,
        "provisional_eligibility": top["eligibility"],
        "high_variance_family": top.get("high_variance_family", False),
        "family_rule": top.get("family_rule"),
        "why_not_exact": list(top.get("why_not_exact") or []),
    }
