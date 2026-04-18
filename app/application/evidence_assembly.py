from __future__ import annotations
from typing import Any

from ..agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from ..agent.exact_item_packets import resolve_exact_item
from ..agent.local_knowledge_selector import resolve_ingredient_anchors
from ..application.context_assembly import canonicalize_lookup_text, lookup_key
from ..application.evidence_normalizer import source_class_for_item
from .evidence_normalizer import infer_brand_hint, infer_candidate_relationship, infer_expected_components, infer_query_alignment, infer_store_hint, infer_variant_type, retrieval_lane_for_item, split_evidence_lanes, to_evidence_candidate
from .evidence_selector import db_hit_type, retrieval_query_is_usable, search_result_quality, summarize_retrieved_evidence, summarize_selected_evidence
from .tool_evidence_policy import _observe_search_results, _refinement_queries, build_attested_evidence_blocks, build_tool_candidate_requests, build_tool_result, extract_search_evidence_blocks, normalize_tool_evidence, tool_availability
from ..schemas import EstimateRequest, TurnIntentResult

__all__ = ["build_attested_evidence_blocks", "build_evidence_bundle", "build_partial_grounding_packet", "build_reasoning_state", "build_tool_candidate_requests", "build_tool_result", "db_hit_type", "execute_primary_tool_request", "extract_search_evidence_blocks", "infer_brand_hint", "infer_candidate_relationship", "infer_expected_components", "infer_query_alignment", "infer_variant_type", "merge_evidence_items", "normalize_tool_evidence", "retrieval_query_is_usable", "retrieval_lane_for_item", "search_result_quality", "split_evidence_lanes", "summarize_retrieved_evidence", "summarize_selected_evidence", "tool_availability"]

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
