from __future__ import annotations

from typing import Any
from .evidence_eligibility import evaluate_candidate_eligibility

def source_class_for_item(item: dict[str, Any]) -> str:
    return str(item.get("source_class") or item.get("source_type") or "unknown")

def source_tier_for_item(item: dict[str, Any]) -> str:
    source_class = source_class_for_item(item)
    if source_class == "exact_item_db":
        return "tier_1_exact_verified"
    if source_class in {"recent_turns", "session_summary", "durable_memory"}:
        return "tier_2_context_verified"
    if source_class in {"base_nutrition_db", "meal_template_db"}:
        return "tier_3_anchor_prior"
    if source_class in {"doc_read_fallback", "web_search_official", "web_search_nonexact"}:
        return "tier_4_web_nonexact"
    return "tier_5_model_context"

def infer_evidence_tier(item: dict[str, Any], *, query: str = "") -> str:
    """Classify evidence with generalized eligibility policy instead of source-only shortcuts."""
    return str(evaluate_candidate_eligibility(item, query=query).get("evidence_tier") or "unusable")

import re
import hashlib
from .context_normalizer import lookup_key, lookup_tokens, normalize_text

_NUTRITION_SIGNAL_HINTS = ("nutrition", "nutrition facts", "kcal", "calories", "熱量", "營養")
_BRAND_HINT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("7-11", "7-11"), ('mcdonald', 'mcdonalds'), ('麥當勞', 'mcdonalds'),
    ('kfc', 'kfc'), ('肯德基', 'kfc'), ('burger king', 'burger_king'), ('漢堡王', 'burger_king'),
    ('starbucks', 'starbucks'), ('星巴克', 'starbucks'), ('subway', 'subway'), ('賽百味', 'subway'),
    ('mos', 'mos_burger'), ('摩斯', 'mos_burger'), ('sukiya', 'sukiya'), ('すき家', 'sukiya'),
    ('matsuya', 'matsuya'), ('松屋', 'matsuya'), ('yoshinoya', 'yoshinoya'), ('吉野家', 'yoshinoya'),
    ('kurasushi', 'kurasushi'), ('藏壽司', 'kurasushi'), ('sushiro', 'sushiro'), ('壽司郎', 'sushiro'),
    ('costco', 'costco'), ('好市多', 'costco'), ('ikea', 'ikea'), ('宜家', 'ikea'),
    ('seven_eleven', '7-11'), ('7-11', '7-11'), ('7-eleven', '7-11'), ('family_mart', 'family_mart'),
    ('全家', 'family_mart'), ('hi-life', 'hi-life'), ('萊爾富', 'hi-life'), ('ok_mart', 'ok_mart'),
    ('ok超商', 'ok_mart'), ('pxmart', 'pxmart'), ('全聯', 'pxmart'), ('carrefour', 'carrefour'),
    ('家樂福', 'carrefour'),
)

def infer_variant_type(item: dict[str, Any], *, query: str = "") -> str:
    source_class = source_class_for_item(item)
    title = normalize_text(str(item.get("title") or item.get("name") or ""))
    haystack = " ".join(
        [
            title,
            " ".join(str(alias) for alias in item.get("aliases", []) if str(alias).strip()),
            str(item.get("brand") or ""),
        ]
    )
    lowered = haystack.lower()
    if source_class == "exact_item_db":
        provenance_text = " ".join(
            [
                str((item.get("provenance") or {}).get("source_url") or ""),
                str((item.get("provenance") or {}).get("source_name") or ""),
                str(item.get("source_note") or ""),
            ]
        ).lower()
        if any(token.lower() in lowered or token.lower() in provenance_text for token in _PACKAGED_RETAIL_SOURCE_HINTS):
            return "packaged_retail"
        if any(token.lower() in lowered for token in _FLAVOR_VARIANT_TOKENS):
            return "flavored_sibling"
        if str(item.get("match_path") or "") in {"exact_title", "exact_alias", "brand_plus_core_token"}:
            return "core_default"
        return "same_family_variant"
    if source_class == "base_nutrition_db" and str(item.get("evidence_role") or "") == "dish_prior":
        return "class_prior"
    if source_class == "web_search_official":
        return "official_candidate"
    return "untyped"
def infer_candidate_relationship(item: dict[str, Any], *, query: str = "") -> str:
    variant_type = infer_variant_type(item, query=query)
    if variant_type == "flavored_sibling":
        return "sibling_of_core_item"
    if variant_type == "packaged_retail":
        return "retail_variant_of_generic_class"
    if variant_type == "core_default":
        return "default_same_item_candidate"
    if variant_type == "class_prior":
        return "generic_class_anchor"
    return "independent_candidate"
