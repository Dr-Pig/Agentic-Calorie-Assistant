from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .exact_brand_web_canary import ExactBrandWebLaneResult, run_exact_brand_web_canary
from .retrieval_semantic_decision import B2ManagerSemanticDecision
from .web_extract_port import WebExtractPort
from .web_search_port import WebSearchPort

LANE_ID = "listed_component_web_evidence_v1"


@dataclass(frozen=True)
class ListedComponentWebEvidenceOutcome:
    results: tuple[ExactBrandWebLaneResult, ...]
    trace: dict[str, Any]


async def run_listed_component_web_evidence(
    *,
    raw_user_input: str,
    manager_decision: B2ManagerSemanticDecision | None,
    search_port: WebSearchPort | None,
    extract_port: WebExtractPort | None,
    allow_search: bool,
) -> ListedComponentWebEvidenceOutcome:
    trace = _default_trace()
    if manager_decision is None:
        trace["skip_reason"] = "manager_owned_retrieval_intent_required"
        return ListedComponentWebEvidenceOutcome(results=(), trace=trace)
    listed_items = [str(item or "").strip() for item in manager_decision.listed_items or [] if str(item or "").strip()]
    if manager_decision.retrieval_goal != "listed_item_lookup":
        trace["skip_reason"] = "retrieval_goal_not_listed_item_lookup"
        return ListedComponentWebEvidenceOutcome(results=(), trace=trace)
    if not listed_items:
        trace["skip_reason"] = "manager_listed_items_required"
        return ListedComponentWebEvidenceOutcome(results=(), trace=trace)
    if not allow_search:
        trace["skip_reason"] = "search_not_allowed"
        return ListedComponentWebEvidenceOutcome(results=(), trace=trace)
    if search_port is None:
        trace["skip_reason"] = "search_port_unavailable"
        return ListedComponentWebEvidenceOutcome(results=(), trace=trace)
    if extract_port is None:
        trace["skip_reason"] = "extract_port_unavailable"
        return ListedComponentWebEvidenceOutcome(results=(), trace=trace)

    trace["attempted"] = True
    trace["retrieval_goal"] = "listed_item_lookup"
    trace["listed_item_count"] = len(listed_items)
    results: list[ExactBrandWebLaneResult] = []
    component_traces: list[dict[str, Any]] = []
    for item in listed_items:
        component_decision = B2ManagerSemanticDecision(
            base_dish=item,
            aliases=[item],
            brand_hint=manager_decision.brand_hint,
            size_hint=None,
            modifier_hints=[],
            listed_items=[],
            retrieval_goal="exact_brand_lookup",
            semantic_authority_source=manager_decision.semantic_authority_source,
        )
        query = _component_query(brand_hint=manager_decision.brand_hint, item=item)
        outcome = await run_exact_brand_web_canary(
            raw_user_input=raw_user_input,
            manager_decision=component_decision,
            search_port=search_port,
            extract_port=extract_port,
            allow_search=allow_search,
            contextualized_query=query,
        )
        component_trace = dict(outcome.trace)
        component_trace["manager_owned_component_item"] = item
        component_traces.append(component_trace)
        if outcome.result is not None:
            results.append(outcome.result)

    trace["component_traces"] = component_traces
    trace["search_attempt_count"] = sum(int(item.get("search_attempt_count") or 0) for item in component_traces)
    trace["extract_attempt_count"] = sum(int(item.get("extract_attempt_count") or 0) for item in component_traces)
    trace["search_query"] = " | ".join(str(item.get("search_query") or "") for item in component_traces if item.get("search_query"))
    trace["web_query"] = trace["search_query"]
    trace["component_level_evidence_present"] = len(results) == len(listed_items)
    trace["all_listed_components_have_sources"] = len(results) == len(listed_items)
    trace["selected_extract_present"] = len(results) == len(listed_items)
    trace["turn_web_evidence_packet_present"] = len(results) == len(listed_items)
    trace["turn_web_evidence_may_support_commit"] = len(results) == len(listed_items)
    trace["permanent_fooddb_promotion_allowed"] = False
    trace["fooddb_truth_updated"] = False
    trace["search_candidate_packet_truth_allowed"] = False
    trace["source_admissibility_status"] = "accepted" if len(results) == len(listed_items) else "rejected"
    if len(results) != len(listed_items):
        trace["failure_reason"] = "not_all_manager_listed_components_have_accepted_extract"
    return ListedComponentWebEvidenceOutcome(results=tuple(results), trace=trace)


def _component_query(*, brand_hint: str | None, item: str) -> str:
    parts = [str(brand_hint or "").strip(), item]
    return " ".join(part for part in parts if part)


def _default_trace() -> dict[str, Any]:
    return {
        "lane_id": LANE_ID,
        "attempted": False,
        "skip_reason": None,
        "failure_reason": None,
        "retrieval_goal": None,
        "search_query": None,
        "web_query": None,
        "component_traces": [],
        "search_attempt_count": 0,
        "extract_attempt_count": 0,
        "component_level_evidence_present": False,
        "all_listed_components_have_sources": False,
        "selected_extract_present": False,
        "turn_web_evidence_packet_present": False,
        "turn_web_evidence_may_support_commit": False,
        "permanent_fooddb_promotion_allowed": False,
        "fooddb_truth_updated": False,
        "search_candidate_packet_truth_allowed": False,
        "source_admissibility_status": None,
    }


__all__ = ["ListedComponentWebEvidenceOutcome", "run_listed_component_web_evidence"]
