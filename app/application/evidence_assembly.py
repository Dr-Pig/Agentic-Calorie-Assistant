from __future__ import annotations

import re
from typing import Any

from ..agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from ..agent.knowledge_packets import resolve_exact_item, resolve_ingredient_anchors, search_local_knowledge
from ..application.context_assembly import canonicalize_lookup_text, lookup_key, lookup_tokens, normalize_text
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


def source_class_for_item(item: dict[str, Any]) -> str:
    return str(item.get("source_class") or item.get("source_type") or "unknown")


def to_evidence_candidate(item: dict[str, Any], *, selected: bool = False, drop_reason: str | None = None) -> dict[str, Any]:
    return {
        "title": str(item.get("title") or item.get("name") or ""),
        "source_class": source_class_for_item(item),
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
        normalized.append(
            {
                "source_type": source_type,
                "query": query,
                "match_quality": str(
                    item.get("match_quality") or item.get("match_confidence") or item.get("identity_confidence") or "unknown"
                ),
                "top_match": str(item.get("title") or item.get("name") or item.get("packet_id") or ""),
                "serving_basis": str(item.get("serving_basis") or item.get("portion_basis") or item.get("serving_size") or ""),
                "alternatives": [str(alt) for alt in item.get("alternatives", []) if str(alt).strip()],
                "note": str(item.get("note") or item.get("summary") or item.get("reason") or ""),
                "raw": item,
            }
        )
    return normalized


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


def pre_rank_evidence_items(items: list[dict[str, Any]], *, query: str, limit: int = 5) -> list[dict[str, Any]]:
    query_tokens = set(lookup_tokens(query))
    query_key = lookup_key(query)
    ranked: list[tuple[int, dict[str, Any]]] = []
    for item in items:
        title = str(item.get("title") or "")
        title_tokens = set(lookup_tokens(title))
        lexical_overlap = len(query_tokens & title_tokens)
        sibling_penalty = -12 if query_key and query_key not in lookup_key(title) and lexical_overlap <= 1 else 0
        source_bonus = {
            "exact_item_db": 40,
            "exact_item_card": 40,
            "web_search_official": 25,
            "base_nutrition": 10,
            "meal_template": 5,
        }.get(source_class_for_item(item), 0)
        ranked.append((source_bonus + lexical_overlap * 10 + sibling_penalty, item))
    ranked.sort(key=lambda pair: pair[0], reverse=True)
    return [item for _, item in ranked[:limit]]


def retrieve_local_knowledge(query: str, *, user_input: str, risk_flags: list[str], limit: int = 4) -> list[dict[str, Any]]:
    del risk_flags
    return search_local_knowledge(query, user_input=user_input, limit=limit)


def retrieval_query_is_usable(query: str) -> bool:
    return bool(lookup_tokens(query)) or bool(lookup_key(query))


def search_result_quality(query: str, results: list[dict[str, Any]]) -> tuple[str, list[dict[str, Any]]]:
    query_lower = normalize_text(query).lower()
    query_tokens = {token for token in re.split(r"\s+", query_lower) if token}
    official_domains = (
        "official",
        ".gov",
        ".edu",
        "mcdonalds",
        "starbucks",
        "7-11",
        "familymart",
        "pocari",
        "uni-president",
    )

    scored: list[tuple[tuple[int, int, int, int], dict[str, Any]]] = []
    for item in results:
        title = str(item.get("title") or "")
        snippet = str(item.get("snippet") or "")
        url = str(item.get("url") or "").lower()
        source_class = str(item.get("source_class") or item.get("source_type") or "").lower()
        haystack = f"{title} {snippet}".lower()
        token_hits = sum(1 for token in query_tokens if token in haystack)
        officialish = any(domain in url for domain in official_domains) or "official" in source_class
        nutritionish = any(term in haystack for term in ("nutrition", "營養", "熱量", "kcal", "calories"))
        calculatorish = any(term in url for term in ("calculator", "convert", "calculateme"))
        if token_hits <= 0 and not officialish and not nutritionish:
            continue
        score = (
            1 if officialish else 0,
            1 if nutritionish else 0,
            token_hits,
            -1 if calculatorish else 0,
        )
        scored.append((score, item))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    filtered = [item for _, item in scored]
    return ("high" if filtered else "low"), filtered


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

    raw_components = [normalize_text(part) for part in raw_components if normalize_text(part)]
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
    exact_truth_present = any(str(item.get("evidence_role") or "") == "exact_truth" for item in selected_evidence)

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

    major_missing = [item["name"] for item in missing_components if item["importance"] == "high"]
    search_recommended = bool(major_missing and not exact_truth_present and (grounded_count > 0 or len(expected_components) >= 3))
    query_parts = _dedupe_texts([user_input, *major_missing])
    suggested_search_query = " ".join([*query_parts, "熱量", "營養"]) if search_recommended else ""

    return {
        "expected_components": expected_components,
        "store_hint": store_hint,
        "store_header_removed": bool(store_hint),
        "anchored_components": anchored_components,
        "missing_components": missing_components,
        "grounded_component_count": grounded_count,
        "missing_component_count": missing_count,
        "grounding_quality": grounding_quality,
        "exact_truth_present": exact_truth_present,
        "search_recommended": search_recommended,
        "suggested_search_query": suggested_search_query,
    }


def db_hit_type(*, retrieved_knowledge: list[dict[str, Any]], meal_template: dict[str, Any] | None) -> str:
    if any(item.get("evidence_role") == "exact_truth" for item in retrieved_knowledge):
        return "exact_truth"
    if meal_template:
        return "meal_template"
    if retrieved_knowledge:
        return "retrieved_knowledge"
    return "none"


def build_search_query(query: str, *, user_input: str, risk_packet: dict[str, Any], retrieved_knowledge: list[dict[str, Any]]) -> str:
    parts = [normalize_text(query or user_input)]
    risk_flags = {str(item) for item in risk_packet.get("risk_flags", [])}
    if "ramen" in risk_flags:
        parts.extend(["拉麵", "熱量", "營養"])
    if any(str(item.get("evidence_role") or "") == "exact_truth" for item in retrieved_knowledge):
        parts.append("營養標示")
    return " ".join(part for part in parts if part)


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
        try:
            results = await search_adapter.search(query=search_query, limit=5)
        except TypeError:
            results = await search_adapter.search(search_query)
        normalized_results = list(results or [])
        quality, filtered = search_result_quality(search_query, normalized_results)
        executed_tool_calls.append(
            build_tool_result(
                tool_name=tool_request,
                status="executed",
                reason=tool_reason or "Primary requested external nutrition lookup.",
                result_count=len(filtered),
                quality=quality,
            )
        )
        return filtered, filtered, search_query, quality
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


def compose_decision_lookup_query(
    *,
    current_user_input: str,
    meal_title: str | None = None,
    meal_link_action: str = "",
    resolved_query: str = "",
    retrieval_query: str = "",
) -> str:
    current_text = normalize_text(current_user_input)
    title = normalize_text(meal_title or "")
    resolved = normalize_text(resolved_query)
    retrieval = normalize_text(retrieval_query)
    if meal_link_action == "attach_to_existing_meal" and title and current_text:
        return f"{title} {current_text}".strip()
    for candidate in (current_text, resolved, retrieval, title):
        if candidate:
            return candidate
    return current_user_input
