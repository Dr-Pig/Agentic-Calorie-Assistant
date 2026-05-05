from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .food_evidence_packet_builder import build_food_evidence_recall_packet
from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    RetrievalIntentSource,
    build_food_evidence_retriever_route_plan,
)
from .fooddb_retrieval_policy import IndexedFoodRecord, retrieve_fooddb_candidates
from .retrieval_intent import RetrievalIntent
from .tool_evidence_result import build_tool_evidence_result
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke


@dataclass(frozen=True)
class RetrieverExecutionCase:
    case_id: str
    raw_query: str
    intent: RetrievalIntent
    expected_primary_backend: str
    intent_source: RetrievalIntentSource = "manager_decision"


def build_food_evidence_retriever_execution_smoke(
    *,
    index: FoodEvidenceIndexPort,
    availability: RetrieverBackendAvailability,
    cases: tuple[RetrieverExecutionCase, ...] = (),
) -> dict[str, Any]:
    execution_cases = cases or _default_cases()
    case_results = [
        _case_result(case, index=index, availability=availability) for case in execution_cases
    ]
    blockers = [
        f"retriever_execution_case_failed:{case['case_id']}"
        for case in case_results
        if case["status"] != "pass"
    ]
    clear = not blockers
    return {
        "artifact_type": "accurate_intake_food_evidence_retriever_execution_smoke_v1",
        "artifact_schema_version": "1.0",
        "generated_at_utc": _now(),
        "track": "FDB",
        "classification": "deterministic_retriever_execution_smoke_only",
        "claim_scope": "fooddb_websearch_retriever_execution_boundary",
        "status": "pass" if clear else "blocked",
        "blockers": blockers,
        "runtime_truth_changed": False,
        "mutation_changed": False,
        "manager_context_changed": False,
        "packetizer_format_changed": False,
        "live_provider_used": False,
        "live_websearch_used": False,
        "readiness_claimed": False,
        "cases": case_results,
        "summary": {
            "case_count": len(case_results),
            "pass_count": sum(1 for case in case_results if case["status"] == "pass"),
            "fail_count": sum(1 for case in case_results if case["status"] != "pass"),
            "fooddb_tool_result_count": sum(
                1 for case in case_results if case["tool_name"] == "lookup_food_evidence"
            ),
            "websearch_tool_result_count": sum(
                1 for case in case_results if case["tool_name"] == "search_official_nutrition"
            ),
            "ask_followup_case_count": sum(
                1 for case in case_results if case["route_plan"]["primary_backend"] == "ask_followup"
            ),
            "blocked_no_execution_case_count": sum(
                1
                for case in case_results
                if case["route_plan"]["primary_backend"] == "blocked_no_execution"
            ),
        },
        "dependency_inversion": {
            "intent_source": "manager_owned_retrieval_intent_or_fixture_in_tests",
            "deterministic_role": "execute_route_plan_and_validate_boundaries",
            "deterministic_does_not_own": [
                "user_intent",
                "workflow_effect",
                "final_action",
                "mutation_legality",
                "fooddb_truth_promotion",
            ],
            "backend_implementation_manager_visible": False,
        },
        "next_required_slice": (
            "grokfast_fooddb_diagnostic_preflight"
            if clear
            else "inspect_food_evidence_retriever_execution_blockers"
        ),
        "non_claims": [
            "no_runtime_truth_promotion",
            "no_runtime_mutation",
            "no_manager_context_change",
            "no_packetizer_format_change",
            "no_live_provider_call",
            "no_live_websearch_call",
            "no_readiness_claim",
        ],
    }


def _case_result(
    case: RetrieverExecutionCase,
    *,
    index: FoodEvidenceIndexPort,
    availability: RetrieverBackendAvailability,
) -> dict[str, Any]:
    route_plan = build_food_evidence_retriever_route_plan(
        case.intent,
        availability=availability,
        intent_source=case.intent_source,
    )
    if route_plan.primary_backend == "blocked_no_execution":
        return _blocked_no_execution_case(case=case, route_plan=route_plan)
    if route_plan.primary_backend == "ask_followup":
        return _ask_followup_case(case=case, route_plan=route_plan)
    if route_plan.websearch_candidate_enabled:
        return _websearch_case(case=case, route_plan=route_plan)
    return _fooddb_case(case=case, route_plan=route_plan, index=index)


