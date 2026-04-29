from __future__ import annotations
from typing import Any
from ...schemas import EstimateRequest
from .web_search_port import WebSearchPort
from .evidence_normalizer import (
    infer_variant_type, _evidence_id_for_item, source_tier_for_item,
    infer_brand_hint, infer_query_alignment, infer_candidate_relationship,
    retrieval_lane_for_item, infer_source_officialness, source_class_for_item,
    infer_evidence_tier
)
from .context_normalizer import lookup_key, lookup_tokens, normalize_text
from .evidence_eligibility import evaluate_candidate_eligibility, summarize_eligibility_results


def normalize_tool_evidence(items: list[dict[str, Any]], *, source_type: str, query: str, limit: int = 5) -> list[dict[str, Any]]:
    normalized: list[dict[str, Any]] = []
    for item in items[:limit]:
        evidence_id = str(item.get("evidence_id") or _evidence_id_for_item(item, query=query))
        source_class = source_class_for_item(item)
        source_tier = str(item.get("source_tier") or source_tier_for_item(item))
        eligibility = evaluate_candidate_eligibility(item, query=query)
        normalized.append(
            {
                "evidence_id": evidence_id,
                "source_type": source_type,
                "source_class": source_class,
                "source_tier": source_tier,
                "evidence_tier": str(item.get("evidence_tier") or eligibility["evidence_tier"] or infer_evidence_tier(item, query=query)),
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
                "source_officialness": str(item.get("source_officialness") or item.get("officialness") or "unknown"),
                "customization_slots_present": list(item.get("customization_slots_present") or []),
                "channel_detected": str(item.get("channel_detected") or ""),
                "brand_detected": str(item.get("brand_detected") or ""),
                "nutrition_fields_present": list(item.get("nutrition_fields_present") or []),
                "identity_confidence": str(eligibility.get("identity_confidence") or item.get("identity_confidence") or ""),
                "applicability_confidence": str(eligibility.get("applicability_confidence") or item.get("applicability_confidence") or "unknown"),
                "high_variance_family": bool(eligibility.get("high_variance_family")),
                "blocking_customization_slots": list(eligibility.get("blocking_customization_slots") or []),
                "why_not_exact": list(eligibility.get("why_not_exact") or []),
                "stop_reason": str(eligibility.get("stop_reason") or ""),
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
        eligibility = evaluate_candidate_eligibility(item, query=query)
        blocks.append(
            {
                "evidence_id": evidence_id,
                "source_tier": source_tier,
                "evidence_tier": str(item.get("evidence_tier") or eligibility["evidence_tier"] or infer_evidence_tier(item, query=query)),
                "source_class": source_class,
                "origin_channel": "search" if source_class in {"web_search_official", "doc_read_fallback"} else "local_db",
                "title": str(item.get("title") or item.get("name") or ""),
                "brand": str(item.get("brand") or ""),
                "identity_confidence": str(eligibility.get("identity_confidence") or item.get("identity_confidence") or item.get("match_confidence") or "none"),
                "applicability_confidence": str(eligibility.get("applicability_confidence") or item.get("applicability_confidence") or "unknown"),
                "brand_hint": str(item.get("brand_hint") or infer_brand_hint(item, query=query)),
                "query_alignment": str(item.get("query_alignment") or infer_query_alignment(item, query=query)),
                "variant_type": str(item.get("variant_type") or infer_variant_type(item, query=query)),
                "candidate_relationship": str(item.get("candidate_relationship") or infer_candidate_relationship(item, query=query)),
                "retrieval_lane": retrieval_lane_for_item(item),
                "evidence_role": str(item.get("evidence_role") or "unknown"),
                "record_role": str(item.get("record_role") or "unknown"),
                "match_path": str(item.get("match_path") or ""),
                "serving_basis": str(item.get("serving_basis") or item.get("portion_basis") or item.get("serving_size") or ""),
                "channel_detected": str(item.get("channel_detected") or ""),
                "high_variance_family": bool(eligibility.get("high_variance_family")),
                "blocking_customization_slots": list(eligibility.get("blocking_customization_slots") or []),
                "why_not_exact": list(eligibility.get("why_not_exact") or []),
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

def tool_availability(request: EstimateRequest, *, search_port: WebSearchPort | None) -> list[str]:
    tools = ["resolve_exact_item", "get_meal_calibration", "resolve_ingredient_anchors"]
    if request.allow_search and search_port is not None:
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
            "evidence_tier": infer_evidence_tier(
                {"source_class": source_class, "identity_confidence": identity_confidence},
                query=query
            ),
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
        block.update(evaluate_candidate_eligibility(block, query=identity_target or query))
        blocks.append(block)
    return blocks

def _observe_search_results(*, query: str, results: list[dict[str, Any]], identity_target: str) -> dict[str, Any]:
    identity_key = lookup_key(identity_target or query)
    identity_tokens = set(lookup_tokens(identity_target or query))
    official_count = sum(1 for item in results if str(item.get("source_class") or "") == "web_search_official")
    identity_hits = 0
    serving_basis_coverage = 0
    customization_coverage = 0
    for item in results:
        haystack = lookup_key(" ".join([str(item.get("title") or ""), str(item.get("snippet") or ""), str(item.get("url") or "")]))
        title_tokens = set(lookup_tokens(str(item.get("title") or "")))
        if (identity_key and identity_key in haystack) or len(identity_tokens.intersection(title_tokens)) >= 2:
            identity_hits += 1
        if str(item.get("serving_basis") or "").strip() and str(item.get("serving_basis") or "").strip() != "unknown":
            serving_basis_coverage += 1
        if list(item.get("customization_slots_present") or []):
            customization_coverage += 1
    eligibility = summarize_eligibility_results(results, query=identity_target or query)
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
        "serving_basis_coverage": serving_basis_coverage,
        "customization_coverage": customization_coverage,
        "coverage_status": coverage_status,
        "provisional_eligibility_result": eligibility["provisional_eligibility"],
        "high_variance_family": eligibility["high_variance_family"],
        "why_not_exact": eligibility["why_not_exact"],
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


def classify_retrieval_query(*, query: str, identity_target: str = "") -> str:
    haystack = normalize_text(f"{query} {identity_target}").lower()
    if any(token in haystack for token in ("7-11", "familymart", "麥當勞", "mcdonald", "starbucks", "coco", "50嵐", "五十嵐", "八方雲集")):
        return "branded_exact_like"
    return "generic"


def retrieval_attempt_budget(*, query: str, identity_target: str = "") -> int:
    return 4 if classify_retrieval_query(query=query, identity_target=identity_target) == "branded_exact_like" else 3
