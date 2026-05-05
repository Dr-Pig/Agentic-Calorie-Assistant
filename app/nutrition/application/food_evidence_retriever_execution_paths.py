from __future__ import annotations

from typing import Any

from .food_evidence_index_port import FoodEvidenceIndexPort
from .food_evidence_packet_builder import build_food_evidence_recall_packet
from .food_evidence_retriever_execution_cases import RetrieverExecutionCase
from .food_evidence_retriever_execution_scope import (
    query_from_intent,
    records_for_query,
    websearch_packets_for_intent,
)
from .food_evidence_retriever_router import (
    RetrieverBackendAvailability,
    build_food_evidence_retriever_route_plan,
)
from .fooddb_retrieval_policy import retrieve_fooddb_candidates
from .tool_evidence_result import build_tool_evidence_result
from .websearch_candidate_packet_smoke import build_websearch_candidate_packet_smoke


def case_result(
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
        return blocked_no_execution_case_result(case=case, route_plan=route_plan)
    if route_plan.primary_backend == "ask_followup":
        return ask_followup_case_result(case=case, route_plan=route_plan)
    if route_plan.websearch_candidate_enabled:
        return websearch_case_result(case=case, route_plan=route_plan)
    return fooddb_case_result(case=case, route_plan=route_plan, index=index)


def fooddb_case_result(
    *,
    case: RetrieverExecutionCase,
    route_plan: Any,
    index: FoodEvidenceIndexPort,
) -> dict[str, Any]:
    manager_owned_query = query_from_intent(case.intent)
    records = records_for_query(index=index, query=manager_owned_query)
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
    return base_case_payload(
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


def websearch_case_result(*, case: RetrieverExecutionCase, route_plan: Any) -> dict[str, Any]:
    packet_smoke = build_websearch_candidate_packet_smoke()
    packets = websearch_packets_for_intent(case.intent, packet_smoke=packet_smoke)
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
    return base_case_payload(
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


def ask_followup_case_result(*, case: RetrieverExecutionCase, route_plan: Any) -> dict[str, Any]:
    checks = {
        "expected_primary_backend": route_plan.primary_backend == case.expected_primary_backend,
        "no_backend_execution_before_clarification": route_plan.backend_sequence == (),
        "route_does_not_decide_logged_or_draft": route_plan.decides_logged_or_draft is False,
        "mutation_forbidden": route_plan.mutation_allowed is False,
    }
    return base_case_payload(
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


def blocked_no_execution_case_result(
    *,
    case: RetrieverExecutionCase,
    route_plan: Any,
) -> dict[str, Any]:
    checks = {
        "expected_primary_backend": route_plan.primary_backend == case.expected_primary_backend,
        "no_backend_execution": route_plan.backend_sequence == (),
        "route_does_not_decide_logged_or_draft": route_plan.decides_logged_or_draft is False,
        "raw_text_hint_not_executed": route_plan.raw_text_hint_executed is False,
        "mutation_forbidden": route_plan.mutation_allowed is False,
        "requires_manager_owned_intent": route_plan.manager_owned_intent_required is True,
    }
    return base_case_payload(
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


def base_case_payload(
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


__all__ = [
    "base_case_payload",
    "blocked_no_execution_case_result",
    "ask_followup_case_result",
    "case_result",
    "fooddb_case_result",
    "websearch_case_result",
]