def _fooddb_case(
    *,
    case: RetrieverExecutionCase,
    route_plan: Any,
    index: FoodEvidenceIndexPort,
) -> dict[str, Any]:
    manager_owned_query = _query_from_intent(case.intent)
    records = _records_for_query(index=index, query=manager_owned_query)
    retrieval_result = retrieve_fooddb_candidates(manager_owned_query, retrieval_records=records)
    packet = build_food_evidence_recall_packet(
        packet_id=f"retriever-execution:{case.case_id}",
        raw_user_input=case.raw_query,
        retrieval_result=retrieval_result,
    )
    tool_result = build_tool_evidence_result(
        tool_name="lookup_food_evidence",
        tool_call_id=f"tool-{case.case_id}",
        evidence_packets=(packet,),
        trace_context={
            "packet_artifact_type": "inline_retriever_execution_packet",
            "packet_claim_scope": "deterministic_fooddb_retriever_execution",
        },
    )
    checks = {
        "expected_primary_backend": route_plan.primary_backend == case.expected_primary_backend,
        "route_does_not_decide_logged_or_draft": route_plan.decides_logged_or_draft is False,
        "tool_result_read_only": tool_result["runtime_mutation_allowed"] is False,
        "tool_result_backend_hidden": tool_result["source_implementation_visible"] is False,
        "accepted_fooddb_packet_present": bool(packet["evidence_items"]),
    }
    return _base_case_payload(
        case=case,
        route_plan=route_plan,
        checks=checks,
        tool_name="lookup_food_evidence",
        tool_result=tool_result,
        extra={
            "manager_owned_query": manager_owned_query,
            "fooddb_candidate_count": len(retrieval_result.get("accepted_candidates") or []),
            "websearch_runtime_truth_allowed": False,
        },
    )


def _websearch_case(*, case: RetrieverExecutionCase, route_plan: Any) -> dict[str, Any]:
    packet_smoke = build_websearch_candidate_packet_smoke()
    packets = _websearch_packets_for_intent(case.intent, packet_smoke=packet_smoke)
    tool_result = build_tool_evidence_result(
        tool_name="search_official_nutrition",
        tool_call_id=f"tool-{case.case_id}",
        evidence_packets=packets,
        trace_context={
            "live_websearch_used": False,
            "websearch_runtime_truth_allowed": False,
        },
    )
    checks = {
        "expected_primary_backend": route_plan.primary_backend == case.expected_primary_backend,
        "route_does_not_decide_logged_or_draft": route_plan.decides_logged_or_draft is False,
        "websearch_candidate_enabled": route_plan.websearch_candidate_enabled is True,
        "websearch_runtime_truth_forbidden": route_plan.websearch_runtime_truth_allowed is False,
        "websearch_candidate_packet_present": len(packets) > 0,
        "all_packets_candidate_only": all(
            packet.get("truth_level") == "candidate" for packet in tool_result["evidence_packets"]
        ),
    }
    return _base_case_payload(
        case=case,
        route_plan=route_plan,
        checks=checks,
        tool_name="search_official_nutrition",
        tool_result=tool_result,
        extra={
            "websearch_runtime_truth_allowed": False,
            "websearch_candidate_packet_count": len(packets),
        },
    )


def _ask_followup_case(*, case: RetrieverExecutionCase, route_plan: Any) -> dict[str, Any]:
    checks = {
        "expected_primary_backend": route_plan.primary_backend == case.expected_primary_backend,
        "no_backend_execution_before_clarification": route_plan.backend_sequence == (),
        "route_does_not_decide_logged_or_draft": route_plan.decides_logged_or_draft is False,
        "mutation_forbidden": route_plan.mutation_allowed is False,
    }
    return _base_case_payload(
        case=case,
        route_plan=route_plan,
        checks=checks,
        tool_name=None,
        tool_result=None,
        extra={
            "runtime_mutation_allowed": False,
            "truth_selection_forbidden": True,
            "websearch_runtime_truth_allowed": False,
        },
    )


def _blocked_no_execution_case(*, case: RetrieverExecutionCase, route_plan: Any) -> dict[str, Any]:
    checks = {
        "expected_primary_backend": route_plan.primary_backend == case.expected_primary_backend,
        "no_backend_execution": route_plan.backend_sequence == (),
        "route_does_not_decide_logged_or_draft": route_plan.decides_logged_or_draft is False,
        "raw_text_hint_not_executed": route_plan.raw_text_hint_executed is False,
        "mutation_forbidden": route_plan.mutation_allowed is False,
        "requires_manager_owned_intent": route_plan.manager_owned_intent_required is True,
    }
    return _base_case_payload(
        case=case,
        route_plan=route_plan,
        checks=checks,
        tool_name=None,
        tool_result=None,
        extra={
            "runtime_mutation_allowed": False,
            "truth_selection_forbidden": True,
            "websearch_runtime_truth_allowed": False,
        },
    )


