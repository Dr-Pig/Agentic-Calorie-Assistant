from __future__ import annotations

import hashlib
import re
from typing import Any

from ..agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from ..agent.knowledge_packets import resolve_exact_item, resolve_ingredient_anchors, search_local_knowledge
from ..application.context_assembly import canonicalize_lookup_text, lookup_key, lookup_tokens, normalize_text
from ..application.evidence_normalizer import source_class_for_item, source_tier_for_item
from ..schemas import EstimateRequest, TurnIntentResult


def merge_evidence_items(*groups: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for group in groups:
        for item in group:
            key = (
                lookup_key(str(item.get("title") or item.get("name") or "")),
                str(item.get("source_class") or item.get("source_type") or ""),
            )
            if key in seen:
                continue
            seen.add(key)
            merged.append(item)
    return merged


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

_BRAND_HINT_PATTERNS: tuple[tuple[str, str], ...] = (
    ("7-11", "7-11"),
    ("7 eleven", "7-11"),
    ("seven eleven", "7-11"),
    ("familymart", "FamilyMart"),
    ("全家", "FamilyMart"),
    ("mos burger", "MOS Burger"),
    ("摩斯", "MOS Burger"),
    ("starbucks", "Starbucks"),
    ("星巴克", "Starbucks"),
    ("mcdonald", "McDonald's"),
    ("麥當勞", "McDonald's"),
    ("burger king", "Burger King"),
    ("漢堡王", "Burger King"),
    ("subway", "Subway"),
    ("yoshinoya", "Yoshinoya"),
    ("吉野家", "Yoshinoya"),
    ("鷹流", "鷹流"),
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


def build_evidence_bundle(items: list[dict[str, Any]], *, selected_titles: list[str] | None = None) -> dict[str, Any]:
    selected_title_set = {str(title) for title in (selected_titles or []) if str(title).strip()}
    candidates = [to_evidence_candidate(item, selected=str(item.get("title") or "") in selected_title_set) for item in items]
    source_classes = sorted({candidate["source_class"] for candidate in candidates if candidate["source_class"]})
    conflict_count = sum(1 for candidate in candidates if candidate["conflict_status"] == "conflict")
    selected_count = sum(1 for candidate in candidates if candidate["selected"])
    return {
        "candidates": candidates,
        "selected_titles": list(selected_title_set),
        "source_classes": source_classes,
        "conflict_count": conflict_count,
        "selected_count": selected_count,
    }


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


def normalize_tool_evidence(items: list[dict[str, Any]], *, source_type: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items[:limit]:
        evidence_id = str(item.get("evidence_id") or _evidence_id_for_item(item, query=query))
        source_class = source_class_for_item(item)
        source_tier = str(item.get("source_tier") or source_tier_for_item(item))
        normalized.append(
            {
                "evidence_id": evidence_id,
                "source_type": source_type,
                "source_class": source_class,
                "source_tier": source_tier,
                "brand_hint": str(item.get("brand_hint") or infer_brand_hint(item, query=query)),
                "query_alignment": str(item.get("query_alignment") or infer_query_alignment(item, query=query)),
                "variant_type": str(item.get("variant_type") or infer_variant_type(item, query=query)),
                "candidate_relationship": str(item.get("candidate_relationship") or infer_candidate_relationship(item, query=query)),
                "retrieval_lane": retrieval_lane_for_item(item),
                "origin_channel": "search" if source_type in {"search_official_nutrition", "read_official_doc_fragment"} else "local_retrieval",
                "query": query,
                "match_quality": str(
                    item.get("match_quality") or item.get("match_confidence") or item.get("identity_confidence") or "unknown"
                ),
                "top_match": str(item.get("title") or item.get("name") or item.get("packet_id") or ""),
                "source_title": str(item.get("title") or item.get("name") or ""),
                "source_url": str(item.get("url") or ""),
                "source_snippet": str(item.get("snippet") or item.get("summary") or ""),
                "attestation": {
                    "source_tier": source_tier,
                    "source_class": source_class,
                    "origin_channel": "search" if source_type in {"search_official_nutrition", "read_official_doc_fragment"} else "local_retrieval",
                    "query": query,
                },
                "serving_basis": str(item.get("serving_basis") or item.get("portion_basis") or item.get("serving_size") or ""),
                "alternatives": [str(alt) for alt in item.get("alternatives", []) if str(alt).strip()],
                "note": str(item.get("note") or item.get("summary") or item.get("reason") or ""),
                "raw": item,
            }
        )
    return normalized


def build_attested_evidence_blocks(items: list[dict[str, Any]], *, query: str = "", limit: int = 8) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for item in items[:limit]:
        evidence_id = str(item.get("evidence_id") or _evidence_id_for_item(item, query=query))
        source_class = source_class_for_item(item)
        source_tier = str(item.get("source_tier") or source_tier_for_item(item))
        blocks.append(
            {
                "evidence_id": evidence_id,
                "source_tier": source_tier,
                "source_class": source_class,
                "origin_channel": "search" if source_class in {"web_search_official", "doc_read_fallback"} else "local_db",
                "title": str(item.get("title") or item.get("name") or ""),
                "brand": str(item.get("brand") or ""),
                "identity_confidence": str(item.get("identity_confidence") or item.get("match_confidence") or "none"),
                "brand_hint": str(item.get("brand_hint") or infer_brand_hint(item, query=query)),
                "query_alignment": str(item.get("query_alignment") or infer_query_alignment(item, query=query)),
                "variant_type": str(item.get("variant_type") or infer_variant_type(item, query=query)),
                "candidate_relationship": str(item.get("candidate_relationship") or infer_candidate_relationship(item, query=query)),
                "retrieval_lane": retrieval_lane_for_item(item),
                "evidence_role": str(item.get("evidence_role") or "unknown"),
                "record_role": str(item.get("record_role") or "unknown"),
                "match_path": str(item.get("match_path") or ""),
                "serving_basis": str(item.get("serving_basis") or item.get("portion_basis") or item.get("serving_size") or ""),
                "nutrition_payload": {
                    "kcal": item.get("label_kcal") or item.get("kcal"),
                    "label_macros": item.get("label_macros") or item.get("macros") or {},
                },
                "attestation": {
                    "query": query or str(item.get("query") or ""),
                    "source_url": str(item.get("url") or ""),
                    "source_title": str(item.get("title") or item.get("name") or ""),
                    "source_snippet": str(item.get("snippet") or item.get("summary") or ""),
                },
            }
        )
    return blocks


def tool_availability(request: EstimateRequest, *, search_adapter: Any | None) -> list[str]:
    tools = ["resolve_exact_item", "get_meal_calibration", "resolve_ingredient_anchors"]
    if request.allow_search and search_adapter is not None:
        tools.extend(["search_official_nutrition", "read_official_doc_fragment"])
    return tools


def build_tool_candidate_requests(*, query: str, decision_tool_plan: str) -> list[dict[str, Any]]:
    if decision_tool_plan == "none":
        return []
    return [{"tool_name": decision_tool_plan, "query": query}]


def build_tool_result(*, tool_name: str, status: str, reason: str, result_count: int = 0, quality: str = "low") -> dict[str, Any]:
    return {
        "tool_name": tool_name,
        "status": status,
        "reason": reason,
        "result_count": result_count,
        "quality": quality,
    }


def extract_nutrition_table_fragment(search_sources: list[dict[str, Any]], *, item_identity: str) -> list[dict[str, Any]]:
    identity_key = lookup_key(item_identity)
    fragments: list[dict[str, Any]] = []
    for item in search_sources:
        title_key = lookup_key(str(item.get("title") or ""))
        if identity_key and identity_key not in title_key:
            continue
        fragments.append(
            {
                "title": str(item.get("title") or ""),
                "source_type": "official_doc_fragment",
                "snippet": str(item.get("snippet") or ""),
                "url": str(item.get("url") or ""),
            }
        )
    return fragments


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


def extract_search_evidence_blocks(results: list[dict[str, Any]], *, query: str, identity_target: str) -> list[dict[str, Any]]:
    identity_key = lookup_key(identity_target or query)
    identity_tokens = set(lookup_tokens(identity_target or query))
    blocks: list[dict[str, Any]] = []
    for item in results:
        title = str(item.get("title") or item.get("name") or "").strip()
        snippet = str(item.get("snippet") or item.get("summary") or "").strip()
        url = str(item.get("url") or "").strip()
        haystack = lookup_key(" ".join([title, snippet, url]))
        officialness = infer_source_officialness(item, query=query)
        title_tokens = set(lookup_tokens(title))
        token_overlap = len(identity_tokens.intersection(title_tokens))
        if identity_key and identity_key in haystack:
            identity_confidence = "high" if officialness == "official" else "medium"
        elif token_overlap >= 2:
            identity_confidence = "medium"
        else:
            identity_confidence = "low"
        source_class = "web_search_official" if officialness == "official" else "web_search_nonexact"
        block = {
            **item,
            "evidence_id": _evidence_id_for_item(item, query=query),
            "source_class": source_class,
            "source_tier": source_tier_for_item({"source_class": source_class}),
            "identity_confidence": str(item.get("identity_confidence") or identity_confidence),
            "match_quality": str(item.get("match_quality") or identity_confidence),
            "brand_hint": str(item.get("brand_hint") or infer_brand_hint(item, query=query)),
            "query_alignment": str(item.get("query_alignment") or infer_query_alignment(item, query=identity_target or query)),
            "query": query,
            "attestation": {
                "query": query,
                "source_url": url,
                "source_title": title,
                "source_snippet": snippet,
                "officialness": officialness,
            },
            "source_officialness": officialness,
        }
        blocks.append(block)
    return blocks


def _observe_search_results(*, query: str, results: list[dict[str, Any]], identity_target: str) -> dict[str, Any]:
    identity_key = lookup_key(identity_target or query)
    identity_tokens = set(lookup_tokens(identity_target or query))
    official_count = sum(1 for item in results if str(item.get("source_class") or "") == "web_search_official")
    identity_hits = 0
    for item in results:
        haystack = lookup_key(" ".join([str(item.get("title") or ""), str(item.get("snippet") or ""), str(item.get("url") or "")]))
        title_tokens = set(lookup_tokens(str(item.get("title") or "")))
        if (identity_key and identity_key in haystack) or len(identity_tokens.intersection(title_tokens)) >= 2:
            identity_hits += 1
    if official_count and identity_hits:
        quality = "high"
        coverage_status = "official_identity_match"
    elif official_count or identity_hits:
        quality = "medium"
        coverage_status = "partial_search_grounding"
    else:
        quality = "low"
        coverage_status = "search_grounding_weak"
    return {
        "quality": quality,
        "official_count": official_count,
        "official_hit_count": official_count,
        "identity_hits": identity_hits,
        "identity_hit_count": identity_hits,
        "coverage_status": coverage_status,
        "why_not_enough_yet": "" if quality == "high" else (
            "missing official hit and identity match"
            if official_count == 0 and identity_hits == 0
            else "missing official corroboration"
            if official_count == 0
            else "identity match still weak"
        ),
        "needs_refinement": quality != "high",
    }


def _refinement_queries(*, query: str, resolved_query: str, identity_target: str) -> list[str]:
    candidates = [
        resolved_query,
        query,
        f"{identity_target or resolved_query or query} official nutrition",
        f"{identity_target or resolved_query or query} calories official",
        f"{identity_target or resolved_query or query} 營養資訊 官方",
        f"{identity_target or resolved_query or query} 熱量 官方",
        f"{identity_target or resolved_query or query} 營養標示 官方",
        f"{identity_target or resolved_query or query} nutrition facts",
        f"{identity_target or resolved_query or query} 栄養情報",
        f"{identity_target or resolved_query or query} カロリー",
    ]
    seen: set[str] = set()
    ordered: list[str] = []
    for candidate in candidates:
        cleaned = normalize_text(candidate)
        if not cleaned:
            continue
        key = cleaned.lower()
        if key in seen:
            continue
        seen.add(key)
        ordered.append(cleaned)
    return ordered[:3]

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


_STORE_HINT_SUFFIXES = (
    "breakfast shop",
    "familymart",
    "7-11",
    "starbucks",
    "mcdonalds",
)


def _looks_like_store_header(component: str, remaining: list[str]) -> bool:
    cleaned = normalize_text(component).lower()
    if not cleaned or len(remaining) < 2:
        return False
    return any(cleaned.endswith(suffix) for suffix in _STORE_HINT_SUFFIXES)


def infer_expected_components(*, user_input: str, planner_foods: list[str] | None = None) -> list[str]:
    expected = _dedupe_texts([_sanitize_component_phrase(item) for item in (planner_foods or [])])
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
    components = infer_expected_components(user_input=user_input, planner_foods=None)
    if components:
        return ""
    text = normalize_text(user_input)
    return text if any(text.lower().endswith(suffix) for suffix in _STORE_HINT_SUFFIXES) else ""


def build_partial_grounding_packet(
    *,
    user_input: str,
    planner_foods: list[str] | None,
    selected_evidence: list[dict[str, Any]],
) -> dict[str, Any]:
    expected_components = infer_expected_components(user_input=user_input, planner_foods=planner_foods)
    store_hint = infer_store_hint(user_input)
    anchored_components: list[dict[str, Any]] = []
    missing_components: list[dict[str, Any]] = []
    lanes = split_evidence_lanes(selected_evidence)
    exact_truth_present = bool(lanes["exact_lane"])

    evidence_haystacks: list[tuple[dict[str, Any], str]] = []
    for item in selected_evidence:
        haystack_parts = [
            str(item.get("title") or item.get("name") or ""),
            *[str(alias) for alias in item.get("aliases", []) if str(alias).strip()],
            *[str(comp) for comp in item.get("common_components", []) if str(comp).strip()],
            str(item.get("brand") or ""),
            str(item.get("content") or ""),
            str(item.get("snippet") or ""),
        ]
        evidence_haystacks.append((item, canonicalize_lookup_text(" ".join(haystack_parts))))

    for index, component in enumerate(expected_components):
        component_key = lookup_key(component)
        matched_item: dict[str, Any] | None = None
        for item, haystack in evidence_haystacks:
            if component_key and component_key in lookup_key(haystack):
                matched_item = item
                break
        if matched_item is not None:
            anchored_components.append(
                {
                    "name": component,
                    "evidence_title": str(matched_item.get("title") or matched_item.get("name") or ""),
                    "evidence_role": str(matched_item.get("evidence_role") or "unknown"),
                    "identity_confidence": str(matched_item.get("identity_confidence") or matched_item.get("match_confidence") or "none"),
                    "source_class": source_class_for_item(matched_item),
                }
            )
        else:
            missing_components.append(
                {
                    "name": component,
                    "importance": "high" if index < 2 else "medium",
                }
            )

    grounded_count = len(anchored_components)
    missing_count = len(missing_components)
    if exact_truth_present:
        grounding_quality = "high"
    elif grounded_count and missing_count:
        grounding_quality = "partial"
    elif grounded_count:
        grounding_quality = "medium"
    else:
        grounding_quality = "low"


    return {
        "expected_components": expected_components,
        "store_hint": store_hint,
        "store_header_removed": bool(store_hint),
        "exact_lane_candidates": summarize_selected_evidence(lanes["exact_lane"], limit=5),
        "anchor_lane_candidates": summarize_selected_evidence(lanes["anchor_lane"], limit=5),
        "template_lane_hits": summarize_selected_evidence(lanes["template_lane"], limit=5),
        "anchored_components": anchored_components,
        "missing_components": missing_components,
        "grounded_component_count": grounded_count,
        "missing_component_count": missing_count,
        "grounding_quality": grounding_quality,
        "exact_truth_present": exact_truth_present,
    }


def build_reasoning_state(
    *,
    user_input: str,
    selected_evidence: list[dict[str, Any]],
    partial_grounding: dict[str, Any] | None = None,
    meal_template_hit: bool = False,
    used_search: bool = False,
    search_query: str | None = None,
    search_quality: Any = None,
    search_attempt_count: int = 0,
) -> dict[str, Any]:
    user_brand_hint = infer_brand_hint({"title": user_input}, query=user_input).strip()
    lanes = split_evidence_lanes(selected_evidence)
    brand_hints = sorted(
        {
            *{
                str(item.get("brand_hint") or infer_brand_hint(item, query=user_input)).strip()
                for item in selected_evidence
                if str(item.get("brand_hint") or infer_brand_hint(item, query=user_input)).strip()
            },
            *([user_brand_hint] if user_brand_hint else []),
        }
    )
    official_evidence_present = any(source_class_for_item(item) == "web_search_official" for item in selected_evidence)
    identity_conflict_present = len(brand_hints) > 1
    missing_components = list((partial_grounding or {}).get("missing_components") or [])
    template_lane_count = len(lanes["template_lane"]) + (1 if meal_template_hit else 0)
    if lanes["exact_lane"]:
        insufficiency = ""
        coverage_status = "exact_available"
    elif lanes["anchor_lane"]:
        insufficiency = "exact lane empty; anchor evidence only"
        coverage_status = "anchor_only"
    elif template_lane_count > 0:
        insufficiency = "only template scaffold evidence available"
        coverage_status = "template_only"
    else:
        insufficiency = "no usable local evidence"
        coverage_status = "empty"
    observation_summary = {
        "official_hit_count": sum(1 for item in selected_evidence if source_class_for_item(item) == "web_search_official"),
        "identity_hit_count": sum(
            1
            for item in selected_evidence
            if str(item.get("identity_confidence") or item.get("match_confidence") or "none") in {"high", "medium"}
        ),
        "top_conflict_type": "brand_conflict" if identity_conflict_present else "none",
        "coverage_status": coverage_status,
        "why_not_enough_yet": insufficiency,
    }
    return {
        "exact_lane_count": len(lanes["exact_lane"]),
        "anchor_lane_count": len(lanes["anchor_lane"]),
        "template_lane_count": template_lane_count,
        "official_evidence_present": official_evidence_present,
        "brand_detected": bool(brand_hints),
        "brand_hints": brand_hints,
        "identity_conflict_present": identity_conflict_present,
        "missing_high_impact_slots": [str(item.get("name") or "") for item in missing_components if str(item.get("importance") or "") == "high"],
        "search_attempt_count": int(search_attempt_count),
        "last_search_quality": search_quality.get("quality") if isinstance(search_quality, dict) else search_quality,
        "last_search_query": search_query,
        "used_search": used_search,
        "why_current_evidence_is_insufficient": insufficiency,
        "observation_summary": observation_summary,
    }


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



async def execute_primary_tool_request(
    *,
    tool_request: str,
    tool_reason: str,
    retrieval_query: str,
    resolved_query: str,
    planner_result: TurnIntentResult,
    request: EstimateRequest,
    search_adapter: Any | None,
    executed_tool_calls: list[dict[str, Any]],
    build_tool_result: Any,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None, dict[str, Any] | None]:
    if tool_request == "resolve_exact_item":
        results = resolve_exact_item(resolved_query or retrieval_query, limit=4)
        executed_tool_calls.append(
            build_tool_result(
                tool_name=tool_request,
                status="executed",
                reason=tool_reason or "Primary requested exact item lookup.",
                result_count=len(results),
                quality="high" if results else "low",
            )
        )
        return results, [], None, None
    if tool_request == "resolve_ingredient_anchors":
        foods = list(dict.fromkeys((planner_result.input_signals.get("foods") or []) or [resolved_query or retrieval_query]))
        results = resolve_ingredient_anchors(
            foods,
            portion_hints=planner_result.input_signals.get("portion_clues", []),
            limit=max(6, len(foods)),
        )
        executed_tool_calls.append(
            build_tool_result(
                tool_name=tool_request,
                status="executed",
                reason=tool_reason or "Primary requested ingredient anchors.",
                result_count=len(results),
                quality="medium" if results else "low",
            )
        )
        return results, [], None, None
    if tool_request == "get_meal_calibration":
        packet_id = suggest_calibration_packet(resolved_query or retrieval_query)
        packet = get_meal_calibration(packet_id) if packet_id else None
        results = [packet] if packet else []
        executed_tool_calls.append(
            build_tool_result(
                tool_name=tool_request,
                status="executed" if packet else "not_needed",
                reason=tool_reason or "Primary requested meal calibration.",
                result_count=len(results),
                quality="high" if packet else "low",
            )
        )
        return results, [], None, None
    if tool_request in {"search_official_nutrition", "read_official_doc_fragment"} and search_adapter and request.allow_search:
        search_query = resolved_query or retrieval_query
        identity_target = resolved_query or retrieval_query
        best_query = search_query
        filtered: list[dict[str, Any]] = []
        quality_meta: dict[str, Any] | None = None
        for candidate_query in _refinement_queries(query=retrieval_query, resolved_query=resolved_query, identity_target=identity_target):
            try:
                results = await search_adapter.search(query=candidate_query, limit=5)
            except TypeError:
                results = await search_adapter.search(candidate_query)
            normalized_results = list(results or [])
            base_quality, minimally_filtered = search_result_quality(candidate_query, normalized_results)
            extracted = extract_search_evidence_blocks(minimally_filtered, query=candidate_query, identity_target=identity_target)
            observation = _observe_search_results(query=candidate_query, results=extracted, identity_target=identity_target)
            filtered = extracted
            best_query = candidate_query
            combined_quality = "low"
            if base_quality == "high" and observation["quality"] == "high":
                combined_quality = "high"
            elif base_quality in {"high", "medium"} or observation["quality"] in {"high", "medium"}:
                combined_quality = "medium"
            quality_meta = {
                "quality": combined_quality,
                "observation": observation,
                "extractor_used": True,
                "refinement_queries": _refinement_queries(query=retrieval_query, resolved_query=resolved_query, identity_target=identity_target),
            }
            if not observation["needs_refinement"]:
                break
        executed_tool_calls.append(
            build_tool_result(
                tool_name=tool_request,
                status="executed",
                reason=tool_reason or "Primary requested external nutrition lookup.",
                result_count=len(filtered),
                quality=str((quality_meta or {}).get("quality") or "low"),
            )
        )
        return filtered, filtered, best_query, quality_meta
    executed_tool_calls.append(
        build_tool_result(
            tool_name=tool_request,
            status="not_needed",
            reason=tool_reason or "Tool request unavailable in current runtime.",
            result_count=0,
            quality="low",
        )
    )
    return [], [], None, None
