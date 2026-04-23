"""Primary tool request execution extracted from evidence_assembly."""
from __future__ import annotations

from typing import Any

from app.runtime.agent.calibration_packets import get_meal_calibration, suggest_calibration_packet
from app.nutrition.agent.exact_item_packets import resolve_exact_item
from app.nutrition.agent.local_knowledge_selector import resolve_ingredient_anchors
from app.nutrition.application.evidence_selector import search_result_quality
from app.nutrition.application.tool_evidence_policy import (
    _observe_search_results,
    _refinement_queries,
    extract_search_evidence_blocks,
    retrieval_attempt_budget,
)
from app.shared.contracts.common import EstimateRequest


async def execute_primary_tool_request(
    *,
    tool_request: str,
    tool_reason: str,
    retrieval_query: str,
    resolved_query: str,
    
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
        session_components = list(getattr(request.session_state, "last_known_components", []) or [])
        foods = list(
            dict.fromkeys(
                [str(getattr(item, "name", "") or "").strip() for item in session_components]
                or [resolved_query or retrieval_query]
            )
        )
        portion_hints = [
            str(getattr(item, "portion_hint", "") or "").strip()
            for item in session_components
            if str(getattr(item, "portion_hint", "") or "").strip()
        ]
        results = resolve_ingredient_anchors(
            foods,
            portion_hints=portion_hints,
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
        # Bundle 2 retrieval baseline: keep the orchestration entry thin while delegating
        # candidate gathering and page extraction to the adapter, then evaluate eligibility here.
        search_query = resolved_query or retrieval_query
        identity_target = resolved_query or retrieval_query
        best_query = search_query
        filtered: list[dict[str, Any]] = []
        quality_meta: dict[str, Any] | None = None
        query_class = "branded_exact_like" if retrieval_attempt_budget(query=retrieval_query, identity_target=identity_target) > 3 else "generic"
        max_attempts = retrieval_attempt_budget(query=retrieval_query, identity_target=identity_target)
        refinement_reasons: list[str] = []
        stop_reason = "attempt_budget_exhausted"
        for candidate_query in _refinement_queries(query=retrieval_query, resolved_query=resolved_query, identity_target=identity_target)[:max_attempts]:
            if hasattr(search_adapter, "search_candidates"):
                normalized_results = list(await search_adapter.search_candidates(candidate_query, max_results=5) or [])
                urls = [str(item.get("url") or "") for item in normalized_results if str(item.get("url") or "").strip()]
                extracted_by_url: dict[str, dict[str, Any]] = {}
                if urls and hasattr(search_adapter, "extract_structured_page_data"):
                    extracted_rows = await search_adapter.extract_structured_page_data(urls=urls[:5], query=candidate_query)
                    extracted_by_url = {str(item.get("url") or ""): dict(item) for item in extracted_rows}
                normalized_results = [{**item, **extracted_by_url.get(str(item.get("url") or ""), {})} for item in normalized_results]
            else:
                try:
                    normalized_results = list(await search_adapter.search(query=candidate_query, limit=5) or [])
                except TypeError:
                    normalized_results = list(await search_adapter.search(candidate_query) or [])
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
                "query_class": query_class,
                "refinement_queries": _refinement_queries(query=retrieval_query, resolved_query=resolved_query, identity_target=identity_target)[:max_attempts],
                "attempt_budget": max_attempts,
                "refine_reason": observation["why_not_enough_yet"],
                "stop_reason": stop_reason,
            }
            if not observation["needs_refinement"]:
                stop_reason = "eligibility_resolved"
                quality_meta["stop_reason"] = stop_reason
                break
            refinement_reasons.append(observation["why_not_enough_yet"])
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