def infer_brand_hint(item: dict[str, Any], *, query: str = "") -> str:
    del query
    brand = normalize_text(str(item.get("brand") or ""))
    if brand:
        return brand
    haystack = " ".join(
        [
            str(item.get("title") or item.get("name") or ""),
            str((item.get("provenance") or {}).get("source_name") or ""),
            str((item.get("provenance") or {}).get("source_url") or ""),
            str(item.get("source_note") or ""),
            str(item.get("url") or ""),
        ]
    ).lower()
    for token, label in _BRAND_HINT_PATTERNS:
        if token.lower() in haystack:
            return label
    return ""
def infer_query_alignment(item: dict[str, Any], *, query: str = "") -> str:
    query_key = lookup_key(query)
    if not query_key:
        return "unknown"
    title_key = lookup_key(str(item.get("title") or item.get("name") or ""))
    if title_key and title_key == query_key:
        return "exact_title"
    aliases = [lookup_key(str(alias)) for alias in item.get("aliases", []) if str(alias).strip()]
    if query_key in aliases:
        return "exact_alias"
    if title_key and (query_key in title_key or title_key in query_key):
        return "partial_title"
    return "weak"
def infer_source_officialness(item: dict[str, Any], *, query: str = "") -> str:
    url = str(item.get("url") or "").strip().lower()
    title = normalize_text(str(item.get("title") or item.get("name") or "")).lower()
    snippet = normalize_text(str(item.get("snippet") or item.get("summary") or "")).lower()
    haystack = " ".join([url, title, snippet])
    query_tokens = set(lookup_tokens(query))
    title_tokens = set(lookup_tokens(title))
    token_overlap = len(query_tokens.intersection(title_tokens))
    if any(token in haystack for token in _NONOFFICIAL_SEARCH_HINTS):
        return "nonofficial"
    if url and any(token in haystack for token in ("official", "官方", "menu", "菜單", ".gov.", ".gov.tw")):
        return "official"
    if (
        url
        and any(token in haystack for token in _NUTRITION_SIGNAL_HINTS)
        and any(token in url for token in ("product", "nutrition", ".tw", ".jp", ".hk", ".com"))
        and (infer_brand_hint(item, query=query) or token_overlap >= 2 or "product" in url or "nutrition" in url)
    ):
        return "official"
    if "營養" in title or "官方" in title:
        return "official"
    if url and "nutrition" in url:
        return "official"
    return "unknown"
def _evidence_id_for_item(item: dict[str, Any], *, query: str = "") -> str:
    stable = "||".join(
        [
            str(item.get("title") or item.get("name") or ""),
            str(item.get("brand") or ""),
            str(item.get("url") or ""),
            str(item.get("source_class") or item.get("source_type") or ""),
            str(query or ""),
        ]
    )
    digest = hashlib.md5(stable.encode("utf-8", errors="ignore")).hexdigest()[:10]
    prefix = "EV"
    return f"{prefix}_{digest}"
def to_evidence_candidate(item: dict[str, Any], *, selected: bool = False, drop_reason: str | None = None) -> dict[str, Any]:
    return {
        "evidence_id": str(item.get("evidence_id") or _evidence_id_for_item(item)),
        "title": str(item.get("title") or item.get("name") or ""),
        "source_class": source_class_for_item(item),
        "source_tier": str(item.get("source_tier") or source_tier_for_item(item)),
        "brand_hint": str(item.get("brand_hint") or infer_brand_hint(item)),
        "query_alignment": str(item.get("query_alignment") or infer_query_alignment(item)),
        "variant_type": str(item.get("variant_type") or infer_variant_type(item)),
        "candidate_relationship": str(item.get("candidate_relationship") or infer_candidate_relationship(item)),
        "retrieval_lane": retrieval_lane_for_item(item),
        "record_role": str(item.get("record_role") or "unknown"),
        "evidence_role": str(item.get("evidence_role") or "unknown"),
        "identity_confidence": str(item.get("identity_confidence") or item.get("match_confidence") or "none"),
        "portion_basis_quality": str(item.get("portion_basis_quality") or "unknown"),
        "provenance": dict(item.get("provenance") or {}),
        "conflict_status": str(item.get("conflict_status") or "none"),
        "selected": selected,
        "drop_reason": drop_reason,
    }