def _base_case_payload(
    *,
    case: RetrieverExecutionCase,
    route_plan: Any,
    checks: dict[str, bool],
    tool_name: str | None,
    tool_result: dict[str, Any] | None,
    extra: dict[str, Any],
) -> dict[str, Any]:
    return {
        "case_id": case.case_id,
        "status": "pass" if checks and all(checks.values()) else "fail",
        "checks": checks,
        "raw_query": case.raw_query,
        "route_plan": {
            "primary_backend": route_plan.primary_backend,
            "backend_sequence": list(route_plan.backend_sequence),
            "retrieval_intent_source": route_plan.retrieval_intent_source,
            "manager_owned_intent_required": route_plan.manager_owned_intent_required,
            "raw_text_hint_executed": route_plan.raw_text_hint_executed,
            "read_only": route_plan.read_only,
            "mutation_allowed": route_plan.mutation_allowed,
            "decides_logged_or_draft": route_plan.decides_logged_or_draft,
            "runtime_truth_source": route_plan.runtime_truth_source,
            "websearch_candidate_enabled": route_plan.websearch_candidate_enabled,
            "websearch_runtime_truth_allowed": route_plan.websearch_runtime_truth_allowed,
            "routing_reasons": list(route_plan.routing_reasons),
        },
        "tool_name": tool_name,
        "tool_evidence_result": tool_result,
        **extra,
    }


def _records_for_query(
    *,
    index: FoodEvidenceIndexPort,
    query: str,
) -> tuple[IndexedFoodRecord, ...]:
    search_records = getattr(index, "search_records", None)
    if callable(search_records):
        records = search_records(query, limit=20)
        if records:
            return records
    return index.load_records()


def _query_from_intent(intent: RetrievalIntent) -> str:
    parts = [
        *(str(alias).strip() for alias in intent.aliases if str(alias).strip()),
        str(intent.base_dish or "").strip(),
    ]
    for part in parts:
        if part:
            return part
    return ""


def _websearch_packets_for_intent(
    intent: RetrievalIntent,
    *,
    packet_smoke: dict[str, Any],
) -> tuple[dict[str, Any], ...]:
    brand = str(intent.brand_hint or "").strip().lower()
    identity_terms = {
        str(intent.base_dish or "").strip().lower(),
        *(str(alias).strip().lower() for alias in intent.aliases if str(alias).strip()),
    }
    scoped_packets = []
    for item in packet_smoke.get("cases") or []:
        packet = item.get("websearch_candidate_packet") if isinstance(item, dict) else None
        if not isinstance(packet, dict):
            continue
        title = str(packet.get("title") or "").lower()
        query = str(packet.get("query") or "").lower()
        brand_matches = not brand or brand in title or brand in query
        identity_matches = any(term and (term in title or term in query) for term in identity_terms)
        exact_enough = (
            packet.get("match_type") == "exact"
            and packet.get("brand_match") in {"exact", "same"}
            and packet.get("source_quality_label") in {"brand_menu", "official_brand"}
        )
        if brand_matches and identity_matches and exact_enough:
            scoped_packets.append(packet)
    return tuple(scoped_packets)


def _default_cases() -> tuple[RetrieverExecutionCase, ...]:
    return (
        RetrieverExecutionCase(
            case_id="generic_boba_fooddb",
            raw_query="boba",
            expected_primary_backend="sqlite_fts_index",
            intent=RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
        RetrieverExecutionCase(
            case_id="exact_brand_websearch_candidate",
            raw_query="Milksha pearl black tea latte",
            expected_primary_backend="sqlite_fts_index",
            intent=RetrievalIntent(
                base_dish="pearl black tea latte",
                aliases=["Milksha pearl black tea latte"],
                brand_hint="Milksha",
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="exact_brand_lookup",
            ),
        ),
        RetrieverExecutionCase(
            case_id="composition_clarification",
            raw_query="luwei",
            expected_primary_backend="ask_followup",
            intent=RetrievalIntent(
                base_dish="luwei",
                aliases=["luwei"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="composition_clarification",
            ),
        ),
        RetrieverExecutionCase(
            case_id="raw_text_hint_does_not_execute_backend",
            raw_query="boba",
            expected_primary_backend="blocked_no_execution",
            intent_source="raw_text_hint",
            intent=RetrievalIntent(
                base_dish="bubble milk tea",
                aliases=["boba"],
                brand_hint=None,
                size_hint=None,
                modifier_hints=[],
                listed_items=[],
                retrieval_goal="generic_anchor_lookup",
            ),
        ),
    )


def _now() -> str:
    return datetime.now(UTC).isoformat().replace("+00:00", "Z")


__all__ = [
    "RetrieverExecutionCase",
    "build_food_evidence_retriever_execution_smoke",
]