def _dedupe_texts(values: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for value in values:
        cleaned = normalize_text(str(value))
        if not cleaned:
            continue
        key = lookup_key(cleaned)
        if not key or key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered
def _sanitize_component_phrase(text: str) -> str:
    cleaned = normalize_text(text)
    if not cleaned:
        return ""
    cleaned = re.sub(r"^(?:\u6211(?:\u65e9\u9910|\u5348\u9910|\u665a\u9910)?\u5403|(?:\u65e9\u9910|\u5348\u9910|\u665a\u9910)\u5403)", "", cleaned)
    cleaned = re.sub(r"\b\d+\s*x\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\bx\s*\d+\b", " ", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\s+", " ", cleaned).strip(" ,")
    return cleaned
def _looks_like_store_header(component: str, remaining: list[str]) -> bool:
    cleaned = normalize_text(component).lower()
    if not cleaned or len(remaining) < 2:
        return False
    return any(cleaned.endswith(suffix) for suffix in _STORE_HINT_SUFFIXES)
def infer_expected_components(*, user_input: str, manager_foods: list[str] | None = None) -> list[str]:
    expected = _dedupe_texts([_sanitize_component_phrase(item) for item in (manager_foods or [])])
    if expected:
        return expected
    text = normalize_text(user_input)
    if not text:
        return []
    raw_components: list[str] = []
    quantity_matches = list(re.finditer(r"\b\d+\s*x\b", text, flags=re.IGNORECASE))
    if quantity_matches:
        previous_end = 0
        for match in quantity_matches:
            segment = text[previous_end:match.start()].strip()
            if segment:
                raw_components.append(segment)
            previous_end = match.end()
        tail = text[previous_end:].strip()
        if tail:
            raw_components.append(tail)
    else:
        split_ready = re.sub(r"加(?!大|小|量|價|倍)", " + ", text)
        parts = re.split(r"(?:,|/| with | and |\+)", split_ready, flags=re.IGNORECASE)
        raw_components = [part for part in parts if normalize_text(part)]

    expanded_components: list[str] = []
    for part in raw_components:
        cleaned_part = normalize_text(part)
        if not cleaned_part:
            continue
        spaced_subparts = [segment.strip() for segment in cleaned_part.split(" ") if segment.strip()]
        if len(spaced_subparts) >= 2 and all(re.search(r"[\u4e00-\u9fff]", segment) for segment in spaced_subparts):
            expanded_components.extend(spaced_subparts)
        else:
            expanded_components.append(cleaned_part)
    raw_components = expanded_components
    if raw_components and len(raw_components) >= 4 and _looks_like_store_header(raw_components[0], raw_components[1:]):
        raw_components = raw_components[1:]
    return _dedupe_texts([_sanitize_component_phrase(part) for part in raw_components if _sanitize_component_phrase(part)])
def infer_store_hint(user_input: str) -> str:
    components = infer_expected_components(user_input=user_input, manager_foods=None)
    if components:
        return ""
    text = normalize_text(user_input)
    return text if any(text.lower().endswith(suffix) for suffix in _STORE_HINT_SUFFIXES) else ""
def retrieval_lane_for_item(item: dict[str, Any]) -> str:
    explicit = str(item.get("retrieval_lane") or "").strip()
    if explicit:
        return explicit
    evidence_role = str(item.get("evidence_role") or "")
    source_class = source_class_for_item(item)
    if evidence_role == "exact_truth" and source_class == "exact_item_db":
        return "exact_lane"
    if evidence_role in {"ingredient_anchor", "dish_prior"}:
        return "anchor_lane"
    if source_class == "meal_template_db":
        return "template_lane"
    return "support_lane"
def split_evidence_lanes(items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    lanes: dict[str, list[dict[str, Any]]] = {
        "exact_lane": [],
        "anchor_lane": [],
        "template_lane": [],
        "support_lane": [],
    }
    for item in items:
        lanes.setdefault(retrieval_lane_for_item(item), []).append(item)
    return lanes
_FLAVOR_VARIANT_TOKENS = (
    "太妃",
    "白巧克力",
    "馥郁",
    "福吉茶",
    "紅茶那堤",
    "伯爵茶",
    "黑糖",
    "草莓",
    "抹茶",
    "巧克力",
    "榛果",
    "香草",
    "焦糖",
    "蒙布朗",
    "風味",
    "特選",
)

_PACKAGED_RETAIL_SOURCE_HINTS = (
    "foodtracer.health.ntpc.gov.tw",
    "nutrition label",
    "營養標示",
    "鋁",
    "罐",
    "瓶",
    "ml",
)

_NONOFFICIAL_SEARCH_HINTS = (
    "fatsecret",
    "eatthismuch",
    "momo",
    "pchome",
    "tiktok",
    "facebook",
    "instagram",
    "youtube",
)

_NUTRITION_SIGNAL_HINTS = ("nutrition", "nutrition facts", "kcal", "calories", "熱量", "營養")

_STORE_HINT_SUFFIXES = (
    "breakfast shop",
    "familymart",
    "7-11",
    "starbucks",
    "mcdonalds",
)
